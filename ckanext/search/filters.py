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

# How deeply nested filter operations can be
MAX_FILTER_OPS_DEPTH = 10

# Maximum number of filter operations
MAX_FILTER_OPS_NUM = 100


class FilterOp(NamedTuple):
    op: str
    field: Optional[str]
    value: Any

    def op_count(self) -> int:

        count = 1  # Count this operation

        if isinstance(self.value, list):
            for item in self.value:
                if isinstance(item, FilterOp):
                    count += item.op_count()
        return count

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


class FiltersParser:

    search_schema: dict = {}
    filters: Optional[FilterOp] = None
    errors: Optional[list[str]] = None
    total_ops: int = 0

    def __init__(
        self,
        input_value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
        search_schema: dict,
    ) -> None:

        self.search_schema = search_schema

        self.filters, self.errors = self._parse_query_filters(
            input_value, search_schema
        )

    def _validate_field_operator(
        self, field_name: str, operator: str, value: Any, search_schema: dict
    ) -> Optional[List[str]]:

        if field_name not in search_schema["fields"].keys():
            return [f"Unknown field: {field_name}"]

        # TODO: check value depending on operation and field type

    def _is_dict_or_list_of_dicts(self, value: Any) -> bool:
        return isinstance(value, dict) or self._is_list_of_dicts(value)

    def _is_list_of_dicts(self, value: Any) -> bool:
        return isinstance(value, list) and all(isinstance(item, dict) for item in value)

    def _check_filter_operator(self, key: str, value: Any) -> Optional[str]:
        if key not in FILTER_OPERATORS:
            return f"Unknown operators (must be one of $or, $and): {key}"

        # Filter operator values must be lists of dicts
        if not self._is_list_of_dicts(value):
            return f"Filter operations must be defined as a list of dicts: {value}"

    def _new_filter_op(self, *args, **kwargs) -> FilterOp:
        self.total_ops += 1
        if self.total_ops > MAX_FILTER_OPS_NUM:
            raise ValidationError(
                {"filters": ["Maximum number of filter operations exceeded"]}
            )
        return FilterOp(*args, **kwargs)

    def _combine_filter_operator_members(
        self,
        value: Any,
        parent_operator: str,
        search_schema: dict,
        nesting_level: int,
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
        child_filters, errors = self._process_filter_operator_members(
            value, parent_operator, search_schema, nesting_level + 1
        )

        if errors:
            return None, errors
        elif child_filters:
            out = self._combine_filter_operations(child_filters, parent_operator)

            return out, None

        return None, None

    def _combine_filter_operations(
        self, filter_ops: List[FilterOp], parent_operator: str
    ) -> List[FilterOp]:
        combined_filters = []
        for filter_ in filter_ops:
            if filter_.op == parent_operator and parent_operator in COMBINE_OPERATORS:
                combined_filters.extend(filter_.value)
            else:
                combined_filters.append(filter_)

        return combined_filters

    def _process_filter_operator_members(
        self,
        value: List[dict],
        parent_operator: str,
        search_schema: dict,
        nesting_level: int,
    ) -> tuple[Optional[List[FilterOp]], Optional[List[str]]]:

        if nesting_level >= MAX_FILTER_OPS_DEPTH:
            raise ValidationError(
                {"filters": ["Maximum nesting depth for filter operations reached"]}
            )

        if not isinstance(value, list):
            return None, [f"Filter operations must contain lists of filters: {value}"]

        out: List[FilterOp] = []
        errors = []

        for item in value:
            if not isinstance(item, dict):
                errors.append(
                    f"Filter operation members must be dictionaries: {item!r}"
                )
                continue

            # Process each key and combine with AND
            child_ops = []

            if len(item.keys()) >= MAX_FILTER_OPS_NUM:
                raise ValidationError(
                    {"filters": ["Maximum number of filter operations exceeded"]}
                )

            for key in item.keys():

                if key.startswith("$") and not key.startswith("$$"):
                    # Handle operator key
                    op_errors = self._check_filter_operator(key, item[key])
                    if op_errors:
                        errors.append(op_errors)
                        continue

                    child_ops_for_key, child_errors = (
                        self._combine_filter_operator_members(
                            item[key],
                            key,
                            search_schema,
                            nesting_level,
                        )
                    )

                    if child_errors:
                        errors.extend(child_errors)
                        continue

                    child_ops.append(
                        self._new_filter_op(
                            op=key,
                            field=None,
                            value=child_ops_for_key,
                        )
                    )
                else:
                    # Handle field key
                    field_op, field_errors = self._process_field_operator(
                        key, item[key], search_schema
                    )

                    if field_errors:
                        errors.extend(field_errors)
                    elif field_op:
                        child_ops.append(field_op)

            if len(child_ops) == 1:
                out.append(child_ops[0])
            else:
                out.append(
                    self._new_filter_op(
                        field=None,
                        op=AND,
                        value=self._combine_filter_operations(child_ops, AND),
                    )
                )

        return out, errors

    def _check_field_operator(
        self, field_name: str, op: str, value: Any, search_schema: dict
    ) -> tuple[Optional[FilterOp], Optional[List[str]]]:

        errors = self._validate_field_operator(field_name, op, value, search_schema)
        if errors:
            return None, errors
        else:
            return self._new_filter_op(field=field_name, op=op, value=value), None

    def _process_field_operator(
        self,
        field_name: str,
        value: Any,
        search_schema: dict,
    ) -> tuple[Optional[FilterOp], Optional[List[str]]]:

        if field_name.startswith("$$"):
            field_name = field_name[1:]

        if not isinstance(value, (dict, list)):
            return self._check_field_operator(field_name, "eq", value, search_schema)

        elif isinstance(value, dict):

            if len(value.keys()) > 1:
                # Combine dict filters with $and
                child_ops = []
                errors = []
                for k, v in value.items():
                    field_op, field_errors = self._process_field_operator(
                        field_name, {k: v}, search_schema
                    )
                    if field_errors:
                        errors.extend(field_errors)
                    else:
                        child_ops.append(field_op)

                if errors:
                    return None, errors
                else:
                    out = self._new_filter_op(op=AND, field=None, value=child_ops)
                    return out, None

            else:
                # Just return the filter

                op = list(value.keys())[0]

                return self._check_field_operator(
                    field_name, op, value[op], search_schema
                )

        elif isinstance(value, list):
            # TODO: fail if lists

            field_ops = [x for x in value if isinstance(x, dict)]
            non_field_ops = [x for x in value if x not in field_ops]

            if not field_ops:
                return self._new_filter_op(field=field_name, op="in", value=value), None

            members = []
            errors = []

            for field_op in field_ops:

                field_op, field_errors = self._process_field_operator(
                    field_name, field_op, search_schema
                )
                if field_errors:
                    errors.extend(field_errors)
                    continue
                else:
                    members.append(field_op)

            members.append(
                self._new_filter_op(field=field_name, op="in", value=non_field_ops)
            )

            if errors:
                return None, errors
            else:
                out = self._new_filter_op(op=OR, field=None, value=members)
                return out, None

    def _parse_query_filters(
        self,
        input_value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
        search_schema: dict,
    ) -> tuple[Optional[FilterOp], Optional[List[str]]]:

        if not input_value:
            return None, None

        # Check structure
        if not self._is_dict_or_list_of_dicts(input_value):
            raise ValidationError(
                {"filters": ["Filters must be defined as a dict or a list of dicts"]}
            )

        filters: Optional[FilterOp] = None
        errors = []

        if isinstance(input_value, list):
            # Filters provided as a list of dicts

            if len(input_value) >= MAX_FILTER_OPS_NUM:
                raise ValidationError(
                    {"filters": ["Maximum number of filter operations exceeded"]}
                )

            child_ops, errors = self._combine_filter_operator_members(
                input_value, OR, search_schema, nesting_level=0
            )

            if child_ops:
                filters = self._new_filter_op(
                    op=OR,
                    field=None,
                    value=child_ops,
                )

        else:
            # Filters provided as a dict

            child_filters = []

            if len(input_value.keys()) >= MAX_FILTER_OPS_NUM:
                raise ValidationError(
                    {"filters": ["Maximum number of filter operations exceeded"]}
                )

            for key, value in input_value.items():
                if key.startswith("$") and not key.startswith("$$"):
                    # Handle Filter Operators (e.g. $or, $and)

                    op_errors = self._check_filter_operator(key, value)
                    if op_errors:
                        errors.append(op_errors)
                        continue

                    child_ops, child_errors = self._combine_filter_operator_members(
                        value, key, search_schema, nesting_level=0
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
                                self._new_filter_op(
                                    op=key,
                                    field=None,
                                    value=child_ops,
                                )
                            )

                else:
                    # Handle Field Operators (e.g. {"field": "value"})
                    field_op, field_errors = self._process_field_operator(
                        key, value, search_schema
                    )

                    if field_errors:
                        errors.extend(field_errors)
                    else:
                        child_filters.append(field_op)

            if not errors and len(child_filters) > 1:
                filters = self._new_filter_op(op=AND, field=None, value=child_filters)
            elif not errors and len(child_filters) == 1:
                filters = child_filters[0]

        return filters, errors


def parse_query_filters(
    input_value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    search_schema: dict,
) -> Optional[FilterOp]:

    if not input_value:
        return None

    parser = FiltersParser(input_value, search_schema)

    if parser.errors:
        raise ValidationError({"filters": parser.errors})

    return parser.filters
