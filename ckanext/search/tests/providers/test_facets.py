import pytest

from ckan.plugins.toolkit import config
from ckanext.search.index import clear_index
from ckanext.search.logic.actions import search as search_action
from ckanext.search.tests import factories


pytestmark = pytest.mark.skipif(
    not config.get("ckan.search.search_provider"),
    reason="No search provided defined",
)


def search(**kwargs):

    context = {"ignore_auth": True}
    return search_action(context, kwargs)


@pytest.fixture()
def index_for_facet_tests():

    clear_index()

    factories.IndexedDataset(
        name="dataset-cats",
        title="A dataset about cats",
        tags=[{"name": "cats"}, {"name": "animal"}],
        metadata_modified="2025-03-01T00:00:00",
        version="1",
    )

    factories.IndexedDataset(
        name="dataset-dogs",
        title="A dataset about dogs",
        tags=[{"name": "dogs"}, {"name": "animal"}],
        metadata_modified="2025-04-01T00:00:00",
        version="2",
    )

    factories.IndexedDataset(
        name="dataset-snakes",
        title="A dataset about snakes",
        tags=[{"name": "snakes"}, {"name": "animal"}],
        metadata_modified="2025-04-01T00:00:00",
        version="3",
    )

    factories.IndexedDataset(
        name="dataset-oaks",
        title="A dataset about oaks",
        tags=[{"name": "oaks"}, {"name": "plant"}],
        metadata_modified="2025-02-01T00:00:00",
        version="1",
    )


def test_facets_basic():

    facets = {
        "field": "tags"
    }

    result = search(facets=facets)
