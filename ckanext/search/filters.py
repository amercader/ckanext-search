"""

See doc/filters.md for the draft spec used by the validator

"""

from typing import NamedTuple, Any, Dict, List, Union, Optional

from ckan.plugins.toolkit import Invalid


class FilterOp(NamedTuple):
    op: str
    field: Optional[str]
    value: Any

    def __repr__(self) -> str:
        if (
            isinstance(self.value, list)
            and self.value
            and isinstance(self.value[0], FilterOp)
        ):
            child_reprs = []
            for child in self.value:
                child_lines = str(child).split("\n")
                indented_lines = ["    " + line for line in child_lines]
                child_reprs.append("\n".join(indented_lines))

            value_str = "[\n" + ",\n".join(child_reprs) + "\n]"
        else:
            value_str = repr(self.value)

        return (
            f"FilterOp(op={repr(self.op)}, field={repr(self.field)}, value={value_str})"
        )


FILTER_OPERATORS = ["$or", "$and"]


def _is_dict_or_list_of_dicts(value: Any) -> bool:
    return isinstance(value, dict) or _is_list_of_dicts(value)


def _is_list_of_dicts(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _check_filter_operator(key: str, value: Any) -> None:
    if key not in FILTER_OPERATORS:
        raise Invalid(f"Unknown operators (must be one of $or, $and): {key}")

    # Filter operator values must be lists of dicts
    if not _is_list_of_dicts(value):
        raise Invalid("Filter operations must be defined as a list of dicts")


def _process_filter_operator_members(value: Any) -> List[Dict[str, Any]]:

    if not isinstance(value, list):
        raise Invalid("Filter operations must contain lists of filters")

    out: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise Invalid("Filter operation members must be dictionaries")

        if len(item.keys()) > 1:
            raise Invalid("Field operation can only have one key")

        key = list(item.keys())[0]

        if key.startswith("$") and not key.startswith("$$"):
            _check_filter_operator(key, item[key])
            item[key] = _process_filter_operator_members(item[key])

            out.append(item)
        else:
            result = _process_field_operator(key, item[key])
            if "$or" in result or "$and" in result:
                out.append(result)
            else:
                item[key] = result

                out.append(item)

    return out


def _process_field_operator(field_name: str, value: Any) -> Dict[str, Any]:

    if not isinstance(value, (dict, list)):

        return {"eq": value}

    elif isinstance(value, dict):

        if len(value.keys()) > 1:
            # Combine dict filters with $and
            members = [{field_name: {k: v}} for k, v in value.items()]
            return {"$and": _process_filter_operator_members(members)}

        else:
            # Just return the filter
            # TODO: check op and value format
            return value

    elif isinstance(value, list):
        # TODO: fail if lists

        field_ops = [x for x in value if isinstance(x, dict)]
        non_field_ops = [x for x in value if x not in field_ops]

        if not field_ops:
            return {"in": value}

        members = []
        for field_op in field_ops:
            members.append(
                {"$and": [{field_name: {k: v}} for k, v in field_op.items()]}
            )

        members.append({field_name: {"in": non_field_ops}})

        return {"$or": members}


def query_filters_validator(
    value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
) -> Optional[Dict[str, Any]]:

    if not value:
        return None

    # Check structure
    if not _is_dict_or_list_of_dicts(value):
        raise Invalid("Filters must be defined as a dict or a list of dicts")

    filters = {}

    # Normalize to dict
    if isinstance(value, list):
        filters = {"$or": value}

    else:

        if len(value.keys()) == 1:

            key = list(value.keys())[0]

            if key.startswith("$") and not key.startswith("$$"):
                _check_filter_operator(key, value[key])
                filters[key] = _process_filter_operator_members(value[key])
            else:
                filters[key] = _process_field_operator(key, value[key])

        else:
            # Move individual filters to $and
            for k, v in value.items():

                if "$and" not in filters:
                    filters["$and"] = []

                filters["$and"].append({k: v})

    for op in ("$and", "$or"):
        if op in filters:
            filters[op] = _process_filter_operator_members(filters[op])

    return filters
