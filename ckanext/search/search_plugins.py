from typing import Any

from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.toolkit import Invalid
from ckan.types import Schema
from ckanext.search.interfaces import ISearchFeature, SearchSchema


def bbox_validator(value):

    # TODO: use all checks and logic from ckanext-spatial

    if isinstance(value, str):
        value = value.split(",")

    if len(value) != 4:
        raise Invalid(
            "Not enough values in bounding box, must be: minx, miny, maxx, maxy"
        )

    try:
        bbox = {}
        bbox["minx"] = float(value[0])
        bbox["miny"] = float(value[1])
        bbox["maxx"] = float(value[2])
        bbox["maxy"] = float(value[3])
    except ValueError:
        raise Invalid(f"Invalid values in bounding box: {value}")

    return bbox


class SpatialSearch(SingletonPlugin):
    """
    Plugin that adds spatial search capabilities to CKAN search.
    """

    implements(ISearchFeature, inherit=True)

    # def search_schema(self) -> SearchSchema:
    #    """Return spatial search schema fields."""
    #    return {
    #        "version": 1,
    #        "fields": [
    #            {"name": "spatial_geom", "type": "string"},
    #            {"name": "spatial_bbox", "type": "string"},
    #        ]
    #    }

    def search_query_schema(self) -> Schema:
        """
        Add spatial query parameters to the search query schema.
        """
        search_query_schema = {}

        # Bounding box coordinates: minx, miny, maxx, maxy
        search_query_schema["bbox"] = [bbox_validator]

        return search_query_schema
