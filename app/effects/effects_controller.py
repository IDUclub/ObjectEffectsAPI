from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.auth.service_auth import get_current_user_id
from app.dependencies import effects_service
from app.dto.provision_dto import ProvisionDTO

from .shemas.effects_base_schema import EffectsSchema

effects_router = APIRouter(prefix="/effects")


@effects_router.get("/evaluate_provision", response_model=EffectsSchema)
async def calculate_effects(
    params: Annotated[ProvisionDTO, Depends(ProvisionDTO)],
    user_id: str = Depends(get_current_user_id),
) -> EffectsSchema:

    return await effects_service.calculate_effects(params, user_id)
