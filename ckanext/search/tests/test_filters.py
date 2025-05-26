import pytest

from ckan.plugins.toolkit import ValidationError
from ckanext.search.filters import query_filters_validator, FilterOp


@pytest.mark.parametrize("filters", ["", None, {}, []])
def test_filters_no_value(filters):

    assert query_filters_validator(filters) is None


@pytest.mark.parametrize(
    "filters", [1, "a", "a,b", '{"a": "b"}', ["a"], ["a", "b"], [{"a": "b"}, "c"]]
)
def test_filters_invalid_format(filters):

    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters)

    assert (
        e.value.error_dict["filters"][0]
        == "Filters must be defined as a dict or a list of dicts"
    )


def test_filters_unknown_top_operators():

    filters = {"$maybe": [{"field1": "value1"}]}
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters)

    assert (
        e.value.error_dict["filters"][0]
        == "Unknown operators (must be one of $or, $and): $maybe"
    )


def test_filters_dollar_fields_escaped():

    filters = {"$$some_field": "some_value"}

    result = query_filters_validator(filters)
    assert result and result.field == "$some_field" and result.op == "eq"


@pytest.mark.parametrize(
    "or_filters", [1, "a", "a,b", '{"a": "b"}', ["a"], ["a", "b"], [{"a": "b"}, "c"]]
)
def test_filters_top_operators_invalid_format(or_filters):
    filters = {
        "field1": "value1",
        "$or": or_filters,
    }
    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters)

    assert (
        e.value.error_dict["filters"][0]
        == f"Filter operations must be defined as a list of dicts: {or_filters}"
    )


def test_filters_single_field():
    filters = {
        "field1": {"gte": 100},
    }
    result = query_filters_validator(filters)
    assert result == FilterOp(field="field1", op="gte", value=100)


def test_filters_single_field_shorthand():
    filters = {
        "field1": "value1",
    }
    result = query_filters_validator(filters)
    assert result == FilterOp(field="field1", op="eq", value="value1")


def test_filters_single_field_in():
    filters = {
        "field1": {"in": ["a", "b"]},
    }
    result = query_filters_validator(filters)
    assert result == FilterOp(field="field1", op="in", value=["a", "b"])


def test_filters_single_field_in_shorthand():
    filters = {
        "field1": ["a", "b"],
    }
    result = query_filters_validator(filters)
    assert result == FilterOp(field="field1", op="in", value=["a", "b"])


def test_filters_single_field_in_shorthand_with_field_operator():
    filters = {
        "field1": [10, 20, {"gte": 50, "lte": 60}, 80, 100],
    }
    result = query_filters_validator(filters)
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


def test_filters_multiple_fields_combined_as_and():
    filters = {
        "field1": "value1",
        "field2": "value2",
    }
    result = query_filters_validator(filters)
    assert result == FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
        ],
    )


def test_filters_multiple_fields_with_and_filter_op():
    filters = {
        "field1": "value1",
        "field2": "value2",
        "$and": [
            {"field3": "value3"},
            {"field4": "value4"},
        ],
    }
    result = query_filters_validator(filters)
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


def test_filters_multiple_fields_with_or_filter_op():
    filters = {
        "field1": "value1",
        "field2": "value2",
        "$or": [
            {"field3": "value3"},
            {"field4": "value4"},
        ],
    }
    result = query_filters_validator(filters)
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


def test_filters_multiple_fields_with_different_filter_ops():
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
    result = query_filters_validator(filters)
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


def test_filters_multiple_fields_with_wrong_and_filter_op():
    filters = {
        "field1": "value1",
        "$and": "wrong_filter",
    }

    with pytest.raises(ValidationError) as e:
        query_filters_validator(filters)

    assert (
        e.value.error_dict["filters"][0]
        == "Filter operations must be defined as a list of dicts: wrong_filter"
    )


def test_filters_list_of_filters_combined_as_or():
    filters = [
        {"field1": "value1"},
        {"field2": "value2"},
    ]
    result = query_filters_validator(filters)
    assert result == FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="field1", op="eq", value="value1"),
            FilterOp(field="field2", op="eq", value="value2"),
        ],
    )


def test_filters_test_nested_operators_combined():

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
    result = query_filters_validator(filters)
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


def test_filters_list_of_filters_with_or_operator():
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
    result = query_filters_validator(filters)
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


# TODO: what do we expect here?
# def test_filters_single_or():
#    filters = {
#        "$or": [
#            {"field1": "value1"},
#        ]
#    }
#    result = query_filters_validator(filters)
#    assert result == FilterOp(field="field1", op="eq", value="value1")
