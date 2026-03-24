"""Pydantic v2 models aligned with the WHOOP Developer API OpenAPI specification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    raise TypeError(f"expected datetime or ISO string, got {type(v).__name__}")


DateTime = Annotated[datetime, BeforeValidator(_parse_dt)]


class WhoopScope(StrEnum):
    """OAuth scopes from the WHOOP API reference."""

    OFFLINE = "offline"
    READ_RECOVERY = "read:recovery"
    READ_CYCLES = "read:cycles"
    READ_WORKOUT = "read:workout"
    READ_SLEEP = "read:sleep"
    READ_PROFILE = "read:profile"
    READ_BODY_MEASUREMENT = "read:body_measurement"


class ScoreState(StrEnum):
    SCORED = "SCORED"
    PENDING_SCORE = "PENDING_SCORE"
    UNSCORABLE = "UNSCORABLE"


# --- OAuth ---


class OAuthTokenResponse(BaseModel):
    """Token endpoint JSON (authorization code and refresh flows)."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Lifetime of the access token in seconds.")
    refresh_token: str | None = None
    scope: str | None = None


class TokenBundle(BaseModel):
    """OAuth credentials persisted between sessions (memory or disk)."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    scope: str | None = None
    expires_in: int | None = Field(
        default=None,
        description="Seconds until access token expiry from the last token response.",
    )
    access_token_expires_at: datetime | None = Field(
        default=None,
        description="UTC time when the access token expires (derived from expires_in).",
    )

    def needs_access_token_refresh(self, *, skew_seconds: float) -> bool:
        """True when the access token should be refreshed proactively."""

        if self.refresh_token is None:
            return False
        if self.access_token_expires_at is None:
            return True
        now = datetime.now(UTC)
        return now >= self.access_token_expires_at - timedelta(seconds=skew_seconds)

    @classmethod
    def from_oauth_response(
        cls,
        response: OAuthTokenResponse,
        *,
        issued_at: datetime | None = None,
    ) -> Self:
        issued_at = issued_at or datetime.now(UTC)
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=UTC)
        expires_at: datetime | None = None
        if response.expires_in > 0:
            expires_at = issued_at + timedelta(seconds=response.expires_in)
        return cls(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            token_type=response.token_type,
            scope=response.scope,
            expires_in=response.expires_in,
            access_token_expires_at=expires_at,
        )

    def merged_with_refresh_response(
        self,
        response: OAuthTokenResponse,
        *,
        issued_at: datetime,
    ) -> Self:
        """Apply a refresh response; keep prior refresh_token if the response omits a new one."""

        new = self.from_oauth_response(response, issued_at=issued_at)
        if new.refresh_token is None and self.refresh_token is not None:
            return new.model_copy(update={"refresh_token": self.refresh_token})
        return new


# --- Pagination (query) ---


class PaginatedListParams(BaseModel):
    """Query parameters for WHOOP collection endpoints (GET /v2/cycle, sleep, recovery, workout)."""

    model_config = ConfigDict(extra="forbid")

    limit: int | None = Field(default=None, ge=1, le=25)
    start: DateTime | None = Field(
        default=None,
        description="Inclusive lower bound on activity time (ISO 8601 date-time).",
    )
    end: DateTime | None = Field(
        default=None,
        description="Exclusive upper bound; API defaults to `now` when omitted.",
    )
    next_token: str | None = Field(
        default=None,
        description="Cursor from the previous response's `next_token` field.",
    )

    def to_query_params(self) -> dict[str, str | int]:
        q: dict[str, str | int] = {}
        if self.limit is not None:
            q["limit"] = self.limit
        if self.start is not None:
            q["start"] = self.start.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if self.end is not None:
            q["end"] = self.end.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if self.next_token is not None:
            q["nextToken"] = self.next_token
        return q


# --- User ---


class UserBasicProfile(BaseModel):
    """GET /v2/user/profile/basic"""

    model_config = ConfigDict(extra="ignore")

    user_id: int
    email: str
    first_name: str
    last_name: str


class UserBodyMeasurement(BaseModel):
    """GET /v2/user/measurement/body"""

    model_config = ConfigDict(extra="ignore")

    height_meter: float
    weight_kilogram: float
    max_heart_rate: int


# --- Cycle ---


class CycleScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strain: float
    kilojoule: float
    average_heart_rate: int
    max_heart_rate: int


class Cycle(BaseModel):
    """GET /v2/cycle/{cycleId} and cycle records in collections."""

    model_config = ConfigDict(extra="ignore")

    id: int
    user_id: int
    created_at: DateTime
    updated_at: DateTime
    start: DateTime
    end: DateTime | None = None
    timezone_offset: str
    score_state: ScoreState
    score: CycleScore | None = None


class PaginatedCycleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    records: list[Cycle] = Field(default_factory=list)
    next_token: str | None = None


# --- Sleep ---


class SleepStageSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_in_bed_time_milli: int
    total_awake_time_milli: int
    total_no_data_time_milli: int
    total_light_sleep_time_milli: int
    total_slow_wave_sleep_time_milli: int
    total_rem_sleep_time_milli: int
    sleep_cycle_count: int
    disturbance_count: int


class SleepNeeded(BaseModel):
    model_config = ConfigDict(extra="ignore")

    baseline_milli: int
    need_from_sleep_debt_milli: int
    need_from_recent_strain_milli: int
    need_from_recent_nap_milli: int


class SleepScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stage_summary: SleepStageSummary
    sleep_needed: SleepNeeded
    respiratory_rate: float | None = None
    sleep_performance_percentage: float | None = None
    sleep_consistency_percentage: float | None = None
    sleep_efficiency_percentage: float | None = None


class Sleep(BaseModel):
    """GET /v2/activity/sleep/{sleepId} and sleep records in collections."""

    model_config = ConfigDict(extra="ignore")

    id: str
    cycle_id: int
    user_id: int
    created_at: DateTime
    updated_at: DateTime
    start: DateTime
    end: DateTime
    timezone_offset: str
    nap: bool
    score_state: ScoreState
    v1_id: int | None = None
    score: SleepScore | None = None


class PaginatedSleepResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    records: list[Sleep] = Field(default_factory=list)
    next_token: str | None = None


# --- Recovery ---


class RecoveryScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_calibrating: bool
    recovery_score: float
    resting_heart_rate: float
    hrv_rmssd_milli: float
    spo2_percentage: float | None = None
    skin_temp_celsius: float | None = None


class Recovery(BaseModel):
    """GET /v2/cycle/{cycleId}/recovery and recovery records in collections."""

    model_config = ConfigDict(extra="ignore")

    cycle_id: int
    sleep_id: str
    user_id: int
    created_at: DateTime
    updated_at: DateTime
    score_state: ScoreState
    score: RecoveryScore | None = None


class RecoveryCollection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    records: list[Recovery] = Field(default_factory=list)
    next_token: str | None = None


# --- Workout ---


class ZoneDurations(BaseModel):
    model_config = ConfigDict(extra="ignore")

    zone_zero_milli: int
    zone_one_milli: int
    zone_two_milli: int
    zone_three_milli: int
    zone_four_milli: int
    zone_five_milli: int


class WorkoutScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strain: float
    average_heart_rate: int
    max_heart_rate: int
    kilojoule: float
    percent_recorded: float
    distance_meter: float | None = None
    altitude_gain_meter: float | None = None
    altitude_change_meter: float | None = None
    zone_durations: ZoneDurations


class WorkoutV2(BaseModel):
    """GET /v2/activity/workout/{workoutId} and workout records in collections."""

    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: int
    created_at: DateTime
    updated_at: DateTime
    start: DateTime
    end: DateTime
    timezone_offset: str
    sport_name: str
    score_state: ScoreState
    score: WorkoutScore | None = None
    v1_id: int | None = None
    sport_id: int | None = None


class WorkoutCollection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    records: list[WorkoutV2] = Field(default_factory=list)
    next_token: str | None = None
