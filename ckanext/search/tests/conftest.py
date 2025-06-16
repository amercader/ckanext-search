import pytest

from ckan.plugins.toolkit import config

from ckanext.search.index import clear_index


def pytest_addoption(parser):
    parser.addoption(
        "--search-provider",
        default=None,  # If none provided, use the one in test.ini or the default one
        help="Search provider to run the tests against",
    )


@pytest.fixture
def search_providers():
    pass


def pytest_runtest_setup(item):

    if "search_providers" in item.fixturenames and item.config.option.search_provider:
        item.add_marker(
            pytest.mark.ckan_config(
                "ckan.search.search_backend", item.config.option.search_provider
            )
        )


@pytest.fixture
def clean_search_index():
    clear_index()
    yield
    clear_index()
