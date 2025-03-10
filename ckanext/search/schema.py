from ckanext.search.interfaces import SearchSchema
from ckanext.search.index import _get_indexing_plugins

DEFAULT_DATASET_SEARCH_SCHEMA: SearchSchema = {
    "version": 1,
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "entity_type", "type": "string"},
        {"name": "dataset_type", "type": "string"},
        {"name": "name", "type": "text"},
        {"name": "title", "type": "text"},
        {"name": "notes", "type": "text"},
        {"name": "tags", "type": "string", "multiple": True},
        {"name": "groups", "type": "string", "multiple": True},
        {"name": "organization", "type": "string"},
        {"name": "private", "type": "bool"},
        {"name": "metadata_created", "type": "date"},
        {"name": "metadata_modified", "type": "date"},
        {"name": "permission_labels", "type": "string", "multiple": True},
        {
            "name": "validated_data_dict",
            "type": "string",
            "indexed": False,
            "stored": True,
        },
    ],
}


def init_schema():

    # TODO: combine different entities, schemas provided by extensions

    # TODO: validate with navl
    search_schema = DEFAULT_DATASET_SEARCH_SCHEMA

    for plugin in _get_indexing_plugins():
        plugin.initialize_search_provider(search_schema, clear=False)
