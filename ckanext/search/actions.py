# This will eventually live in ckan/logic/action/get.py
from ckan.plugins import PluginImplementations
from ckan.plugins.toolkit import aslist, config, get_action, side_effect_free

from ckanext.search.interfaces import ISearchProvider


@side_effect_free
def search(context, data_dict):

    # TODO: Check auth

    # TODO:

    ## Validate data_dict. Any key not in the standard schema is moved to
    ## additional_params
    ## Q: Do we validate just the common interface params here or get additional schema
    ##    entries from the search feature plugin to validate additional params like `bbox`?
    # schema = default_search_query_schema()

    # for plugin in PluginImplementations(ISearchFeature):
    #    plugin.search_schema(schema)

    query_dict = {
        "query": data_dict.get("q"),
        "filters": [],
        "sort": "",
        "additional_params": {},
        "lang": "",
    }

    search_backend = config["ckan.search.search_backend"]
    result = {}
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id == search_backend:
            result = plugin.search_query(**query_dict)
            break

    # TODO
    # if context.get('for_view'):
    #    for item in plugins.PluginImplementations(
    #        plugins.IPackageController):
    #    package_dict = item.before_dataset_view(
    #        package_dict)

    return result
