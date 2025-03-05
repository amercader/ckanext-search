import hashlib
import json
from typing import Any, Optional

import pysolr
from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import config

from ckanext.search.interfaces import ISearchProvider, SearchResults


class SolrSearchProvider(SingletonPlugin):

    implements(ISearchProvider, inherit=True)

    id = "solr"

    _client = None

    # ISearchProvider

    # TODO: do we need id_ or we just check the search_data dict?
    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:

        client = self.get_client()

        validated_data_dict = json.dumps(
            search_data, cls=MissingNullEncoder
        )


        search_data["index_id"] = hashlib.md5(
            b"%s%s" % (id_.encode(), config["ckan.site_id"].encode())
        ).hexdigest()

        # TODO: choose what to commit
        search_data.pop("organization", None)

        # TODO: handle this at the provider or core level?
        search_data["validated_data_dict"] = validated_data_dict

        try:
            # TODO: commit
            x = client.add(docs=[search_data])
        except pysolr.SolrError as e:
            msg = "Solr returned an error: {0}".format(
                e.args[0][:1000]  # limit huge responses
            )
            import ipdb

            ipdb.set_trace()
            # TODO: custom exception
            raise Exception(msg)
        except socket.error as e:
            assert client
            err = "Could not connect to Solr using {0}: {1}".format(client.url, str(e))
            log.error(err)
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

        solr_params = {"q": query}

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
            items.append(json.loads(doc["validated_data_dict"][0]))

        return {"count": len(items), "results": items, "facets": {}}

    # Backend methods

    def get_client(self) -> pysolr.Solr:

        if self._client:
            return self._client

        # TODO:
        #   Check conf at startup, handle always_commit, timeout and auth
        self._client = pysolr.Solr(config["ckan.search.solr.url"], always_commit=True)

        return self._client
