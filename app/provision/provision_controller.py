from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.auth.service_auth import get_current_user_id
from app.dependencies import provision_service
from app.dto.provision_dto import ProvisionDTO
from app.schemas.provision_base_schema import (
    MultiProvisionRequestSchema,
    MultiProvisionSchema,
    ProvisionSchema,
)

provision_router = APIRouter(prefix="/provision", tags=["provision"])


@provision_router.get("/calc_provision", response_model=ProvisionSchema)
async def calculate_provision(
    provision_dto: Annotated[ProvisionDTO, Depends(ProvisionDTO)],
    user_id: str = Depends(get_current_user_id),
) -> ProvisionSchema:

    return await provision_service.calculate_provision(provision_dto, user_id)


@provision_router.post("/calc_provisions", response_model=MultiProvisionSchema)
async def calculate_multi_provision(
    multi_provision_params: MultiProvisionRequestSchema,
    user_id: str = Depends(get_current_user_id),
) -> MultiProvisionSchema:

    return await provision_service.calculate_multi_provision(
        multi_provision_params, user_id
    )
