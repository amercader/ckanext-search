from collections.abc import Iterator
import json

from ckan import model
from ckan.lib.navl.dictization_functions import MissingNullEncoder
from ckan.lib.plugins import get_permission_labels
from ckan.plugins import PluginImplementations, SingletonPlugin
from ckan.plugins.toolkit import aslist, config, get_action
from sqlalchemy.sql.expression import true

from ckanext.search.interfaces import ISearchProvider


def _get_indexing_providers() -> list:
    indexing_providers = aslist(
        config.get("ckan.search.indexing_backend", config["ckan.search.search_backend"])
    )

    return indexing_providers


def _get_indexing_plugins() -> Iterator[SingletonPlugin]:
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            yield plugin


def index_dataset(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "for_indexing": True,  # TODO: implement support in core
        "validate": False,
    }
    data_dict = get_action("package_show")(context, {"id": id_})

    # TODO: choose what to index here?
    search_data = dict(data_dict)
    search_data.pop("organization", None)

    # TODO: handle resource fields
    search_data.pop("resources", None)

    # Add search-specific fields

    search_data["entity_type"] = "dataset"

    search_data["validated_data_dict"] = json.dumps(search_data, cls=MissingNullEncoder)

    # permission labels determine visibility in search, can't be set
    # in original dataset or before_dataset_index plugins
    labels = get_permission_labels()
    search_data["permission_labels"] = labels.get_dataset_labels(model.Package.get(id_))

    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            plugin.index_search_record("dataset", search_data["id"], search_data)


def index_organization(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "for_indexing": True,  # TODO: implement support in core
        "validate": False,
    }
    data_dict = get_action("organization_show")(context, {"id": id_})

    # TODO: choose what to index here?
    search_data = dict(data_dict)
    search_data.pop("users", None)

    search_data["entity_type"] = "organization"
    search_data["validated_data_dict"] = json.dumps(search_data, cls=MissingNullEncoder)

    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            plugin.index_search_record("organization", search_data["id"], search_data)


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
