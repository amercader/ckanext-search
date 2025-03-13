# This will eventually live in ckan/logic/action/get.py

import ckan.authz as authz
from ckan.lib.plugins import get_permission_labels
from ckan.plugins import PluginImplementations
from ckan.plugins.toolkit import aslist, config, get_action, side_effect_free

from ckanext.search.interfaces import ISearchProvider


@side_effect_free
def search(context, data_dict):

    # TODO: Check auth
    user = context.get("user")

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
        "filters": {},
        "sort": "",
        "additional_params": {},
        "lang": "",
    }

    # enforce permission filter based on user
    if context.get("ignore_auth") or (user and authz.is_sysadmin(user)):
        labels = None
    else:
        labels = get_permission_labels().get_user_dataset_labels(
            context["auth_user_obj"]
        )

    if labels:
        query_dict["filters"]["permission_labels"] = labels

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
