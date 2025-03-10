from collections.abc import Iterator

from ckanext.search.interfaces import ISearchProvider
from sqlalchemy.sql.expression import true

from ckan import model
from ckan.plugins import PluginImplementations, SingletonPlugin
from ckan.plugins.toolkit import aslist, config, get_action


def _get_indexing_providers() -> list:
    indexing_providers = aslist(
        config.get("ckan.search.indexing_backend", config["ckan.search.search_backend"])
    )

    return indexing_providers


def _get_indexing_plugins() -> Iterator[SingletonPlugin]:
    for plugin in PluginImplementations(ISearchProvider):
        yield plugin


def index_dataset(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "for_indexing": True,  # TODO: implement support in core
        "validate": False,
    }
    data_dict = get_action("package_show")(context, {"id": id_})

    data_dict["entity_type"] = "dataset"

    # TODO: choose what to index here?
    # TODO: add permission labels

    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            plugin.index_search_record("dataset", data_dict["id"], data_dict)


def index_organization(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "for_indexing": True,  # TODO: implement support in core
        "validate": False,
    }
    data_dict = get_action("organization_show")(context, {"id": id_})

    data_dict["entity_type"] = "organization"

    # TODO: choose what to index here?

    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in _get_indexing_providers():
            plugin.index_search_record("organization", data_dict["id"], data_dict)


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
