"""

# CKAN Query Filters spec

The goal of this specification is to provide a common syntax for defining filters
that need to be applied to queries performed. It is not tied to a particular API
endpoint or search backend, and it aims to be simple and extensible.

Filters are always provided as a dict.

The top level keys can either be:

* A field name
* A top level operator: one of `$or` or `$and`

For example:

```
"filters": {
    "field1": "value",    # exact match
    "$or": {
        "field2": ["value1", "value2"]    # or clauses
        "field3": {"gte": 9000, "lt": 10000}    # range
    }
}
```


"""

from ckan.plugins.toolkit import Invalid


def query_filters_validator(value):

    if not value:
        return

    # Check structure
    if not isinstance(value, (dict, list)) or (
        isinstance(value, list) and not all(isinstance(item, dict) for item in value)
    ):
        raise Invalid("Filters must be defined as a dict or a list of dicts")

    # Normalize to dict
    if isinstance(value, list):
        filters = {"$and": value}
    else:
        filters = value

    # Check top operators
    if unknown_top_keys := [
        k for k in filters.keys() if k.startswith("$") and not k.startswith("$$")
    ]:
        raise Invalid(
            f"Unknown operators (must be one of $or, $and): {unknown_top_keys}"
        )

    # TODO: Do we return the input as is or normalize shorthands?
    return value
