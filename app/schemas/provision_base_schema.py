from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GeometrySchema(BaseModel):

    type: Literal[
        "Polygon",
        "MultiPolygon",
        "LineString",
        "MultiLineString",
        "Point",
        "MultiPoint",
    ]
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


class ServiceInfoSchema(BaseModel):

    name: str = Field(..., examples=["Школа"], description="Service display name")
    as_layer: bool = Field(
        default=True,
        description="If true, response includes GeoJSON layers for the service",
    )


class MultiProvisionRequestSchema(BaseModel):

    scenario_id: int = Field(..., examples=[192], description="Scenario ID")
    services: dict[int, ServiceInfoSchema] = Field(
        ...,
        examples=[{22: {"name": "Школа", "as_layer": True}}],
        description="Service type IDs to calculate provision for",
    )


class ProvisionSummarySchema(BaseModel):

    services_count: int
    total_capacity: int
    total_demand: int
    satisfied_demand_within: int
    satisfied_demand_without: int
    unsatisfied_demand: int
    average_provision_value: float | None
    median_provision_value: float | None


class ServiceProvisionResultSchema(BaseModel):

    name: str
    summary: ProvisionSummarySchema | None = None
    layers: ProvisionSchema | None = None
    error: str | None = None


class MultiProvisionSchema(BaseModel):

    services: dict[int, ServiceProvisionResultSchema]
