"""Load persisted OAuth tokens and refresh the access token when needed (stdio MCP server)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx

from whoop_mcp.exceptions import TokenRefreshError, TokenStoreError
from whoop_mcp.models import TokenBundle
from whoop_mcp.oauth import refresh_access_token
from whoop_mcp.settings import WhoopSettings
from whoop_mcp.token_store import FileTokenStore

_refresh_lock = asyncio.Lock()


def _store(settings: WhoopSettings) -> FileTokenStore:
    return FileTokenStore(Path(settings.token_store_path))


async def get_valid_token_bundle(settings: WhoopSettings) -> TokenBundle:
    """Return a token bundle usable for API calls, refreshing and persisting when needed."""

    async with _refresh_lock:
        store = _store(settings)
        bundle = store.load()
        if bundle is None:
            raise TokenStoreError(
                "No OAuth tokens found. Run `uv run whoop-mcp login` once to authorize.",
                path=settings.token_store_path,
            )
        if not bundle.needs_access_token_refresh(
            skew_seconds=settings.token_refresh_skew_seconds,
        ):
            return bundle
        if bundle.refresh_token is None:
            raise TokenRefreshError(
                "Access token is expired and no refresh token is stored. "
                "Run `uv run whoop-mcp login`.",
            )
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            oauth = await refresh_access_token(
                settings,
                refresh_token=bundle.refresh_token,
                httpx_client=client,
            )
        issued_at = datetime.now(UTC)
        updated = bundle.merged_with_refresh_response(oauth, issued_at=issued_at)
        store.save(updated)
        return updated
