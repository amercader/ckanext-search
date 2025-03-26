import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.search import cli
from ckanext.search.logic import actions

# TODO: All this whole plugin will eventually live in CKAN core


class SearchPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IActions)

    # IActions
    def get_actions(self):
        return {
            "search": actions.search
        }

    # IClick

    def get_commands(self):
        return cli.get_commands()
