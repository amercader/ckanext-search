import hashlib
import json
from typing import Any, Optional

from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config
from elasticsearch import Elasticsearch

from ckanext.search.interfaces import ISearchProvider, SearchResults


class ElasticSearchProvider(SingletonPlugin):

    implements(ISearchProvider, inherit=True)

    id = "elasticsearch"

    _client = None

    # ISearchProvider

    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:

        client = self.get_client()

        validated_data_dict = json.dumps(
            search_data, cls=MissingNullEncoder
        )

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
