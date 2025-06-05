from typing import Any

from ckan.plugins.toolkit import validator_args

from ckan.types import (
    Schema,
    Validator,
    ValidatorFactory,
    FlattenKey,
    FlattenDataDict,
    FlattenErrorDict,
    Context,
)

from ckan.plugins.toolkit import ValidationError
from ckanext.search.filters import parse_query_filters
from ckanext.search.schema import get_search_schema


def query_filters_validator(search_schema) -> Validator:

    def callable(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ) -> Any:

        value = data.get(key)

        try:
            data[key] = parse_query_filters(value, search_schema)
        except ValidationError as e:
            errors[key] = e.error_dict["filters"]

    return callable


@validator_args
def default_search_query_schema(
    ignore_missing: Validator,
    ignore_empty: Validator,
    remove_whitespace: Validator,
    unicode_safe: Validator,
    list_of_strings: Validator,
    json_list_or_string: Validator,
    natural_number_validator: Validator,
    convert_to_json_if_string: Validator,
    convert_to_list_if_string: Validator,
    limit_to_configured_maximum: ValidatorFactory,
    default: ValidatorFactory,
) -> Schema:

    return {
        "q": [ignore_missing, unicode_safe],
        "limit": [
            default(10),
            natural_number_validator,
            limit_to_configured_maximum("ckan.search.rows_max", 1000),
        ],
        "sort": [ignore_missing, json_list_or_string],
        # TODO: index value based ordering
        "start": [ignore_missing, ignore_empty, natural_number_validator],
        "filters": [
            ignore_missing,
            convert_to_json_if_string,
            query_filters_validator(get_search_schema()),
        ],
        "lang": [ignore_missing],
    }
