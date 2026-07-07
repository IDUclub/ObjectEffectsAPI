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
    target_population: int | None = Field(
        default=None,
        examples=[25000],
        description=(
            "Total population of the scenario territory for demand calculation. "
            "If not provided, population is restored from Urban API data."
        ),
    )


class ProvisionSummarySchema(BaseModel):

    services_count: int
    total_capacity: int
    total_demand: int
    satisfied_demand_within: int
    satisfied_demand_without: int
    unsatisfied_demand: int
    balance: int = Field(
        description="Capacity minus demand; negative means shortage of places"
    )
    deficit: int = Field(
        ge=0, description="Places short of demand, 0 when capacity covers demand"
    )
    surplus: int = Field(
        ge=0, description="Places above demand, 0 when demand exceeds capacity"
    )
    average_provision_value: float | None
    median_provision_value: float | None


class ServiceProvisionResultSchema(BaseModel):

    name: str
    summary: ProvisionSummarySchema | None = None
    layers: ProvisionSchema | None = None
    error: str | None = None


class MultiProvisionSchema(BaseModel):

    services: dict[int, ServiceProvisionResultSchema]
