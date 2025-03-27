# This will eventually live in ckan/logic/action/get.py

import ckan.authz as authz
from ckan.lib.plugins import get_permission_labels
from ckan.plugins import PluginImplementations
from ckan.plugins.toolkit import (
    config,
    side_effect_free,
    navl_validate,
    ValidationError,
)
from ckan.types import Context, DataDict
from ckanext.search.interfaces import ISearchProvider, ISearchFeature
from ckanext.search.logic.schema import default_search_query_schema


def _get_permission_labels(context: Context) -> list[str] | None:

    user = context.get("user")
    if context.get("ignore_auth") or (user and authz.is_sysadmin(user)):
        labels = None
    else:
        labels = get_permission_labels().get_user_dataset_labels(
            context["auth_user_obj"]
        )

    return labels


@side_effect_free
def search(context: Context, data_dict: DataDict):

    # TODO: Check auth

    schema = default_search_query_schema()

    additional_params_schema = {}
    # Allow search providers to add custom params
    for plugin in PluginImplementations(ISearchProvider):
        additional_params_schema.update(plugin.search_query_schema())

    # Allow search extensions to add custom params
    for plugin in PluginImplementations(ISearchFeature):
        additional_params_schema.update(plugin.search_query_schema())

    # Any fields not in the default schema are moved to additional_params
    query_dict = {
        "q": "",
        "filters": {},
        "sort": "",
        "start": "",
        "limit": "",
        "lang": "",
    }
    additional_params = {}

    for param in data_dict.keys():
        if param in schema:
            query_dict[param] = data_dict[param]
        elif param in additional_params_schema:
            additional_params[param] = data_dict[param]
        else:
            # TODO: do we want to fail or silently ignore extra params?
            raise ValidationError({"message": f"Unknown parameter: {param}"})

    # Validate common params
    query_dict, errors = navl_validate(query_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    # Validate additional params
    additional_params, errors = navl_validate(
        additional_params, additional_params_schema, context
    )
    if errors:
        raise ValidationError(errors)

    query_dict["additional_params"] = additional_params

    # Allow search extensions to modify the query params
    for plugin in PluginImplementations(ISearchFeature):
        plugin.before_query(query_dict)

    # Permission labels
    if labels := _get_permission_labels(context):
        query_dict["filters"]["permission_labels"] = labels

    search_backend = config["ckan.search.search_backend"]
    result = {}
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id == search_backend:
            result = plugin.search_query(**query_dict)
            break

    # Allow search extensions to modify the query results
    for plugin in PluginImplementations(ISearchFeature):
        plugin.after_query(result, query_dict)

    # TODO
    # if context.get('for_view'):
    #    for item in plugins.PluginImplementations(
    #        plugins.IPackageController):
    #    package_dict = item.before_dataset_view(
    #        package_dict)

    return result
