from ckanext.search import actions, cli

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

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
