import pytest

from ckan.plugins.toolkit import ValidationError
from ckanext.search.filters import query_filters_validator, FilterOp


@pytest.fixture
def default_search_schema():
    return {
        "fields": [
            {"name": "field1"},
            {"name": "field2"},
            {"name": "field3"},
            {"name": "field4"},
            {"name": "field5"},
            {"name": "field6"},
            {"name": "field7"},
        ]
    }


@pytest.mark.parametrize("filters", ["", None, {}, []])
def test_filters_no_value(filters, default_search_schema):

    assert query_filters_validator(filters, default_search_schema) is None


@pytest.mark.parametrize(
    "filters", [1, "a", "a,b", '{"a": "b"}', ["a"], ["a", "b"], [{"a": "b"}, "c"]]
)
def test_filters_invalid_format(filters, default_search_schema):

    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": ["Filters must be defined as a dict or a list of dicts"]
    }


def test_filters_unknown_top_operators(default_search_schema):

    filters = {"$maybe": [{"field1": "value1"}]}
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": ["Unknown operators (must be one of $or, $and): $maybe"]
    }


def test_filters_dollar_fields_escaped():

    filters = {"$$some_field": "some_value"}
    search_schema = {"fields": [{"name": "$some_field"}]}

    result = query_filters_validator(filters, search_schema)
    assert result == FilterOp(field="$some_field", op="eq", value="some_value")


def test_filters_dollar_fields_in_operators(default_search_schema):
    search_schema = default_search_schema.copy()
    search_schema["fields"].append({"name": "$some_field"})

    filters = {"$or": [{"$$some_field": {"gt": 100}}, {"field1": "value1"}]}
    result = query_filters_validator(filters, search_schema)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="$some_field", op="gt", value=100),
            FilterOp(field="field1", op="eq", value="value1"),
        ],
    )


@pytest.mark.parametrize(
    "or_filters", [1, "a", "a,b", '{"a": "b"}', ["a"], ["a", "b"], [{"a": "b"}, "c"]]
)
def test_filters_top_operators_invalid_format(or_filters, default_search_schema):
    filters = {
        "field1": "value1",
        "$or": or_filters,
    }
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": [
            f"Filter operations must be defined as a list of dicts: {or_filters}"
        ]
    }


def test_filters_single_field(default_search_schema):
    filters = {
        "field1": {"gte": 100},
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(field="field1", op="gte", value=100)


def test_filters_single_field_shorthand(default_search_schema):
    filters = {
        "field1": "value1",
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(field="field1", op="eq", value="value1")


def test_filters_single_field_in(default_search_schema):
    filters = {
        "field1": {"in": ["a", "b"]},
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(field="field1", op="in", value=["a", "b"])


def test_filters_single_field_in_shorthand(default_search_schema):
    filters = {
        "field1": ["a", "b"],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(field="field1", op="in", value=["a", "b"])


def test_filters_single_field_in_shorthand_with_field_operator(default_search_schema):
    filters = {
        "field1": [10, 20, {"gte": 50, "lte": 60}, 80, 100],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(
                field=None,
                op="$and",
                value=[
                    FilterOp(field="field1", op="gte", value=50),
                    FilterOp(field="field1", op="lte", value=60),
                ],
            ),
            FilterOp(field="field1", op="in", value=[10, 20, 80, 100]),
        ],
    )


def test_filters_multiple_fields_combined_as_and(default_search_schema):
    filters = {
        "field1": "value1",
        "field2": "value2",
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
        ],
    )


def test_filters_multiple_fields_with_and_filter_op(default_search_schema):
    filters = {
        "field1": "value1",
        "field2": "value2",
        "$and": [
            {"field3": "value3"},
            {"field4": "value4"},
        ],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
            FilterOp(field="field3", op="eq", value="value3"),
            FilterOp(field="field4", op="eq", value="value4"),
        ],
    )


def test_filters_multiple_fields_with_or_filter_op(default_search_schema):
    filters = {
        "field1": "value1",
        "field2": "value2",
        "$or": [
            {"field3": "value3"},
            {"field4": "value4"},
        ],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
            FilterOp(
                field=None,
                op="$or",
                value=[
                    FilterOp(field="field3", op="eq", value="value3"),
                    FilterOp(field="field4", op="eq", value="value4"),
                ],
            ),
        ],
    )


def test_filters_multiple_fields_with_different_filter_ops(default_search_schema):
    filters = {
        "field1": "value1",
        "$and": [
            {"field2": {"gte": 5, "lte": 7}},
            {"field3": "value3"},
        ],
        "field4": "value4",
        "$or": [
            {"field5": "value5"},
            {"field6": "value6"},
        ],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="gte", value=5),
            FilterOp(field="field2", op="lte", value=7),
            FilterOp(field="field3", op="eq", value="value3"),
            FilterOp(field="field4", op="eq", value="value4"),
            FilterOp(
                field=None,
                op="$or",
                value=[
                    FilterOp(field="field5", op="eq", value="value5"),
                    FilterOp(field="field6", op="eq", value="value6"),
                ],
            ),
        ],
    )


def test_filters_multiple_fields_with_wrong_and_filter_op(default_search_schema):
    filters = {
        "field1": "value1",
        "$and": "wrong_filter",
    }

    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": [
            "Filter operations must be defined as a list of dicts: wrong_filter"
        ]
    }


def test_filters_list_of_filters_combined_as_or(default_search_schema):
    filters = [
        {"field1": "value1"},
        {"field2": "value2"},
    ]
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
        ],
    )


def test_filters_test_nested_operators_combined(default_search_schema):

    filters = {
        "field1": "value1",
        "$and": [
            {"field2": {"gte": 5, "lte": 7}},
            {
                "$and": [
                    {"field3": "value3"},
                    {"field4": "value4"},
                ]
            },
        ],
        "$or": [
            {"field5": "value5"},
            {
                "$or": [
                    {"field6": "value6"},
                    {"field7": "value7"},
                ]
            },
        ],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="gte", value=5),
            FilterOp(field="field2", op="lte", value=7),
            FilterOp(field="field3", op="eq", value="value3"),
            FilterOp(field="field4", op="eq", value="value4"),
            FilterOp(
                field=None,
                op="$or",
                value=[
                    FilterOp(field="field5", op="eq", value="value5"),
                    FilterOp(field="field6", op="eq", value="value6"),
                    FilterOp(field="field7", op="eq", value="value7"),
                ],
            ),
        ],
    )


def test_filters_nested_operators(default_search_schema):
    filters = {
        "$or": [
            {"field1": "value1"},
            {
                "$and": [
                    {"field2": {"gte": 10, "lte": 20}},
                    {
                        "$or": [
                            {"field3": ["a", "b", "c"]},
                            {"$and": [{"field4": {"lt": 5}}, {"field5": "value5"}]},
                        ]
                    },
                ]
            },
        ]
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(
                field=None,
                op="$and",
                value=[
                    FilterOp(field="field2", op="gte", value=10),
                    FilterOp(field="field2", op="lte", value=20),
                    FilterOp(
                        field=None,
                        op="$or",
                        value=[
                            FilterOp(field="field3", op="in", value=["a", "b", "c"]),
                            FilterOp(
                                field=None,
                                op="$and",
                                value=[
                                    FilterOp(field="field4", op="lt", value=5),
                                    FilterOp(field="field5", op="eq", value="value5"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def test_filters_multiple_top_level_operators(default_search_schema):
    filters = {
        "$or": [{"field1": "value1"}, {"field2": "value2"}],
        "$and": [{"field3": "value3"}, {"field4": "value4"}],
    }
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(
                field=None,
                op="$or",
                value=[
                    FilterOp(field="field1", op="eq", value="value1"),
                    FilterOp(field="field2", op="eq", value="value2"),
                ],
            ),
            FilterOp(field="field3", op="eq", value="value3"),
            FilterOp(field="field4", op="eq", value="value4"),
        ],
    )


def test_filters_list_of_filters_with_or_operator(default_search_schema):
    filters = [
        {"field1": "value1"},
        {"field2": "value2"},
        {
            "$or": [
                {"field3": "value3"},
                {"field4": "value4"},
            ]
        },
    ]
    result = query_filters_validator(filters, default_search_schema)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
            FilterOp(field="field3", op="eq", value="value3"),
            FilterOp(field="field4", op="eq", value="value4"),
        ],
    )


def test_filters_unknown_field_single_field(default_search_schema):
    filters = {"random_field": {"eq": "value"}}
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {"filters": ["Unknown field: random_field"]}


def test_filters_unknown_field_single_field_shorthand(default_search_schema):
    filters = {"random_field": "value"}
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {"filters": ["Unknown field: random_field"]}


def test_filters_unknown_field_filter_op(default_search_schema):
    filters = {"$or": [{"field1": "value1"}, {"random_field": "value"}]}
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {"filters": ["Unknown field: random_field"]}


def test_filters_unknown_field_multiple_filter_op(default_search_schema):
    filters = {
        "$or": [
            {"random_field1": "value"},
            {"$and": [{"random_field2": "value"}, {"field1": "value1"}]},
        ]
    }
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": [
            "Unknown field: random_field1",
            "Unknown field: random_field2",
        ]
    }


def test_filters_different_errors(default_search_schema):
    filters = {
        "$or": [
            {"random_field1": "value"},
            {"$and": [{"random_field2": "value"}, {"$or": ["wrong_format"]}]},
        ]
    }
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters, default_search_schema)

    assert e.value.error_dict == {
        "filters": [
            "Unknown field: random_field1",
            "Unknown field: random_field2",
            "Filter operation members must be dictionaries: wrong_format",
        ]
    }


# TODO: what do we expect here?
# def test_filters_single_or(default_search_schema):
#    """Test that a single item in an $or operator works correctly."""
#    filters = {
#        "$or": [
#            {"field1": "value1"},
#        ]
#    }
#    result = query_filters_validator(filters, default_search_schema)
#    assert result == FilterOp(field="field1", op="eq", value="value1")
#
#
# def test_filters_single_and(default_search_schema):
#    """Test that a single item in an $and operator works correctly."""
#    filters = {
#        "$and": [
#            {"field1": "value1"},
#        ]
#    }
#    result = query_filters_validator(filters, default_search_schema)
#    assert result == FilterOp(field="field1", op="eq", value="value1")
