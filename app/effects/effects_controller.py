from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.auth.bearer import verify_bearer_token
from app.dto.provision_dto import ProvisionDTO

from .effects_service import effects_service
from .shemas.effects_base_schema import EffectsSchema

effects_router = APIRouter(prefix="/effects")


@effects_router.get("/evaluate_provision", response_model=EffectsSchema)
async def calculate_effects(
    params: Annotated[ProvisionDTO, Depends(ProvisionDTO)],
    token: str = Depends(verify_bearer_token),
) -> EffectsSchema:

    return await effects_service.calculate_effects(params, token)
