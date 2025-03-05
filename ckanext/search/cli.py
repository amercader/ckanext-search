import click

from ckanext.search.index import rebuild_dataset_index


@click.group()
def search():
    """Search utilities for CKAN"""
    pass



@search.command()
def rebuild():

    rebuild_dataset_index()



def get_commands():

    return [search]
