import hashlib
import json
import logging
from typing import Any, Optional

from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config
from elasticsearch import Elasticsearch

from ckanext.search.interfaces import (ISearchProvider, SearchResults,
                                       SearchSchema)

log = logging.getLogger(__name__)


class ElasticSearchProvider(SingletonPlugin):

    implements(ISearchProvider, inherit=True)

    id = "elasticsearch"

    _client = None

    # ISearchProvider

    def initialize_search_provider(
        self, search_schema: SearchSchema, clear: bool
    ) -> None:

        client = self.get_client()

        # Check if index exists, create otherwise
        if not client.indices.exists(index="ckan"):

            # TODO: what else do we need?
            params = {"index": "ckan", "mappings": {"dynamic": "false"}}

            client.indices.create(**params)
            log.info("Created new index 'ckan'")

        # Translate common search schema format to ES format
        es_field_types = {
            "string": "keyword",
            "bool": "boolean",
        }

        mapping = {"properties": {}}
        for field in search_schema["fields"]:

            field_name = field.pop("name")
            field_type = field.pop("type")

            if field_type in es_field_types:
                field_type = es_field_types[field_type]

            # All fields are multivalued by default
            mapping["properties"][field_name] = {
                "type": field_type,
                "index": field.get("indexed", True),
                "store": field.get("stored", False),
            }
            log.info(
                f"Added field '{field_name}' to index, with type {field_type} and params {field}"
            )

        client.indices.put_mapping(index="ckan", body=mapping)
        log.info("Updated index with mapping")

    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:

        client = self.get_client()

        validated_data_dict = json.dumps(search_data, cls=MissingNullEncoder)

        index_id = hashlib.md5(
            b"%s%s" % (id_.encode(), config["ckan.site_id"].encode())
        ).hexdigest()

        # TODO: choose what to commit
        search_data.pop("organization", None)

        # TODO: handle this at the provider or core level?
        search_data["validated_data_dict"] = validated_data_dict

        client.index(
            index="ckan",
            id=index_id,
            document=search_data,
        )

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

        # Transform generic search params to Elastic Search query params

        # TODO: Use ES query DSL
        es_params = {"q": query}

        client = self.get_client()

        # TODO: error handling
        es_response = client.search(**es_params)

        items = []
        for doc in es_response["hits"]["hits"]:
            doc = doc["_source"]
            # TODO allow to choose validated/not validated? i.e use_default_schema
            items.append(json.loads(doc["validated_data_dict"]))

        return {"count": len(items), "results": items, "facets": {}}

    # Provider methods

    def get_client(self) -> Elasticsearch:

        if self._client:
            return self._client

        # TODO: review config needed, check on startup
        self._client = Elasticsearch(
            config["ckan.search.elasticsearch.url"],
            ca_certs=config["ckan.search.elasticsearch.ca_certs_path"],
            basic_auth=("elastic", config["ckan.search.elasticsearch.password"]),
        )

        return self._client
