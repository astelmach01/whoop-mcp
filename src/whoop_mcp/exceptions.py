"""WHOOP OAuth and Developer API error types (no silent failures)."""

from __future__ import annotations


class WhoopError(Exception):
    """Base error for this package."""


class WhoopOAuthError(WhoopError):
    """Token endpoint returned a non-success status or an invalid payload."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WhoopApiError(WhoopError):
    """Developer API request failed (after transport; HTTP layer)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        method: str,
        url: str,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.url = url
        self.response_text = response_text


class TokenStoreError(WhoopError):
    """Token file is missing, unreadable, or violates the expected schema."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path


class TokenRefreshError(WhoopError):
    """Refresh token flow failed or no refresh token is available."""
