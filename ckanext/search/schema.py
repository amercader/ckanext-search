from ckanext.search.index import _get_indexing_plugins
from ckanext.search.interfaces import SearchSchema


def merge_search_schemas(schemas: list[SearchSchema]) -> SearchSchema:
    """
    Merge multiple search schemas into one, ensuring fields with the same name
    have identical properties.

    Raises ValueError if conflicting field definitions are found.
    """
    if not schemas:
        return {"version": 1, "fields": []}

    # Use the version from the first schema
    result: SearchSchema = {"version": schemas[0].get("version", 1), "fields": []}

    # Track fields we've already seen by name
    field_map = {}

    # Process all schemas
    for schema in schemas:
        for field in schema.get("fields", []):
            name = field.get("name")
            if name in field_map:
                # Check if the new field definition matches the existing one
                existing_field = field_map[name]
                # Create copies without the name for comparison
                field_copy = field.copy()
                existing_copy = existing_field.copy()
                field_name = field_copy.pop("name")
                existing_copy.pop("name")

                if field_copy != existing_copy:
                    raise ValueError(
                        f"Conflicting definitions for field '{name}': "
                        f"{existing_field} vs {field}"
                    )
            else:
                # Add new field to our result and tracking map
                field_map[name] = field
                result["fields"].append(field)

    return result


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
        # TODO: nested fields (e.g. resources)
    ],
}

DEFAULT_ORGANIZATION_SEARCH_SCHEMA: SearchSchema = {
    "version": 1,
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "entity_type", "type": "string"},
        {"name": "organization_type", "type": "string"},  # TODO: group_type?
        {"name": "name", "type": "text"},
        {"name": "title", "type": "text"},
        {"name": "description", "type": "text"},
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

    search_schemas = [
        DEFAULT_DATASET_SEARCH_SCHEMA,
        DEFAULT_ORGANIZATION_SEARCH_SCHEMA,
    ]

    combined_search_schema = merge_search_schemas(search_schemas)

    for plugin in _get_indexing_plugins():
        plugin.initialize_search_provider(combined_search_schema, clear=False)
