import hashlib
import logging
import json
import socket
from typing import Any, Dict, Optional

import requests
import pysolr
from ckanext.search.interfaces import ISearchProvider, SearchResults, SearchSchema

from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config


log = logging.getLogger(__name__)


class SolrSchema:

    solr_url: str = ""
    schema_url: str = ""
    luke_url: str = ""

    def __init__(self, solr_url: str) -> None:

        # TODO: check URL, auth
        solr_url = solr_url.rstrip("/")
        self.solr_url = solr_url
        self.schema_url = f"{self.solr_url}/schema"

    def _request(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:

        data = {command: params}
        # TODO: auth
        resp = requests.post(
            self.schema_url,
            json=data,
        )

        return resp.json()

    def get_field(self, name: str) -> Optional[Dict[str, Any]]:

        url = f"{self.schema_url}/fields/{name}"

        # TODO: auth, error handling
        resp = requests.get(url)

        resp = resp.json()

        return resp["field"] if resp.get("field") else None

    def add_field(self, name: str, type_: str, **kwargs: Any) -> Dict[str, Any]:

        params = {"name": name, "type": type_}
        params.update(kwargs)

        resp = self._request("add-field", params)

        return resp

    def get_copy_field(self, source: str, dest: str) -> Optional[Dict[str, Any]]:

        url = f"{self.schema_url}/copyfields"

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

    # ISearchProvider

    def initialize_search_provider(
        self, search_schema: SearchSchema, clear: bool
    ) -> None:

        # TODO: how to handle udpates to the schema:
        #   - Replace fields if a field already exists
        #   - Delete fields no longer in the schema
        #   - Delete copy fields no longer needed

        admin_client = self.get_admin_client()

        # Create catch-all field

        # TODO: lang
        resp = admin_client.add_field(
            "text_combined", "text_en", indexed=True, stored=False, multiValued=True
        )

        # Set unique id

        # TODO: Create dynamic fields? eg. *_date, *_list, etc

        for field in search_schema["fields"]:

            field_name = field.pop("name")
            field_type = field.pop("type")

            if admin_client.get_field(field_name):
                log.info(
                    f"Field '{field_name}' exists and clear not provided, skipping"
                )

            # Translate common search schema format to Solr format

            solr_field_types = {
                # TODO: lang
                "text": "text_en",
                "bool": "boolean",
                # TODO: check
                "date": "pdate",
            }
            if field_type in solr_field_types:

                field_type = solr_field_types[field_type]

            field["multiValued"] = field.pop("multiple", False)

            resp = admin_client.add_field(field_name, field_type, **field)
            if "error" in resp:
                log.warning(
                    f'Error creating field "{field_name}": {resp["error"]["details"][0]["errorMessages"]}'
                )
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

        validated_data_dict = json.dumps(search_data, cls=MissingNullEncoder)

        # TODO: looks like we can set uniqueKey via the API so index_id can not be
        # used by solr by default. It uses "id". This is probably fine™ if using UUID
        # (barring uuid clashes) for single sites but it might cause issues if users
        # use custom ids or using the same db on two sites
        # (for testing or development)
        search_data["index_id"] = hashlib.md5(
            b"%s%s" % (id_.encode(), config["ckan.site_id"].encode())
        ).hexdigest()

        # TODO: choose what to commit
        search_data.pop("organization", None)
        search_data.pop("users", None)

        # TODO: handle this at the provider or core level?
        search_data["validated_data_dict"] = validated_data_dict

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

    def search_query(
        self,
        query: str,
        filters: dict[str, str | list[str]],
        sort: list[list[str]],
        additional_params: dict[str, Any],
        lang: str,
        return_ids: bool = False,
        return_entity_types: bool = False,
        return_facets: bool = False,
        limit: int = 20,
    ) -> Optional[SearchResults]:

        # Transform generic search params to Solr query params

        df = additional_params.get("df") or "text_combined"

        solr_params = {
            "q": query,
            "df": df,
        }

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

    # Backend methods

    def get_client(self) -> pysolr.Solr:

        if self._client:
            return self._client

        # TODO:
        #   Check conf at startup, handle always_commit, timeout and auth
        self._client = pysolr.Solr(config["ckan.search.solr.url"], always_commit=True)

        return self._client

    def get_admin_client(self) -> SolrSchema:

        if self._admin_client:
            return self._admin_client

        # TODO:
        #   Check conf at startup, handle always_commit, timeout and auth
        self._admin_client = SolrSchema(config["ckan.search.solr.url"])

        return self._admin_client
