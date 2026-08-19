from __future__ import annotations

from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

from app.common.api_handler.api_handler import APIHandler
from app.common.auth.service_auth import get_mcp_user_id


class FakeServiceAuth:
    async def get_authorization_headers(self):
        return {"Authorization": "Bearer service-token"}


@pytest.mark.asyncio
async def test_service_token_cannot_be_overridden_by_request_headers():
    handler = APIHandler("http://urban", FakeServiceAuth())

    headers = await handler._service_headers(
        {"Authorization": "Bearer caller-token", "X-User-Id": "u1"}
    )

    assert headers["Authorization"] == "Bearer service-token"
    assert headers["X-User-Id"] == "u1"


def test_mcp_user_context_comes_from_x_user_id_not_authorization():
    with patch(
        "app.common.auth.service_auth.get_http_headers",
        return_value={
            "authorization": "Bearer service-token",
            "x-user-id": " user-42 ",
        },
    ):
        assert get_mcp_user_id() == "user-42"


def test_mcp_user_context_is_required():
    with patch(
        "app.common.auth.service_auth.get_http_headers",
        return_value={"authorization": "Bearer service-token"},
    ):
        with pytest.raises(ToolError, match="X-User-Id header is required"):
            get_mcp_user_id()
