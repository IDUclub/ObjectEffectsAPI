from typing import Annotated

from fastapi import APIRouter, Depends


from .dto.effects_dto import EffectsDTO
from .shemas.effects_base_schema import EffectsSchema
from .effects_service import effects_service


effects_router = APIRouter(prefix="/effects")

@effects_router.get("/evaluate_provision", response_model=EffectsSchema)
async def calculate_effects(
        params: Annotated[EffectsDTO, Depends(EffectsDTO)],
) -> EffectsSchema:
    """
    Get method for retrieving effects with objectnat
    Params:

    project ID: Project ID
    scenario ID: Scenario ID
    """

    return await effects_service.handle_effects_calculation(params)
