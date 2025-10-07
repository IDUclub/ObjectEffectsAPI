from typing import Optional

from pydantic import BaseModel, Field


class EffectsDTO(BaseModel):

    project_id: int = Field(..., examples=[72], description="Project ID")
    scenario_id: int = Field(..., examples=[192], description="Scenario ID")
    service_type_id: int = Field(..., examples=[7], description="Service type ID")
    target_population: Optional[int] = Field(
        default=None,
        examples=[200],
        description="Target population for project territory",
    )
