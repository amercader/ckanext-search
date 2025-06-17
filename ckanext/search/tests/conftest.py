import pytest

from ckanext.search.index import clear_index


@pytest.fixture
def clean_search_index():
    clear_index()
    yield
    clear_index()
