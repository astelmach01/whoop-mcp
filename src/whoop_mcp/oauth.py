"""WHOOP OAuth 2.0 helpers (authorization code + refresh). Official flow per WHOOP docs."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from whoop_mcp.exceptions import WhoopOAuthError
from whoop_mcp.models import OAuthTokenResponse
from whoop_mcp.settings import WhoopSettings


def build_authorization_url(
    settings: WhoopSettings,
    *,
    state: str,
    scopes: list[str] | None = None,
) -> str:
    """Build the user-facing authorization URL (step 1 of the authorization code grant).

    WHOOP documents an eight-character `state` value for CSRF protection.
    """

    if len(state) != 8:
        msg = "WHOOP documents `state` as eight characters for CSRF protection."
        raise ValueError(msg)

    scope_list = scopes if scopes is not None else settings.scope_list()
    query = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": str(settings.redirect_uri),
        "scope": " ".join(scope_list),
        "state": state,
    }
    base = str(settings.authorization_url).rstrip("/")
    return f"{base}?{urlencode(query)}"


async def exchange_authorization_code(
    settings: WhoopSettings,
    *,
    code: str,
    httpx_client: httpx.AsyncClient | None = None,
) -> OAuthTokenResponse:
    """Exchange an authorization code for tokens at the WHOOP token URL."""

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret.get_secret_value(),
        "redirect_uri": str(settings.redirect_uri),
    }
    return await _post_token(settings, data, httpx_client)


async def refresh_access_token(
    settings: WhoopSettings,
    *,
    refresh_token: str,
    httpx_client: httpx.AsyncClient | None = None,
) -> OAuthTokenResponse:
    """Refresh tokens; requires prior `offline` scope during authorization.

    WHOOP rotates refresh tokens: the response refresh token replaces the prior one.
    """

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret.get_secret_value(),
        "scope": "offline",
    }
    return await _post_token(settings, data, httpx_client)


def _oauth_token_response_from_json(payload: dict[str, object]) -> OAuthTokenResponse:
    try:
        return OAuthTokenResponse.model_validate(payload)
    except Exception as e:
        raise WhoopOAuthError(
            "Token endpoint returned JSON that does not match the expected OAuth token shape.",
            response_text=str(payload),
        ) from e


async def _post_token(
    settings: WhoopSettings,
    data: dict[str, str],
    httpx_client: httpx.AsyncClient | None,
) -> OAuthTokenResponse:
    client_owned = httpx_client is None
    client = httpx_client or httpx.AsyncClient(timeout=settings.http_timeout_seconds)
    try:
        response = await client.post(
            str(settings.token_url),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.is_error:
            raise WhoopOAuthError(
                f"Token endpoint HTTP {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return _oauth_token_response_from_json(response.json())
    finally:
        if client_owned:
            await client.aclose()
