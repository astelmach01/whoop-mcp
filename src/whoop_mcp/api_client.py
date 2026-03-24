"""Async WHOOP Developer API client with optional proactive refresh and 401 retry."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx

from whoop_mcp.exceptions import TokenRefreshError, WhoopApiError
from whoop_mcp.models import (
    Cycle,
    PaginatedCycleResponse,
    PaginatedListParams,
    PaginatedSleepResponse,
    Recovery,
    RecoveryCollection,
    Sleep,
    TokenBundle,
    UserBasicProfile,
    UserBodyMeasurement,
    WorkoutCollection,
    WorkoutV2,
)
from whoop_mcp.oauth import refresh_access_token
from whoop_mcp.settings import WhoopSettings
from whoop_mcp.token_store import TokenStore

T = TypeVar("T")


class WhoopApiClient:
    """Bearer-authenticated access to documented WHOOP API paths under `api_base_url`.

    Refresh tokens rotate: after a successful refresh, use the new refresh token on the
    next refresh (WHOOP invalidates the previous refresh token). Concurrent API calls
    coordinate refresh with a lock and a token generation counter so only one refresh
    runs for a batch of 401 responses.
    """

    def __init__(
        self,
        settings: WhoopSettings,
        *,
        token_bundle: TokenBundle,
        httpx_client: httpx.AsyncClient | None = None,
        token_store: TokenStore | None = None,
    ) -> None:
        self._settings = settings
        self._token = token_bundle.model_copy(deep=True)
        self._token_store = token_store
        self._refresh_lock = asyncio.Lock()
        self._token_generation = 0
        self._owns_client = httpx_client is None
        self._client = httpx_client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
        )

    @property
    def token_bundle(self) -> TokenBundle:
        """Current credentials (updated after refresh)."""

        return self._token.model_copy(deep=True)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _base_url(self) -> str:
        return str(self._settings.api_base_url).rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self._base_url()}/{path.lstrip('/')}"

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token.access_token}",
            "Accept": "application/json",
        }

    async def _ensure_proactive_refresh(self) -> None:
        if not self._token.needs_access_token_refresh(
            skew_seconds=self._settings.token_refresh_skew_seconds,
        ):
            return
        gen = self._token_generation
        async with self._refresh_lock:
            if self._token_generation != gen:
                return
            await self._perform_refresh()

    async def _perform_refresh(self) -> None:
        if not self._token.refresh_token:
            raise TokenRefreshError(
                "No refresh_token available; re-authorize with `offline` scope.",
            )
        issued_at = datetime.now(UTC)
        response = await refresh_access_token(
            self._settings,
            refresh_token=self._token.refresh_token,
            httpx_client=self._client,
        )
        self._token = self._token.merged_with_refresh_response(response, issued_at=issued_at)
        self._token_generation += 1
        if self._token_store is not None:
            self._token_store.save(self._token)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        """Perform an authenticated request (low-level). On 401, refresh once if possible."""

        await self._ensure_proactive_refresh()
        url = self._url(path)
        gen = self._token_generation
        response = await self._client.request(
            method,
            url,
            headers=self._auth_headers(),
            params=params,
            json=json,
        )
        if response.status_code == 401 and self._token.refresh_token is not None:
            async with self._refresh_lock:
                if self._token_generation != gen:
                    pass
                else:
                    await self._perform_refresh()
            response = await self._client.request(
                method,
                url,
                headers=self._auth_headers(),
                params=params,
                json=json,
            )
        return response

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        model: type[T],
    ) -> T:
        response = await self.request("GET", path, params=params)
        if response.is_error:
            raise WhoopApiError(
                f"WHOOP API returned HTTP {response.status_code}",
                status_code=response.status_code,
                method="GET",
                url=str(response.request.url),
                response_text=response.text,
            )
        try:
            return model.model_validate(response.json())
        except Exception as e:
            raise WhoopApiError(
                f"Response JSON does not match {model.__name__}",
                status_code=response.status_code,
                method="GET",
                url=str(response.request.url),
                response_text=response.text,
            ) from e

    async def get_user_profile_basic(self) -> UserBasicProfile:
        return await self._get_json("/v2/user/profile/basic", model=UserBasicProfile)

    async def get_user_body_measurement(self) -> UserBodyMeasurement:
        return await self._get_json("/v2/user/measurement/body", model=UserBodyMeasurement)

    async def list_cycles(
        self,
        params: PaginatedListParams | None = None,
    ) -> PaginatedCycleResponse:
        q = params.to_query_params() if params else None
        return await self._get_json("/v2/cycle", params=q, model=PaginatedCycleResponse)

    async def get_cycle(self, cycle_id: int) -> Cycle:
        return await self._get_json(f"/v2/cycle/{cycle_id}", model=Cycle)

    async def list_sleep(self, params: PaginatedListParams | None = None) -> PaginatedSleepResponse:
        q = params.to_query_params() if params else None
        return await self._get_json("/v2/activity/sleep", params=q, model=PaginatedSleepResponse)

    async def get_sleep(self, sleep_id: str) -> Sleep:
        return await self._get_json(f"/v2/activity/sleep/{sleep_id}", model=Sleep)

    async def get_sleep_for_cycle(self, cycle_id: int) -> Sleep:
        return await self._get_json(f"/v2/cycle/{cycle_id}/sleep", model=Sleep)

    async def list_recovery(self, params: PaginatedListParams | None = None) -> RecoveryCollection:
        q = params.to_query_params() if params else None
        return await self._get_json("/v2/recovery", params=q, model=RecoveryCollection)

    async def get_recovery_for_cycle(self, cycle_id: int) -> Recovery:
        return await self._get_json(f"/v2/cycle/{cycle_id}/recovery", model=Recovery)

    async def list_workouts(self, params: PaginatedListParams | None = None) -> WorkoutCollection:
        q = params.to_query_params() if params else None
        return await self._get_json("/v2/activity/workout", params=q, model=WorkoutCollection)

    async def get_workout(self, workout_id: str) -> WorkoutV2:
        return await self._get_json(f"/v2/activity/workout/{workout_id}", model=WorkoutV2)
