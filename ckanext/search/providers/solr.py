import hashlib
import json
import logging
import socket
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

import pysolr
import requests
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config, get_validator
from ckan.types import Schema
from ckanext.search.interfaces import ISearchProvider, SearchResults, SearchSchema

log = logging.getLogger(__name__)


class SolrSchema:

    solr_url: str = ""
    core_url: str = ""
    schema_admin_url: str = ""
    cores_url: str = ""

    def __init__(self, solr_url: str, core_name: str | None = None) -> None:

        # TODO: check URL, auth
        solr_url = solr_url.rstrip("/")
        self.solr_url = solr_url

        parts = urlparse(self.solr_url)
        solr_root_url = urlunparse(
            (parts.scheme, parts.netloc, "solr", None, None, None)
        )

        path_parts = [p for p in parts.path.split("/") if p]
        if not core_name:
            if len(path_parts) > 1:
                self.core_name = path_parts[1]
                self.core_url = f"{self.solr_url}"
            else:
                raise ValueError(
                    "Root Solr URL provided and no core_name param provided"
                )
        else:
            self.core_name = core_name
            if len(path_parts) > 1:
                if path_parts[1] != core_name:
                    raise ValueError(
                        "Inconsistent core names provided in URL and core_name param"
                    )
                self.core_name = core_name
                self.core_url = f"{self.solr_url}"
            else:
                self.core_url = f"{self.solr_url}/{core_name}"

        self.schema_admin_url = f"{self.core_url}/schema"
        self.cores_admin_url = f"{solr_root_url}/admin/cores"

    def _request(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:

        data = {command: params}
        # TODO: auth
        resp = requests.post(
            self.schema_admin_url,
            json=data,
        )

        return resp.json()

    def get_core(self, core_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get core details. Returns None if the core does not exist.
        """
        if not core_name:
            core_name = self.core_name

        params = {"action": "STATUS", "core": core_name}

        # TODO: auth, error handling
        data = requests.get(self.cores_admin_url, params=params).json()

        status = data.get("status", {})

        if core_name not in status:
            return None

        return status[core_name]

    def create_core(self, core_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a core in Solr.
        """
        if not core_name:
            core_name = self.core_name

        params = {"action": "CREATE", "name": core_name, "configSet": "_default"}
        # TODO: auth, error handling
        resp = requests.get(self.cores_admin_url, params=params).json()

        return resp

    def get_field(self, name: str) -> Optional[Dict[str, Any]]:

        url = f"{self.schema_admin_url}/fields/{name}"

        # TODO: auth, error handling
        resp = requests.get(url)

        resp = resp.json()

        return resp["field"] if resp.get("field") else None

    def add_field(self, name: str, type_: str, **kwargs: Any) -> Dict[str, Any]:

        params = {"name": name, "type": type_}
        params.update(kwargs)

        resp = self._request("add-field", params)

        return resp

    def get_field_type(self, name: str) -> Optional[Dict[str, Any]]:

        url = f"{self.schema_admin_url}/fieldtypes/{name}"

        # TODO: auth, error handling
        resp = requests.get(url)

        resp = resp.json()

        return resp["fieldType"] if resp.get("fieldType") else None

    def add_field_type(self, name: str, **kwargs: Any) -> Dict[str, Any]:

        params = {"name": name}
        params.update(kwargs)

        resp = self._request("add-field-type", params)

        return resp

    def get_copy_field(self, source: str, dest: str) -> Optional[Dict[str, Any]]:

        url = f"{self.schema_admin_url}/copyfields"

        params = {
            "source.fl": [source],
            "dest.fl": [dest],
        }

        # TODO: auth, error handling
        resp = requests.get(url, params=params)

        resp = resp.json()

        return resp["copyFields"] if resp.get("copyFields") else None

    def copy_field(self, source: str, dest: str) -> Dict[str, Any]:

        params = {"source": source, "dest": dest}

        resp = self._request("add-copy-field", params)

        return resp


class SolrSearchProvider(SingletonPlugin):

    implements(ISearchProvider, inherit=True)

    id = "solr"

    _client = None
    _admin_client = None
    _core_admin_client = None

    # ISearchProvider

    def initialize_search_provider(
        self, search_schema: SearchSchema, clear: bool
    ) -> None:

        admin_client = self.get_admin_client()
        # TODO: Should be create the ckan core here?

        if not admin_client.get_core():
            resp = admin_client.create_core()
            log.info("Created Solr core: %s" % admin_client.core_name)

        # TODO: how to handle udpates to the schema:
        #   - Replace fields if a field already exists
        #   - Delete fields no longer in the schema
        #   - Delete copy fields no longer needed

        # Create catch-all field

        # TODO: lang

        if not admin_client.get_field("text_combined"):
            admin_client.add_field(
                "text_combined", "text_en", indexed=True, stored=False, multiValued=True
            )

        # Set unique id

        # TODO: Create dynamic fields? eg. *_date, *_list, etc

        solr_field_types = {
            # TODO: lang
            "text": "text_en",
            "bool": "boolean",
            # TODO: check
            "date": "pdate",
        }

        for field_name, field in search_schema.get("fields", {}).items():

            field_type = field.pop("type")
            if admin_client.get_field(field_name):
                log.info(
                    f"Field '{field_name}' exists and clear not provided, skipping"
                )
            else:
                # Translate common search schema format to Solr format

                if field_type in solr_field_types:
                    field_type = solr_field_types[field_type]

                field["multiValued"] = field.pop("multiple", False)

                resp = admin_client.add_field(field_name, field_type, **field)
                if "error" in resp:
                    msg = ""
                    if "details" in resp["error"]:
                        msg = resp["error"]["details"][0]["errorMessages"]
                    elif "msg" in resp["error"]:
                        msg = resp["error"]["msg"][:1000]

                    log.warning(f'Error creating field "{field_name}": {msg}')
                else:
                    log.info(
                        f"Added field '{field_name}' to index, with type {field_type} and params {field}"
                    )

            # Copy text values to catch-all field
            if field_type.startswith("text"):
                if not admin_client.get_copy_field(field_name, "text_combined"):
                    admin_client.copy_field(field_name, "text_combined")
                    log.info(f"Added field '{field_name}' to combined text field")

    # TODO: do we need id_ or we just check the search_data dict?
    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:

        client = self.get_client()

        # TODO: looks like we can set uniqueKey via the API so index_id can not be
        # used by solr by default. It uses "id". This is probably fine™ if using UUID
        # (barring uuid clashes) for single sites but it might cause issues if users
        # use custom ids or using the same db on two sites
        # (for testing or development)
        search_data["index_id"] = hashlib.md5(
            b"%s%s" % (id_.encode(), config["ckan.site_id"].encode())
        ).hexdigest()

        try:
            # TODO: commit
            client.add(docs=[search_data])
        except pysolr.SolrError as e:
            msg = "Solr returned an error: {0}".format(
                e.args[0][:1000]  # limit huge responses
            )
            # TODO: custom exception
            raise Exception(msg)
        except socket.error as e:
            assert client
            msg = "Could not connect to Solr using {0}: {1}".format(client.url, str(e))
            log.error(msg)
            # TODO: custom exception
            raise Exception(msg)

    def search_query_schema(self) -> Schema:
        """
        Return a schema to validate Solr specific custom query parameters.
        """

        ignore_missing = get_validator("ignore_missing")
        unicode_safe = get_validator("unicode_safe")
        convert_to_list_if_string = get_validator("convert_to_list_if_string")

        search_query_schema = {
            "df": [ignore_missing, unicode_safe],
            "fl": [ignore_missing, unicode_safe],
            "qf": [ignore_missing, unicode_safe],
            "bf": [ignore_missing, unicode_safe],
            "boost": [ignore_missing, unicode_safe],
            "tie": [ignore_missing, unicode_safe],
            "defType": [ignore_missing, unicode_safe],
            "mm": [ignore_missing, unicode_safe],
            # Compatibility params with old API
            "fq": [ignore_missing, convert_to_list_if_string],
            "rows": [ignore_missing, unicode_safe],
            # TODO: 'facet', 'facet.mincount', 'facet.limit', 'facet.field',
        }

        return search_query_schema

    def search_query(
        self,
        q: str,
        filters: dict[str, str | list[str]],
        sort: list[list[str]],
        additional_params: dict[str, Any],
        lang: str,
        return_ids: bool = False,
        return_entity_types: bool = False,
        return_facets: bool = False,
        limit: int = 20,
        start: int = 0,
    ) -> Optional[SearchResults]:

        # Transform generic search params to Solr query params
        if not q:
            q = "*:*"

        df = additional_params.get("df") or "text_combined"

        # TODO: transform filters and combine
        fq = additional_params.get("fq") or []
        if isinstance(fq, str):
            fq = [str]

        solr_params = {
            "q": q,
            "df": df,
            "fq": fq,
        }

        # TODO: perm labels for arbitrary entities
        if "permission_labels" in filters:
            perms_conditions = (
                "permission_labels:("
                + " OR ".join(solr_literal(p) for p in filters["permission_labels"])
                + ")"
            )

            perms_fq = (
                "(entity_type:dataset AND {}) OR (*:* NOT entity_type:dataset)".format(
                    perms_conditions
                )
            )

            solr_params["fq"].append(perms_fq)

        client = self.get_client()

        try:
            solr_response = client.search(**solr_params)
        except pysolr.SolrError as e:
            # TODO:
            raise e

        items = []
        for doc in solr_response.docs:

            # TODO: return just ids, or arbitrary fields?
            # TODO allow to choose validated/not validated? i.e use_default_schema
            items.append(json.loads(doc["validated_data_dict"]))

        return {"count": len(items), "results": items, "facets": {}}

    def clear_index(self) -> None:

        client = self.get_client()
        try:
            client.delete(q="*:*")
            log.info("Cleared all documents in the search index")

        except pysolr.SolrError as e:
            # TODO:
            raise e

    # Backend methods

    def get_client(self) -> pysolr.Solr:

        if self._client:
            return self._client

        # TODO: core in URL

        # TODO:
        #   Check conf at startup, handle always_commit, timeout and auth
        self._client = pysolr.Solr(config["ckan.search.solr.url"], always_commit=True)

        return self._client

    def get_admin_client(self) -> SolrSchema:

        if self._admin_client:
            return self._admin_client

        # TODO: core in URL

        # TODO:
        #   Check conf at startup, handle always_commit, timeout and auth
        self._admin_client = SolrSchema(config["ckan.search.solr.url"])

        return self._admin_client


# TODO: review
def solr_literal(t: str) -> str:
    """
    return a safe literal string for a solr query. Instead of escaping
    each of + - && || ! ( ) { } [ ] ^ " ~ * ? : \\ / we're just dropping
    double quotes -- this method currently only used by tokens like site_id
    and permission labels.
    """
    return '"' + t.replace('"', "") + '"'
