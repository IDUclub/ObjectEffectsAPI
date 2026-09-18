from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.api_handler.api_handler import APIHandler
from app.common.api_handler.urban_api_url import normalize_urban_api_url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "base, api_root",
    [
        ("https://urban.test:8443", "https://urban.test:8443/api"),
        ("https://urban.test:8443/", "https://urban.test:8443/api"),
        ("https://urban.test:8443/api", "https://urban.test:8443/api"),
        (" https://urban.test:8443/api/// ", "https://urban.test:8443/api"),
        (
            "https://prostor-api.idu.actocgnitive.org/urban_api",
            "https://prostor-api.idu.actocgnitive.org/urban_api",
        ),
        (
            "https://prostor-api.idu.actocgnitive.org/urban_api/",
            "https://prostor-api.idu.actocgnitive.org/urban_api",
        ),
        (
            "https://urban.test/gateway/urban_api/",
            "https://urban.test/gateway/urban_api",
        ),
    ],
)
@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
@pytest.mark.parametrize(
    "endpoint",
    ["/api/v1/scenarios/7", "api/v1/scenarios/7", "/v1/scenarios/7", "v1/scenarios/7"],
)
async def test_requests_use_configured_api_root(base, api_root, method, endpoint):
    auth = MagicMock()
    auth.get_authorization_headers = AsyncMock(
        return_value={"Authorization": "Bearer service"}
    )
    handler = APIHandler(base, auth)
    session = MagicMock()
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"ok": True})
    request = getattr(session, method)
    request.return_value.__aenter__.return_value = response

    assert await getattr(handler, method)(
        endpoint, session=session, params={"page": 2}
    ) == {"ok": True}

    assert request.call_args.kwargs["url"] == f"{api_root}/v1/scenarios/7"
    assert request.call_args.kwargs["params"] == {"page": 2}
    assert request.call_args.kwargs["headers"] == {"Authorization": "Bearer service"}


@pytest.mark.parametrize(
    "base, expected",
    [
        ("http://api", "http://api/api"),
        ("https://urban.test/gateway/api/", "https://urban.test/gateway/api"),
        ("https://urban.test/gateway/", "https://urban.test/gateway"),
        ("https://urban.test/api/api/", "https://urban.test/api/api"),
    ],
)
def test_normalization_preserves_authority_and_proxy_path(base, expected):
    assert normalize_urban_api_url(base) == expected
    assert normalize_urban_api_url(expected) == expected


@pytest.mark.parametrize(
    "base",
    [
        "",
        "urban.test",
        "ftp://urban.test",
        "https://urban.test?x=1",
        "https://urban.test#fragment",
    ],
)
def test_invalid_base_url_is_rejected(base):
    with pytest.raises(ValueError, match="Urban API URL"):
        normalize_urban_api_url(base)
