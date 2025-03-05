from ckan import model
from ckan.plugins import PluginImplementations
from ckan.plugins.toolkit import aslist, config, get_action

from ckanext.search.interfaces import ISearchProvider


def index_dataset(id_: str) -> None:

    context = {
        "ignore_auth": True,
        "for_indexing": True,   # TODO: implement support in core
        "validate": False,
    }
    data_dict = get_action("package_show")(context, {"id": id_})

    indexing_providers = aslist(
        config.get("ckan.search.indexing_backend", config["ckan.search.search_backend"])
    )
    for plugin in PluginImplementations(ISearchProvider):
        if plugin.id in indexing_providers:

            plugin.index_search_record("dataset", data_dict["id"], data_dict)


def rebuild_dataset_index() -> None:

    dataset_ids = [
        r[0]
        for r in model.Session.query(model.Package.id)
        .filter(model.Package.state != "deleted")   # TODO: more filters (state, type, etc)?
        .all()
    ]

    for id_ in dataset_ids:
        index_dataset(id_)
