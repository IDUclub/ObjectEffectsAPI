from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ProvisionDTO(BaseModel):

    project_id: int = Field(..., examples=[72], description="Project ID")
    scenario_id: int = Field(..., examples=[192], description="Scenario ID")
    service_type_id: int = Field(..., examples=[22], description="Service type ID")
    target_population: int | None = Field(
        default=None,
        examples=[200],
        description="Target population for project territory",
    )


class NormativeOverride(BaseModel):
    """Normative values set by a regulatory norm instead of the Urban API ones."""

    capacity_per_1000: float | None = Field(
        default=None, gt=0, description="Places per 1000 residents"
    )
    residents_per_service: float | None = Field(
        default=None,
        gt=0,
        description="Residents served by one service object (1 object per N residents)",
    )
    accessibility_type: Literal["time", "dist"] | None = Field(
        default=None, description="time — minutes, dist — metres"
    )
    accessibility_value: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def accessibility_has_a_type(self) -> "NormativeOverride":
        if (self.accessibility_type is None) != (self.accessibility_value is None):
            raise ValueError("accessibility_type and accessibility_value go together")
        if (
            self.capacity_per_1000 is not None
            and self.residents_per_service is not None
        ):
            raise ValueError(
                "capacity_per_1000 and residents_per_service exclude each other"
            )
        return self

    def is_complete(self) -> bool:
        """Both values are set, so the Urban API normative is not needed."""
        has_capacity = (
            self.capacity_per_1000 is not None or self.residents_per_service is not None
        )
        return has_capacity and self.accessibility_value is not None


class NormativeProvisionDTO(NormativeOverride):

    scenario_id: int = Field(..., examples=[192], description="Scenario ID")
    service_type_id: int = Field(..., examples=[22], description="Service type ID")

    def override(self) -> NormativeOverride:
        return NormativeOverride(
            capacity_per_1000=self.capacity_per_1000,
            residents_per_service=self.residents_per_service,
            accessibility_type=self.accessibility_type,
            accessibility_value=self.accessibility_value,
        )
