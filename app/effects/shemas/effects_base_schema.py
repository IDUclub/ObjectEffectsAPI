from typing import Optional

from pydantic import BaseModel

from app.schemas.provision_base_schema import FeatureCollectionSchema, ProvisionSchema


class PivotSchema(BaseModel):

    sum_absolute_total: int
    average_absolute_total: int | float
    median_absolute_total: int
    average_index_total: int | float
    median_index_total: int
    sum_absolute_scenario_project: Optional[int] = None
    average_absolute_scenario_project: Optional[int | float] = None
    median_absolute_scenario_project: Optional[int] = None
    average_index_scenario_project: Optional[int | float] = None
    median_index_scenario_project: Optional[int] = None
    sum_absolute_within: int
    average_absolute_within: int | float
    median_absolute_within: int


class EffectsSchema(BaseModel):

    before_prove_data: ProvisionSchema
    after_prove_data: ProvisionSchema
    effects: FeatureCollectionSchema
    pivot: PivotSchema
    text_pivot: str | None = None
