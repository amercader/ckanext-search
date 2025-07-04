import datetime

import pytest
from ckan.plugins.toolkit import config

from ckanext.search.filters import FilterOp
from ckanext.search.interfaces import SearchSchema
from ckanext.search.providers.es import ElasticSearchProvider


pytestmark = pytest.mark.skipif(
    config.get("ckan.search.search_provider") != "elasticsearch",
    reason="These tests are ElasticSearch specific",
)


SEARCH_SCHEMA: SearchSchema = {
    "version": 1,
    "fields": {
        "some_text_field": {"type": "text"},
        "some_numeric_field": {
            "type": "number"  # TODO: still not defined (probably need int,...)
        },
        "some_date_field": {"type": "date"},
    },
}


@pytest.fixture
def esp():

    return ElasticSearchProvider()


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_text_field", op="eq", value="some_value"),
            {"term": {"some_text_field": "some_value"}},
        ),
        (
            FilterOp(field="some_numeric_field", op="eq", value=2),
            {"term": {"some_numeric_field": 2}},
        ),
    ],
)
def test_filters_builtin_operations_eq(esp, filters, result):

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_builtin_operations_eq_date(esp):
    now = datetime.datetime.now().isoformat()
    filters = FilterOp(
        field="some_date_field",
        op="eq",
        value=now,
    )

    result = {"term": {"some_date_field": now}}

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_numeric_field", op="gt", value=5),
            {"range": {"some_numeric_field": {"gt": 5}}},
        ),
        (
            FilterOp(field="some_numeric_field", op="gte", value=5),
            {"range": {"some_numeric_field": {"gte": 5}}},
        ),
        (
            FilterOp(field="some_numeric_field", op="lt", value=5),
            {"range": {"some_numeric_field": {"lt": 5}}},
        ),
        (
            FilterOp(field="some_numeric_field", op="lte", value=5),
            {"range": {"some_numeric_field": {"lte": 5}}},
        ),
    ],
)
def test_filters_builtin_operations_ranges_numbers(esp, filters, result):

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_date_field", op="gt", value="2025-06-06T00:00:00Z"),
            {"range": {"some_date_field": {"gt": "2025-06-06T00:00:00Z"}}},
        ),
        (
            FilterOp(field="some_date_field", op="gte", value="2025-06-06T00:00:00Z"),
            {"range": {"some_date_field": {"gte": "2025-06-06T00:00:00Z"}}},
        ),
        (
            FilterOp(field="some_date_field", op="lt", value="2025-06-06T00:00:00Z"),
            {"range": {"some_date_field": {"lt": "2025-06-06T00:00:00Z"}}},
        ),
        (
            FilterOp(field="some_date_field", op="lte", value="2025-06-06T00:00:00Z"),
            {"range": {"some_date_field": {"lte": "2025-06-06T00:00:00Z"}}},
        ),
    ],
)
def test_filters_builtin_operations_ranges_dates(esp, filters, result):

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_unknown_field_returns_term_query(esp):
    filters = FilterOp(
        field="unknown_field",
        op="eq",
        value="some_value",
    )
    result = {"term": {"unknown_field": "some_value"}}

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_in_operation(esp):
    filters = FilterOp(
        field="some_text_field",
        op="in",
        value=["value1", "value2", "value3"],
    )

    result = {"terms": {"some_text_field": ["value1", "value2", "value3"]}}
    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_in_operation_empty_list(esp):
    filters = FilterOp(
        field="some_text_field",
        op="in",
        value=[],
    )

    result = esp._filterop_to_es_query(filters, SEARCH_SCHEMA)
    assert result is None


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_text_field", op="eq", value='some "quoted" value'),
            {"term": {"some_text_field": 'some "quoted" value'}},
        ),
        (
            FilterOp(field="some_numeric_field", op="eq", value='some "quoted" value'),
            {"term": {"some_numeric_field": 'some "quoted" value'}},
        ),
        (
            FilterOp(field="some_date_field", op="eq", value='some "quoted" value'),
            {"term": {"some_date_field": 'some "quoted" value'}},
        ),
    ],
)
def test_filters_quotes_are_preserved(esp, filters, result):

    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_basic_or(esp):

    filters = FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="some_text_field", op="eq", value="some_value1"),
            FilterOp(field="some_text_field", op="eq", value="some_value2"),
        ],
    )

    result = {
        "bool": {
            "should": [
                {"term": {"some_text_field": "some_value1"}},
                {"term": {"some_text_field": "some_value2"}},
            ],
            "minimum_should_match": 1,
        }
    }
    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_basic_and(esp):

    filters = FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="some_text_field", op="eq", value="some_value1"),
            FilterOp(field="some_numeric_field", op="lte", value=10),
        ],
    )

    result = {
        "bool": {
            "must": [
                {"term": {"some_text_field": "some_value1"}},
                {"range": {"some_numeric_field": {"lte": 10}}},
            ]
        }
    }
    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_permission_labels(esp):
    labels = ["creator-xxx", "member-yyy", "collaborator-zzz"]
    perm_labels_filter_op = FilterOp(field="permission_labels", op="in", value=labels)

    filters = FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(
                field=None,
                op="$and",
                value=[
                    FilterOp(field="some_text_field", op="eq", value="some_value1"),
                    FilterOp(field="some_numeric_field", op="lte", value=10),
                ],
            ),
            perm_labels_filter_op,
        ],
    )

    result = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "must": [
                            {"term": {"some_text_field": "some_value1"}},
                            {"range": {"some_numeric_field": {"lte": 10}}},
                        ]
                    }
                },
                {"terms": {"permission_labels": labels}},
            ]
        }
    }
    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result


def test_filters_unknown_operator_defaults_to_term(esp):
    filters = FilterOp(
        field="some_text_field",
        op="unknown_op",
        value="some_value",
    )

    result = {"term": {"some_text_field": "some_value"}}
    assert esp._filterop_to_es_query(filters, SEARCH_SCHEMA) == result
