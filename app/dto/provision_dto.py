from pydantic import BaseModel, Field


class ProvisionDTO(BaseModel):

    project_id: int = Field(..., examples=[72], description="Project ID")
    scenario_id: int = Field(..., examples=[192], description="Scenario ID")
    service_type_id: int = Field(..., examples=[22], description="Service type ID")
    target_population: int | None = Field(
        default=None,
        examples=[200],
        description="Target population for project territory",
    )
