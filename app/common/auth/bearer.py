from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

http_bearer = HTTPBearer()


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> str | None:

    token = credentials.credentials
    return token if token not in ["''", '""'] or not token else None
