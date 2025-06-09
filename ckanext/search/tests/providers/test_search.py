import pytest
from ckanext.search.logic.actions import search as search_action
from ckanext.search.index import clear_index
from ckanext.search.tests import factories

pytestmark = pytest.mark.usefixtures("with_plugins", "search_providers")


@pytest.fixture
def clean_search_index():
    clear_index()
    yield
    clear_index()


def search(**kwargs):

    context = {"ignore_auth": True}
    return search_action(context, kwargs)


@pytest.mark.usefixtures("clean_search_index")
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


@pytest.mark.usefixtures("clean_search_index")
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


@pytest.fixture(scope="session")
def index_for_filters_tests():

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


@pytest.mark.usefixtures("index_for_filters_tests")
@pytest.mark.parametrize(
    "filters,names",
    [
        (None, ["dataset-cats", "dataset-dogs", "dataset-oaks", "dataset-snakes"]),
        # Single field shorthand
        ({"tags": "cats"}, ["dataset-cats"]),
        # Single field
        ({"tags": {"eq": "cats"}}, ["dataset-cats"]),
        # OR shorthand
        # (Needs to be passed as string otherwise Navl won't understand it)
        (
            '[{"tags": "cats"}, {"tags": "snakes"}]',
            ["dataset-cats", "dataset-snakes"],
        ),
        # OR
        (
            {"$or": [{"tags": "dogs"}, {"tags": "snakes"}]},
            ["dataset-dogs", "dataset-snakes"],
        ),
        # AND shortand
        (
            {"tags": "animal", "version": "2"},
            ["dataset-dogs"],
        ),
        # AND
        (
            {"$and": [{"tags": "animal"}, {"version": "2"}]},
            ["dataset-dogs"],
        ),
        # Nested
        (
            {
                "$or": [
                    {"tags": "dogs"},
                    {"$and": [{"tags": "animal"}, {"version": "1"}]},
                ]
            },
            ["dataset-cats", "dataset-dogs"],
        ),
        # IN shorthand
        (
            {"version": ["2", "3"]},
            ["dataset-dogs", "dataset-snakes"],
        ),
        # IN
        (
            {"version": {"in": ["2", "3"]}},
            ["dataset-dogs", "dataset-snakes"],
        ),
        # Ranges
        (
            {"metadata_modified": {"gt": "2025-03-01T00:00:00Z"}},
            ["dataset-dogs", "dataset-snakes"],
        ),
        (
            {"metadata_modified": {"gte": "2025-03-01T00:00:00Z"}},
            ["dataset-cats", "dataset-dogs", "dataset-snakes"],
        ),
        (
            {
                "metadata_modified": {
                    "gte": "2025-02-01T00:00:00Z",
                    "lte": "2025-03-01T00:00:00Z",
                }
            },
            ["dataset-cats", "dataset-oaks"],
        ),
        (
            {"version": {"lt": "2"}},
            ["dataset-cats", "dataset-oaks"],
        ),
        (
            {"version": {"lte": "2"}},
            ["dataset-cats", "dataset-dogs", "dataset-oaks"],
        ),
        (
            {"version": {"gt": "1", "lt": "3"}},
            ["dataset-dogs"],
        ),
    ],
)
def test_search_filters(index_for_filters_tests, filters, names):

    result = search(q="*", filters=filters)

    assert result["count"] == len(names)
    if names:
        assert sorted([d["name"] for d in result["results"]]) == names
