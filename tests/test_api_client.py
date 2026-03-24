"""Tests for WhoopApiClient authenticated HTTP wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from whoop_mcp.api_client import WhoopApiClient
from whoop_mcp.models import TokenBundle
from whoop_mcp.settings import WhoopSettings


@pytest.mark.asyncio
async def test_request_get_profile_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/oauth/callback")

    settings = WhoopSettings()
    token_bundle = TokenBundle(access_token="test-bearer-token")

    mock_response = httpx.Response(
        200,
        json={"user_id": 1},
        request=httpx.Request(
            "GET",
            "https://api.prod.whoop.com/developer/v2/user/profile/basic",
        ),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_response)

    client = WhoopApiClient(
        settings,
        token_bundle=token_bundle,
        httpx_client=mock_client,
    )
    response = await client.request("GET", "/v2/user/profile/basic")

    assert response.status_code == 200
    assert response.json() == {"user_id": 1}

    mock_client.request.assert_called_once()
    call_args = mock_client.request.call_args
    assert call_args.args[0] == "GET"
    assert call_args.args[1].endswith("/v2/user/profile/basic")
    assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-bearer-token"
