import pytest
from ckanext.search.actions import search as search_action
from ckanext.search.index import clear_index
from ckanext.search.tests import factories

pytestmark = pytest.mark.usefixtures("with_plugins", "clean_search_index")


@pytest.fixture
def clean_search_index():
    clear_index()


def search(**kwargs):

    context = {"ignore_auth": True}
    return search_action(context, kwargs)


def test_search():

    dataset = factories.IndexedDataset(title="Walrus data")

    result = search(q="walrus")

    assert result["count"] == 1
    assert result["results"][0]["id"] == dataset["id"]
    assert result["results"][0]["title"] == dataset["title"]
