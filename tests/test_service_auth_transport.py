from __future__ import annotations

import pytest

from app.common.api_handler.api_handler import APIHandler


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
