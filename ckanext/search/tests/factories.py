from ckan.tests import factories as core_factories

from ckanext.search import index


class CKANIndexedOnlyFactory(core_factories.CKANFactory):

    @classmethod
    def _api_prepare_args(cls, data_dict):
        """Add any extra details for the action."""
        data_dict = super()._api_prepare_args(data_dict)

        data_dict["context"]["for_indexing"] = True
        data_dict["context"]["validate"] = False
        # Prevent actually storing the entity in the database
        data_dict["context"]["defer_commit"] = True

        return data_dict

    @classmethod
    def _api_postprocess_result(cls, result):
        """Modify result before returning it to the consumer."""

        if cls.indexer:
            cls.indexer(result)

        return result


class IndexedDataset(core_factories.Dataset, CKANIndexedOnlyFactory):

    indexer = index.index_dataset_dict


class IndexedOrganization(core_factories.Organization, CKANIndexedOnlyFactory):

    indexer = index.index_organization_dict
