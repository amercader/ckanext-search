import pytest

from ckan.plugins.toolkit import Invalid
from ckanext.search.filters import query_filters_validator


@pytest.mark.parametrize("filters", ["", None, {}, []])
def test_filters_no_value(filters):

    assert query_filters_validator(filters) is None


@pytest.mark.parametrize("filters", [1, "a", "a,b", '{"a": "b"}'])
def test_filters_invalid_format(filters):

    with pytest.raises(Invalid) as e:
        query_filters_validator(filters)

    assert e.value.error == "Filters must be defined as a dict or a list of dicts"


@pytest.mark.parametrize("filters", [["a"], ["a", "b"], [{"a": "b"}, "c"]])
def test_filters_list_invalid_format(filters):

    with pytest.raises(Invalid) as e:
        query_filters_validator(filters)

    assert e.value.error == "Filters must be defined as a dict or a list of dicts"


def test_filters_unknown_top_operators():

    filters = {"$maybe": [{"field1": "value1"}]}
    with pytest.raises(Invalid) as e:
        query_filters_validator(filters)

    assert e.value.error == "Unknown operators (must be one of $or, $and): ['$maybe']"

def test_filters_dollar_fields_escaped():

    filters = {"$$some_field": "some_value"}

    assert "$$some_field" in query_filters_validator(filters)

