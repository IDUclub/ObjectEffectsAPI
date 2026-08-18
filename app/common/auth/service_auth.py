from __future__ import annotations

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastmcp.exceptions import AuthorizationError, ToolError
from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_http_headers
from idu_service_auth import KeycloakTokenClient, KeycloakTokenConfig

from app.common.config.config import Config

USER_ID_HEADER = "X-User-Id"
SERVICE_ACCOUNT_PREFIX = "service-account-"
bearer_scheme = HTTPBearer(auto_error=True)


def build_service_auth(config: Config) -> KeycloakTokenClient:
    return KeycloakTokenClient(
        KeycloakTokenConfig(
            auth_server_url=config.get("SERVICE_AUTH_SERVER_URL"),
            realm=config.get("SERVICE_AUTH_REALM"),
            client_id=config.get("SERVICE_AUTH_CLIENT_ID"),
            client_secret=config.get("SERVICE_AUTH_CLIENT_SECRET"),
            background_refresh=True,
        )
    )


def build_service_token_verifier(config: Config) -> "ServiceTokenVerifier":
    return ServiceTokenVerifier(config)


async def get_current_user_id(
    _credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
) -> str:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{USER_ID_HEADER} header is required",
        )
    return x_user_id.strip()


async def require_service_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> None:
    """Require a verified Keycloak service-account token."""

    from app.dependencies import service_token_verifier

    try:
        access_token = await service_token_verifier.verify_token(
            credentials.credentials
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        ) from exc
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )


def get_mcp_user_id() -> str:
    user_id = get_http_headers(include_all=True).get("x-user-id", "").strip()
    if not user_id:
        raise ToolError(f"{USER_ID_HEADER} header is required")
    return user_id


class ServiceTokenVerifier(JWTVerifier):
    """Verify Keycloak JWTs and accept only client-credentials accounts."""

    def __init__(self, config: Config) -> None:
        server_url = config.get("SERVICE_AUTH_SERVER_URL").rstrip("/")
        realm = config.get("SERVICE_AUTH_REALM")
        issuer = f"{server_url}/realms/{realm}"
        super().__init__(
            jwks_uri=f"{issuer}/protocol/openid-connect/certs",
            issuer=issuer,
            algorithm="RS256",
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        access_token = await super().verify_token(token)
        if access_token is None:
            return None
        username = access_token.claims.get("preferred_username", "")
        if not isinstance(username, str) or not username.startswith(
            SERVICE_ACCOUNT_PREFIX
        ):
            raise AuthorizationError("A service-account token is required")
        return access_token
