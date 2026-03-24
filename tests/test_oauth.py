"""Tests for OAuth URL construction and token exchange helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from whoop_mcp.models import OAuthTokenResponse
from whoop_mcp.oauth import (
    build_authorization_url,
    exchange_authorization_code,
    refresh_access_token,
)
from whoop_mcp.settings import WhoopSettings


def test_build_authorization_url_requires_eight_char_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "sec")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/callback")

    settings = WhoopSettings()
    with pytest.raises(ValueError, match="eight characters"):
        build_authorization_url(settings, state="short")


def test_build_authorization_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "sec")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/cb?x=1")
    monkeypatch.setenv("WHOOP_DEFAULT_SCOPES", "read:profile offline")

    settings = WhoopSettings()
    url = build_authorization_url(settings, state="abcdefgh")
    assert url.startswith("https://api.prod.whoop.com/oauth/oauth2/auth?")
    assert "response_type=code" in url
    assert "client_id=cid" in url
    assert "state=abcdefgh" in url
    # redirect_uri value must be percent-encoded in the query (e.g. ? and : in the URI)
    assert "redirect_uri=https%3A%2F%2Fapp.local%2Fcb%3Fx%3D1" in url


def test_build_authorization_url_custom_scopes_override_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "sec")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/callback")
    monkeypatch.setenv(
        "WHOOP_DEFAULT_SCOPES",
        "read:profile offline read:sleep read:recovery",
    )

    settings = WhoopSettings()
    url = build_authorization_url(
        settings,
        state="abcdefgh",
        scopes=["read:workout", "read:body_measurement"],
    )
    assert "read%3Aworkout" in url
    assert "read%3Abody_measurement" in url
    assert "read%3Asleep" not in url
    assert "read%3Aprofile" not in url


@pytest.mark.asyncio
async def test_exchange_authorization_code_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "sec")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/callback")

    settings = WhoopSettings()
    mock_response = httpx.Response(
        200,
        json={
            "access_token": "at",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "rt",
            "scope": "offline read:profile",
        },
        request=httpx.Request("POST", "https://api.prod.whoop.com/oauth/oauth2/token"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    token = await exchange_authorization_code(settings, code="abc", httpx_client=mock_client)

    assert isinstance(token, OAuthTokenResponse)
    assert token.access_token == "at"
    assert token.refresh_token == "rt"


@pytest.mark.asyncio
async def test_refresh_access_token_parses_json_and_posts_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "sec")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://app.local/callback")

    settings = WhoopSettings()
    mock_response = httpx.Response(
        200,
        json={
            "access_token": "at_new",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "rt_new",
            "scope": "offline read:profile",
        },
        request=httpx.Request("POST", str(settings.token_url)),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    token = await refresh_access_token(
        settings,
        refresh_token="rt_in",
        httpx_client=mock_client,
    )

    assert isinstance(token, OAuthTokenResponse)
    assert token.access_token == "at_new"
    assert token.refresh_token == "rt_new"

    mock_client.post.assert_called_once()
    _args, kwargs = mock_client.post.call_args
    data = kwargs["data"]
    assert data["grant_type"] == "refresh_token"
    assert data["refresh_token"] == "rt_in"
    assert "offline" in data["scope"]
    assert data["client_id"] == "cid"
    assert data["client_secret"] == "sec"
