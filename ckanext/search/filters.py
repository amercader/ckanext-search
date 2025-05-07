"""

See doc/filters.md for the draft spec used by the validator

"""

from ckan.plugins.toolkit import Invalid


TOP_OPERATORS = ["$or", "$and"]


def _is_dict_or_list_of_dicts(value):
    return isinstance(value, (dict)) or (
        isinstance(value, list) and all(isinstance(item, dict) for item in value)
    )


def query_filters_validator(value):

    if not value:
        return

    # Check structure
    if not _is_dict_or_list_of_dicts(value):
        raise Invalid("Filters must be defined as a dict or a list of dicts")

    # Normalize to dict
    if isinstance(value, list):
        filters = {"$and": value}
    else:
        filters = value

    # Check top operators
    top_operators = [
        k for k in filters.keys() if k.startswith("$") and not k.startswith("$$")
    ]
    if unknown_top_operators := [k for k in top_operators if k not in TOP_OPERATORS]:
        raise Invalid(
            f"Unknown operators (must be one of $or, $and): {unknown_top_operators}"
        )

    # Top operator values must be lists of dicts or dicts
    for top_operator in top_operators:
        if not _is_dict_or_list_of_dicts(filters[top_operator]):
            raise Invalid(
                "Top level operations must be defined as a dict or a list of dicts"
            )

    # Individual filters should


    # TODO: Do we return the input as is or normalize shorthands?
    return value
