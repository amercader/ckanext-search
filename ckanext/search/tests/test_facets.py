import pytest

from ckan.tests.helpers import call_action
from ckan.plugins import toolkit

pytestmark = [
    pytest.mark.usefixtures("with_plugins"),
    pytest.mark.ckan_config("ckan.search.search_provider", "test-provider"),
]


def test_standard_params(mock_search_plugins):
    call_action(
        "search",
        facets={"field": ["type"], "mincount": 2, "limit": 20},
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["facets"] == {"field": ["type"], "mincount": 2, "limit": 20}


def test_standard_params_as_string(mock_search_plugins):
    call_action(
        "search",
        facets='{"field": ["type"], "mincount": 2, "limit": 20}',
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["facets"] == {"field": ["type"], "mincount": 2, "limit": 20}


def test_field_key_transformed_to_list(mock_search_plugins):
    call_action(
        "search",
        facets={"field": "type"},
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["facets"] == {"field": ["type"]}


def test_facets_wrong_format(mock_search_plugins):

    with pytest.raises(toolkit.ValidationError) as exc_info:
        call_action(
            "search",
            facets={"field": {"not": "right"}},
        )

    assert exc_info.value.error_dict["facets"] == ["facets.field: Not a list"]


def test_facets_unknown_parameters(mock_search_plugins):

    with pytest.raises(toolkit.ValidationError) as exc_info:
        call_action(
            "search",
            facets={"field": "type", "not": "known"},
        )

    assert exc_info.value.error_dict["facets"] == [
        "Unknown parameters: {'not': 'known'}"
    ]
