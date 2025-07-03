import json
from collections.abc import Iterator

from ckan import model
from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.lib.plugins import get_permission_labels
from ckan.plugins import PluginImplementations, SingletonPlugin
from ckan.plugins.toolkit import aslist, config, get_action
from ckan.types import ActionResult
from ckanext.search.interfaces import ISearchProvider, ISearchFeature
from sqlalchemy.sql.expression import true


def _get_indexing_providers() -> list:
    indexing_providers = aslist(
        config.get("ckan.search.indexing_provider", config["ckan.search.search_provider"])
    )

    return indexing_providers


def _get_indexing_plugins() -> Iterator[SingletonPlugin]:
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            yield plugin


def index_dataset(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "use_cache": False
        # "for_indexing": True,  # TODO: implement support in core?
    }

    # Request the validated dataset
    dataset_dict = get_action("package_show")(context, {"id": id_})

    return index_dataset_dict(dataset_dict)


def index_dataset_dict(dataset_dict: ActionResult.PackageShow) -> None:

    # TODO: choose what to index here?
    search_data = dict(dataset_dict)
    search_data.pop("organization", None)

    # TODO: handle resource fields
    search_data.pop("resources", None)

    search_data["tags"] = [t["name"] for t in search_data.get("tags", [])]

    # Add search-specific fields

    search_data["entity_type"] = "dataset"

    search_data["validated_data_dict"] = json.dumps(search_data, cls=MissingNullEncoder)

    # permission labels determine visibility in search, can't be set
    # in original dataset or before_dataset_index plugins
    id_ = dataset_dict["id"]
    labels = get_permission_labels()
    search_data["permission_labels"] = labels.get_dataset_labels(model.Package.get(id_))

    _index_record("dataset", search_data["id"], search_data)


def index_organization(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "use_cache": False, # TODO: not really used in core outside datasets
        # "for_indexing": True,  # TODO: implement support in core
    }
    org_dict = get_action("organization_show")(context, {"id": id_})

    return index_organization_dict(org_dict)


def index_organization_dict(org_dict: ActionResult.OrganizationShow) -> None:

    # TODO: choose what to index here?
    search_data = dict(org_dict)
    search_data.pop("users", None)

    search_data["entity_type"] = "organization"
    search_data["validated_data_dict"] = json.dumps(search_data, cls=MissingNullEncoder)

    _index_record("organization", search_data["id"], search_data)


def _index_record(entity_type: str, id_: str, search_data: dict) -> None:

    for provider_plugin in PluginImplementations(ISearchProvider):
        if provider_plugin.id in _get_indexing_providers():

            for feature_plugin in PluginImplementations(ISearchFeature):
                provider_supported = (
                    provider_plugin.id in feature_plugin.supported_providers()
                )
                entity_type_supported = entity_type in feature_plugin.entity_types()

                if provider_supported and entity_type_supported:

                    feature_plugin.before_index(entity_type, id_, search_data)

            provider_plugin.index_search_record(entity_type, id_, search_data)


def rebuild_dataset_index() -> None:

    dataset_ids = [
        r[0]
        for r in model.Session.query(model.Package.id)
        .filter(
            model.Package.state != "deleted"
        )  # TODO: more filters (state, type, etc)?
        .all()
    ]

    for id_ in dataset_ids:
        index_dataset(id_)


def rebuild_organization_index() -> None:

    org_ids = [
        r[0]
        for r in model.Session.query(model.Group.id)
        .filter(
            model.Group.state != "deleted"
        )  # TODO: more filters (state, type, etc)?
        .filter(model.Group.is_organization == true())
        .all()
    ]

    for id_ in org_ids:
        index_organization(id_)


def clear_index():
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            plugin.clear_index()
