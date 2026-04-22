from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.auth.bearer import verify_bearer_token
from app.dto.provision_dto import ProvisionDTO
from app.provision.provision_service import provision_service
from app.schemas.provision_base_schema import ProvisionSchema

provision_router = APIRouter(prefix="/provision", tags=["provision"])


@provision_router.get("/calc_provision", response_model=ProvisionSchema)
async def calculate_provision(
    provision_dto: Annotated[ProvisionDTO, Depends(ProvisionDTO)],
    token: str = Depends(verify_bearer_token),
) -> ProvisionSchema:

    return await provision_service.calculate_provision(provision_dto, token)
