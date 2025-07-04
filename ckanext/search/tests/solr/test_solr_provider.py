import datetime

import pytest
from ckan.plugins.toolkit import config

from ckanext.search.filters import FilterOp
from ckanext.search.interfaces import SearchSchema
from ckanext.search.providers.solr import SolrSearchProvider


pytestmark = pytest.mark.skipif(
    config.get("ckan.search.search_provider") != "solr",
    reason="These tests are Solr specific",
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
def ssp():

    return SolrSearchProvider()


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_text_field", op="eq", value="some_value"),
            ['some_text_field:"some_value"'],
        ),
        (
            FilterOp(field="some_numeric_field", op="eq", value=2),
            ["some_numeric_field:2"],
        ),
    ],
)
def test_filters_builtin_operations_eq(ssp, filters, result):

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_builtin_operations_eq_date(ssp):
    now = datetime.datetime.now().isoformat()
    filters = FilterOp(
        field="some_date_field",
        op="eq",
        value=now,
    )

    # Dates not in range filters are quoted
    result = [f'some_date_field:"{now}"']

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_numeric_field", op="gt", value=5),
            ["some_numeric_field:{5 TO *}"],
        ),
        (
            FilterOp(field="some_numeric_field", op="gte", value=5),
            ["some_numeric_field:[5 TO *]"],
        ),
        (
            FilterOp(field="some_numeric_field", op="lt", value=5),
            ["some_numeric_field:{* TO 5}"],
        ),
        (
            FilterOp(field="some_numeric_field", op="lte", value=5),
            ["some_numeric_field:[* TO 5]"],
        ),
    ],
)
def test_filters_builtin_operations_ranges_numbers(ssp, filters, result):

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_date_field", op="gt", value="2025-06-06T00:00:00Z"),
            ["some_date_field:{2025-06-06T00:00:00Z TO *}"],
        ),
        (
            FilterOp(field="some_date_field", op="gte", value="2025-06-06T00:00:00Z"),
            ["some_date_field:[2025-06-06T00:00:00Z TO *]"],
        ),
        (
            FilterOp(field="some_date_field", op="lt", value="2025-06-06T00:00:00Z"),
            ["some_date_field:{* TO 2025-06-06T00:00:00Z}"],
        ),
        (
            FilterOp(field="some_date_field", op="lte", value="2025-06-06T00:00:00Z"),
            ["some_date_field:[* TO 2025-06-06T00:00:00Z]"],
        ),
    ],
)
def test_filters_builtin_operations_ranges_dates(ssp, filters, result):

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_in_operation(ssp):
    filters = FilterOp(
        field="some_text_field",
        op="in",
        value=["value1", "value2", "value3"],
    )

    result = [
        'some_text_field:"value1" OR '
        'some_text_field:"value2" OR '
        'some_text_field:"value3"'
    ]
    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_in_operation_empty_list(ssp):
    filters = FilterOp(
        field="some_text_field",
        op="in",
        value=[],
    )

    result = ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA)
    assert result == []


def test_filters_unknown_field_is_quoted(ssp):
    filters = FilterOp(
        field="unknown_field",
        op="eq",
        value="some_value",
    )
    result = ['unknown_field:"some_value"']

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


@pytest.mark.parametrize(
    "filters,result",
    [
        (
            FilterOp(field="some_text_field", op="eq", value='some "quoted" value'),
            ['some_text_field:"some \\"quoted\\" value"'],
        ),
        (
            FilterOp(field="some_numeric_field", op="eq", value='some "quoted" value'),
            ['some_numeric_field:some \\"quoted\\" value'],
        ),
        (
            FilterOp(field="some_date_field", op="eq", value='some "quoted" value'),
            ['some_date_field:"some \\"quoted\\" value"'],
        ),
    ],
)
def test_filters_quotes_are_escaped(ssp, filters, result):

    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_basic_or(ssp):

    filters = FilterOp(
        field=None,
        op="$or",
        value=[
            FilterOp(field="some_text_field", op="eq", value="some_value1"),
            FilterOp(field="some_text_field", op="eq", value="some_value2"),
        ],
    )

    result = ['(some_text_field:"some_value1") OR (some_text_field:"some_value2")']
    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_basic_and(ssp):

    filters = FilterOp(
        field=None,
        op="$and",
        value=[
            FilterOp(field="some_text_field", op="eq", value="some_value1"),
            FilterOp(field="some_numeric_field", op="lte", value=10),
        ],
    )

    result = ['(some_text_field:"some_value1") AND (some_numeric_field:[* TO 10])']
    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_permission_labels(ssp):
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

    result = [
        '((some_text_field:"some_value1") AND (some_numeric_field:[* TO 10])) AND '
        '(permission_labels:"creator-xxx" OR '
        'permission_labels:"member-yyy" OR '
        'permission_labels:"collaborator-zzz")'
    ]
    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result


def test_filters_unknown_operator_defaults_to_equality(ssp):
    filters = FilterOp(
        field="some_text_field",
        op="unknown_op",
        value="some_value",
    )

    result = ['some_text_field:"some_value"']
    assert ssp._filterop_to_solr_fq(filters, SEARCH_SCHEMA) == result
