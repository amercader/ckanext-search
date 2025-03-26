import pytest
from ckanext.search.logic.actions import search as search_action
from ckanext.search.index import clear_index
from ckanext.search.tests import factories

pytestmark = pytest.mark.usefixtures(
    "with_plugins", "clean_search_index", "search_providers"
)


@pytest.fixture
def clean_search_index():
    clear_index()


def search(**kwargs):

    context = {"ignore_auth": True}
    return search_action(context, kwargs)


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("name", "walrus-data"),
        ("title", "Walrus data"),
        ("notes", "Some data about a walrus"),
    ],
)
def test_search_dataset_combined_field(field_name, field_value):

    dataset = factories.IndexedDataset(**{field_name: field_value})

    result = search(q="walrus")

    assert result["count"] == 1
    assert result["results"][0]["id"] == dataset["id"]
    assert result["results"][0][field_name] == field_value


# TODO: test stemming English

# TODO: test stemming other languages


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("name", "walrus-org"),
        ("title", "Walrus org"),
        ("description", "Some org about a walrus"),
    ],
)
def test_search_organization_combined_field(field_name, field_value):

    organization = factories.IndexedOrganization(**{field_name: field_value})

    result = search(q="walrus")

    assert result["count"] == 1
    assert result["results"][0]["id"] == organization["id"]
    assert result["results"][0][field_name] == field_value
