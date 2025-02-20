from typing import Literal, Optional, Any

from pydantic import BaseModel


class GeometrySchema(BaseModel):

    type: Literal["Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "MultiPoint"]
    coordinates: list[Any]


class FeatureSchema(BaseModel):

    id: Optional[int | None]
    type: Literal["Feature"]
    geometry: GeometrySchema
    properties: dict


class FeatureCollectionSchema(BaseModel):

    type: Literal["FeatureCollection"]
    features: list[FeatureSchema]


class ProvisionSchema(BaseModel):

    buildings: FeatureCollectionSchema
    services: FeatureCollectionSchema
    links: FeatureCollectionSchema


class EffectsSchema(BaseModel):

    before_prove_data: ProvisionSchema
    after_prove_data: ProvisionSchema
    effects: FeatureCollectionSchema
