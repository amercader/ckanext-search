# This will eventually live in CKAN core
from typing import Any, Iterable, Optional, TypedDict

from ckan.plugins.interfaces import Interface


class SearchSchema(TypedDict, total=False):
    """Type definition for search schema"""
    version: int
    fields: list[dict[str, Any]]  # field properties like type, repeating, etc.


class SearchResults(TypedDict, total=False):
    """Type definition for search results"""

    count: int
    results: list[dict[str, Any]]
    facets: dict[str, Any]


class ISearchProvider(Interface):

    def search_query(
        self,
        q: str,  # e.g. 'water data'
        filters: dict[
            str, str | list[str]
        ],  # e.g. {'metadata_modified<': '2024-01-01', 'entity_type': ['package']}
        sort: list[list[str]],  # e.g. [['title'], ['metadata_modified', 'desc']]
        additional_params: dict[
            str, Any
        ],  # custom parameters this provider may process or ignore
        # TODO: config
        lang: str,  # for text query language stemming e.g. 'de'
        return_ids: bool = False,  # True: return records as ids (may increase maximum record limit)
        return_entity_types: bool = False,  # True: wrap records with {'entity_type': et, 'data': record} objects
        return_facets: bool = False,  # True: return facet counts for available indexes
        # TODO: config
        limit: int = 20,  # maximum records to return, None: maximum provider allows
        start: int = 0,
    ) -> Optional[SearchResults]:
        """generate search results or return None if another provider
        should be used for the query"""

    # TODO: what is clear used for?
    def initialize_search_provider(
        self, combined_schema: SearchSchema, clear: bool
    ) -> None:
        """create or update indexes for fields based on combined search
        schema containing all field names, types and repeating state"""

    def index_search_record(
        self, entity_type: str, id_: str, search_data: dict[str, str | list[str]]
    ) -> None:
        "create or update search data record in index"

    def delete_search_record(self, entity_type: str, id_: str) -> None:
        "remove record from index"

    # TODO: clear just one entity type
    def clear_index(self) -> None:
        """Clear all documents from the index"""


class ISearchFeature:
    def entity_types(self) -> list[str]:
        "return list of entity types covered by this feature"
        pass

    def search_schema(self) -> SearchSchema:
        """return index fields names, their types (text, str, date, numeric)
        and whether they are repeating"""

    def format_search_data(
        self, entity_type: str, data: dict[str:Any]
    ) -> dict[str, str | list[str]]:
        """convert data for this entity type to search data suitable to be
        passed to the search provider index method"""

    def existing_record_ids(self, entity_type: str) -> Iterable[str]:
        """return a list or iterable of all record ids for the given entity type
        managed by this feature. Return an empty list for core entity
        types like 'package' or entity types managed by another feature.
        This method is used to identify missing and orphan records in the
        search index"""

    def fetch_records(
        self, entity_type: str, records: Optional[Iterable[str]]
    ) -> Iterable[dict[str, Any]]:
        """generator of all records for this entity type managed by this
        feature, or only records for the ids passed if not None.
        This method is used to rebuild all or some records in the search
        index"""
