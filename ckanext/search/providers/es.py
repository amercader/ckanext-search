import hashlib
import json
import logging
from typing import Any, Optional

from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config
from elasticsearch import Elasticsearch

from ckanext.search.interfaces import ISearchProvider, SearchResults, SearchSchema

log = logging.getLogger(__name__)


class ElasticSearchProvider(SingletonPlugin):

    implements(ISearchProvider, inherit=True)

    id = "elasticsearch"

    _client = None

    _index_name = ""

    def __init__(self, *args: Any, **kwargs: Any):

        super().__init__(*args, **kwargs)

        # TODO: config declaration
        self._index_name = config.get("ckan.search.elasticsearch.index_name", "ckan")

    # ISearchProvider

    def initialize_search_provider(
        self, search_schema: SearchSchema, clear: bool
    ) -> None:

        client = self.get_client()
        # Check if index exists, create otherwise
        if not client.indices.exists(index=self._index_name):

            # TODO: what else do we need?
            params = {"index": self._index_name, "mappings": {"dynamic": "false"}}

            client.indices.create(**params)
            log.info("Created new index '%s'" % self._index_name)

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

        client.indices.put_mapping(index=self._index_name, body=mapping)
        log.info("Updated index with mapping")

    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:
        # TODO: provider specific params

        client = self.get_client()

        index_id = id_

        # TODO: choose what to commit
        search_data.pop("organization", None)
        # TODO: refresh
        client.index(
            index=self._index_name, id=index_id, document=search_data, refresh="true"
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

    def clear_index(self) -> None:

        client = self.get_client()
        # TODO: review bulk, versions, slices, etc
        # TODO: wait for completion
        client.delete_by_query(
            q="*:*", index=self._index_name, wait_for_completion=True
        )
        log.info("Cleared all documents in the search index")

    # Provider methods

    def get_client(self) -> Elasticsearch:

        if self._client:
            return self._client

        es_config = {}
        if ca_certs_path := config["ckan.search.elasticsearch.ca_certs_path"]:
            es_config["ca_certs"] = ca_certs_path

        if password := config["ckan.search.elasticsearch.password"]:
            es_config["basic_auth"] = ("elastic", password)

        # TODO: review config needed, check on startup
        self._client = Elasticsearch(
            config["ckan.search.elasticsearch.url"], **es_config
        )

        return self._client
