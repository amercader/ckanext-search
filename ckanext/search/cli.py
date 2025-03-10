import click

from ckanext.search.index import (rebuild_dataset_index,
                                  rebuild_organization_index)
from ckanext.search.schema import init_schema


@click.group()
def search():
    """Search utilities for CKAN"""
    pass


@search.command()
@click.argument("entity_type", required=False)
def rebuild(entity_type: str):

    if entity_type == "dataset":
        rebuild_dataset_index()
    elif entity_type == "organization":
        rebuild_organization_index()
    elif entity_type is None:

        rebuild_organization_index()
        rebuild_dataset_index()


@search.command()
def init():
    init_schema()


def get_commands():

    return [search]
