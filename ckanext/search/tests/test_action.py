import pytest
from unittest import mock

import ckan.plugins as plugins
from ckan.plugins import toolkit
from ckan.tests import helpers

from ckanext.search.interfaces import ISearchFeature, ISearchProvider

from ckanext.search.filters import FilterOp


pytestmark = [
    pytest.mark.usefixtures("with_plugins"),
    pytest.mark.ckan_config("ckan.search.search_provider", "test-provider"),
]


class MockSearchFeature:

    def before_query(self, query_dict):
        pass

    def after_query(self, query_results, query_dict):
        pass

    def search_query_schema(self):
        return {
            "custom_param": [],
        }


class MockSearchProvider:

    id = "test-provider"

    def search_query_schema(self):
        return {
            "qf": [],
            "df": [],
        }

    search_query = mock.MagicMock()


@pytest.fixture
def mock_search_plugins():
    """Fixture that mocks plugin implementations for search tests."""
    mock_provider = MockSearchProvider()
    mock_feature = MockSearchFeature()

    with mock.patch(
        "ckanext.search.logic.actions.PluginImplementations"
    ) as mock_plugin_implementations:

        def choose(interface):
            if interface == ISearchProvider:
                return [mock_provider]
            elif interface == ISearchFeature:
                return [mock_feature]
            return []

        mock_plugin_implementations.side_effect = choose

        # Return the mocks so tests can access them for assertions
        yield {
            "provider": mock_provider,
            "feature": mock_feature,
        }


def test_standard_params(mock_search_plugins):
    helpers.call_action(
        "search",
        q="cats",
        limit=10,
        start=10,
        sort=["title asc"],
        filters={"entity_type": "dataset"},
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["q"] == "cats"
    assert query_params["limit"] == 10
    assert query_params["start"] == 10
    assert query_params["sort"] == ["title asc"]
    assert query_params["filters"] == FilterOp(
        field="entity_type", op="eq", value="dataset"
    )


def test_standard_params_are_converted(mock_search_plugins):
    helpers.call_action(
        "search",
        q="cats",
        limit="10",
        start="10",
        sort='["title asc"]',
        filters='{"entity_type": "dataset"}',
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["q"] == "cats"
    assert query_params["limit"] == 10
    assert query_params["start"] == 10
    assert query_params["sort"] == ["title asc"]
    assert query_params["filters"] == FilterOp(
        field="entity_type", op="eq", value="dataset"
    )


def test_standard_params_are_validated(mock_search_plugins):

    with pytest.raises(toolkit.ValidationError) as exc_info:
        helpers.call_action(
            "search",
            q="cats",
            limit="a",
            start="b",
            sort='{"title": "asc"}',
            filters="aa",
        )

    assert exc_info.value.error_dict["limit"][0] == "Invalid integer"
    assert exc_info.value.error_dict["start"][0] == "Invalid integer"
    assert (
        exc_info.value.error_dict["filters"][0]
        == "Filters must be defined as a dict or a list of dicts"
    )
    # TODO: use a better validator for lists for sort
    # assert exc_info.value.error_dict["sort"][0] == "Could not parse as valid JSON"


def test_provider_params(mock_search_plugins):
    helpers.call_action(
        "search",
        q="cats",
        df="title",
        qf="title^4.0 description^2.0",
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["q"] == "cats"
    assert query_params["additional_params"]["df"] == "title"
    assert query_params["additional_params"]["qf"] == "title^4.0 description^2.0"


def test_feature_params(mock_search_plugins):
    helpers.call_action(
        "search",
        q="cats",
        custom_param="hi",
    )

    query_params = mock_search_plugins["provider"].search_query.call_args[1]
    assert query_params["q"] == "cats"
    assert query_params["additional_params"]["custom_param"] == "hi"


def test_unknown_params_fail(mock_search_plugins):

    with pytest.raises(toolkit.ValidationError) as exc_info:
        helpers.call_action(
            "search",
            q="cats",
            not_="a",
            known="b",
        )

    assert exc_info.value.error_dict["message"] == "Unknown parameters: not_, known"
