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
            f"FilterOp(field={repr(self.field)}, op={repr(self.op)}, value={value_str})"
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


def _process_filter_operator_members(value: Any) -> List[FilterOp]:

    if not isinstance(value, list):
        raise Invalid("Filter operations must contain lists of filters")

    out: List[FilterOp] = []
    for item in value:
        if not isinstance(item, dict):
            raise Invalid("Filter operation members must be dictionaries")

        if len(item.keys()) > 1:
            raise Invalid("Field operation can only have one key")

        key = list(item.keys())[0]

        if key.startswith("$") and not key.startswith("$$"):
            _check_filter_operator(key, item[key])

            out.append(
                FilterOp(
                    op=key,
                    field=None,
                    value=_process_filter_operator_members(item[key]),
                )
            )
        else:
            out.append(_process_field_operator(key, item[key]))

    return out


def _process_field_operator(field_name: str, value: Any) -> FilterOp:

    if field_name.startswith("$$"):
        field_name = field_name[1:]

    if not isinstance(value, (dict, list)):

        return FilterOp(field=field_name, op="eq", value=value)

    elif isinstance(value, dict):

        if len(value.keys()) > 1:
            # Combine dict filters with $and
            child_ops = []
            for k, v in value.items():
                child_ops.append(_process_field_operator(field_name, {k: v}))

            return FilterOp(op="$and", field=None, value=child_ops)

        else:
            # Just return the filter
            # TODO: check op and value format

            op = list(value.keys())[0]

            return FilterOp(field=field_name, op=op, value=value[op])

    elif isinstance(value, list):
        # TODO: fail if lists

        field_ops = [x for x in value if isinstance(x, dict)]
        non_field_ops = [x for x in value if x not in field_ops]

        if not field_ops:
            return FilterOp(field=field_name, op="in", value=value)

        members = []

        for field_op in field_ops:
            members.append(_process_field_operator(field_name, field_op))

        members.append(FilterOp(field=field_name, op="in", value=non_field_ops))

        return FilterOp(op="$or", field=None, value=members)


def query_filters_validator(
    input_value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
) -> Optional[FilterOp]:

    if not input_value:
        return None

    # Check structure
    if not _is_dict_or_list_of_dicts(input_value):
        raise Invalid("Filters must be defined as a dict or a list of dicts")

    filters: Optional[FilterOp] = None

    if isinstance(input_value, list):

        filters = FilterOp(
            op="$or", field=None, value=_process_filter_operator_members(input_value)
        )

    else:
        child_filters = []
        for key, value in input_value.items():
            if key.startswith("$") and not key.startswith("$$"):

                _check_filter_operator(key, value)

                if key == "$and":
                    # Just add child filters to the root $and
                    child_filters.extend(_process_filter_operator_members(value))
                else:
                    child_filters.append(
                        FilterOp(
                            op=key,
                            field=None,
                            value=_process_filter_operator_members(value),
                        )
                    )

            else:
                child_filters.append(_process_field_operator(key, value))

        if len(child_filters) > 1:
            filters = FilterOp(op="$and", field=None, value=child_filters)
        elif len(child_filters) == 1:
            filters = child_filters[0]

    return filters
