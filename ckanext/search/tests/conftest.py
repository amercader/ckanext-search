import pytest

from ckan.plugins.toolkit import config


def pytest_addoption(parser):
    parser.addoption(
        "--search-provider",
        default=None,  # If none provided, use the one in test.ini or the default one
        help="Search provider to run the tests against",
    )


@pytest.fixture
def search_providers():
    pass


def pytest_sessionstart(session):
    if session.config.option.search_provider:
        provider = session.config.option.search_provider
        source = "CLI option"
    elif config.get("ckan.search.search_backend"):
        provider = config["ckan.search.search_backend"]
        source = "config"
    else:
        provider = "solr"
        source = "default"

    print("Using Search provider: %s (%s)" % (provider, source))
    import ipdb; ipdb.set_trace()


def pytest_runtest_setup(item):

    if "search_providers" in item.fixturenames and item.config.option.search_provider:
        item.add_marker(
            pytest.mark.ckan_config(
                "ckan.search.search_backend", item.config.option.search_provider
            )
        )
