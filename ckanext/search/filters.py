"""

See doc/filters.md for the draft spec used by the validator

"""

from typing import NamedTuple, Any, Dict, List, Union, Optional

from ckan.plugins.toolkit import ValidationError


OR = "$or"
AND = "$and"

# TODO: allow plugins to extend these
FILTER_OPERATORS = [OR, AND]

# Nested operators of these types will be merged
COMBINE_OPERATORS = [OR, AND]


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


def _is_dict_or_list_of_dicts(value: Any) -> bool:
    return isinstance(value, dict) or _is_list_of_dicts(value)


def _is_list_of_dicts(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _check_filter_operator(key: str, value: Any) -> Optional[str]:
    if key not in FILTER_OPERATORS:
        return f"Unknown operators (must be one of $or, $and): {key}"

    # Filter operator values must be lists of dicts
    if not _is_list_of_dicts(value):
        return f"Filter operations must be defined as a list of dicts: {value}"


def _combine_filter_operator_members(
    value: Any, parent_operator: str
) -> tuple[Optional[List[FilterOp]], Optional[List[str]]]:
    """
    Combine child operator members of the same type, e.g.:

    {
        "$and": [
            {"field1": "value1"},
            {
                "$and": [
                    {"field2": "value2"},
                    {"$and": [
                        {"field3": "value3"},
                        {"field4": "value4"}
                        ]
                    },
                ]
            },
        ]
    }

    will generate a single $and filter:

        FilterOp(
            field=None,
            op="$and",
            value=[
                FilterOp(field="field1", op="eq", value="value1"),
                FilterOp(field="field2", op="eq", value="value2"),
                FilterOp(field="field3", op="eq", value="value3"),
                FilterOp(field="field4", op="eq", value="value4"),
            ],
        )
    """
    child_filters, errors = _process_filter_operator_members(value, parent_operator)

    if errors:
        return None, errors
    elif child_filters:
        combined_filters = []
        for filter_ in child_filters:
            if filter_.op == parent_operator and parent_operator in COMBINE_OPERATORS:
                combined_filters.extend(filter_.value)
            else:
                combined_filters.append(filter_)

        return combined_filters, None

    return None, None


def _process_filter_operator_members(
    value: Any, parent_operator: str
) -> tuple[Optional[List[FilterOp]], Optional[List[str]]]:

    if not isinstance(value, list):
        return None, [f"Filter operations must contain lists of filters: {value}"]

    out: List[FilterOp] = []
    errors = []
    for item in value:
        if not isinstance(item, dict):
            errors.append(f"Filter operation members must be dictionaries: {item}")

        elif len(item.keys()) > 1:

            errors.append(f"Filter operations can only have one key: {item}")

        if errors:
            return None, errors

        key = list(item.keys())[0]

        if key.startswith("$") and not key.startswith("$$"):
            op_errors = _check_filter_operator(key, value)
            if op_errors:
                errors.append(op_errors)
                continue

            child_ops, child_errors = _combine_filter_operator_members(item[key], key)

            if child_errors:
                errors.extend(child_errors)
                continue

            out.append(
                FilterOp(
                    op=key,
                    field=None,
                    value=child_ops,
                )
            )
        else:
            field_op, field_errors = _process_field_operator(key, item[key])
            if field_errors:
                errors.extend(field_errors)
            elif field_op:
                out.append(field_op)

    return out, errors


def _process_field_operator(
    field_name: str, value: Any
) -> tuple[Optional[FilterOp], Optional[List[str]]]:

    if field_name.startswith("$$"):
        field_name = field_name[1:]

    if not isinstance(value, (dict, list)):

        return FilterOp(field=field_name, op="eq", value=value), None

    elif isinstance(value, dict):

        if len(value.keys()) > 1:
            # Combine dict filters with $and
            child_ops = []
            errors = []
            for k, v in value.items():
                field_op, field_errors = _process_field_operator(field_name, {k: v})
                if field_errors:
                    errors.extend(field_errors)
                else:
                    child_ops.append(field_op)

            if errors:
                return None, errors
            else:
                return FilterOp(op=AND, field=None, value=child_ops), None

        else:
            # Just return the filter
            # TODO: check op and value format
            errors = []

            op = list(value.keys())[0]

            return FilterOp(field=field_name, op=op, value=value[op]), errors

    elif isinstance(value, list):
        # TODO: fail if lists

        field_ops = [x for x in value if isinstance(x, dict)]
        non_field_ops = [x for x in value if x not in field_ops]

        if not field_ops:
            return FilterOp(field=field_name, op="in", value=value), None

        members = []
        errors = []

        for field_op in field_ops:

            field_op, field_errors = _process_field_operator(field_name, field_op)
            if field_errors:
                errors.extend(field_errors)
            else:
                members.append(field_op)

        members.append(FilterOp(field=field_name, op="in", value=non_field_ops))

        if errors:
            return None, errors
        else:
            return FilterOp(op=OR, field=None, value=members), None


def query_filters_validator(
    input_value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
) -> Optional[FilterOp]:

    if not input_value:
        return None

    # Check structure
    if not _is_dict_or_list_of_dicts(input_value):
        raise ValidationError(
            {"filters": ["Filters must be defined as a dict or a list of dicts"]}
        )

    filters: Optional[FilterOp] = None
    errors = []

    if isinstance(input_value, list):
        # Filters provided as a list of dicts

        child_ops, errors = _combine_filter_operator_members(input_value, OR)

        if child_ops:
            filters = FilterOp(
                op=OR,
                field=None,
                value=child_ops,
            )

    else:
        # Filters provided as a dict

        child_filters = []

        for key, value in input_value.items():
            if key.startswith("$") and not key.startswith("$$"):
                # Handle Filter Operators (e.g. $or, $and)

                op_errors = _check_filter_operator(key, value)
                if op_errors:
                    errors.append(op_errors)
                    continue

                child_ops, child_errors = _combine_filter_operator_members(
                    value, key
                )

                if child_errors:
                    errors.extend(child_errors)
                    continue
                elif child_ops:

                    if key == AND:
                        # Just add child filters to the root $and
                        child_filters.extend(child_ops)
                    else:
                        child_filters.append(
                            FilterOp(
                                op=key,
                                field=None,
                                value=child_ops,
                            )
                        )

            else:
                # Handle Field Operators (e.g. {"field": "value"})
                field_op, field_errors = _process_field_operator(key, value)

                if not field_errors:
                    child_filters.append(field_op)

        if not errors and len(child_filters) > 1:
            filters = FilterOp(op=AND, field=None, value=child_filters)
        elif not errors and len(child_filters) == 1:
            filters = child_filters[0]

    if errors:
        raise ValidationError({"filters": errors})

    return filters
