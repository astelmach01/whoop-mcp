"""Tests for settings loading."""

from __future__ import annotations

import pytest

from whoop_mcp.settings import WhoopSettings, get_settings


def _minimal_whoop_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://example.com/callback")


def test_whoop_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://example.com/callback")

    s = WhoopSettings()
    assert s.client_id == "test-client"
    assert s.client_secret.get_secret_value() == "secret"
    assert str(s.authorization_url) == "https://api.prod.whoop.com/oauth/oauth2/auth"
    assert str(s.token_url) == "https://api.prod.whoop.com/oauth/oauth2/token"
    assert str(s.api_base_url) == "https://api.prod.whoop.com/developer"
    assert "offline" in s.scope_list()


def test_scope_list_splits_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "x")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "y")
    monkeypatch.setenv("WHOOP_REDIRECT_URI", "https://example.com/cb")
    monkeypatch.setenv("WHOOP_DEFAULT_SCOPES", "read:profile  offline")

    s = WhoopSettings()
    assert s.scope_list() == ["read:profile", "offline"]


def test_whoop_http_timeout_seconds_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _minimal_whoop_env(monkeypatch)
    monkeypatch.setenv("WHOOP_HTTP_TIMEOUT_SECONDS", "45.5")

    s = WhoopSettings()
    assert s.http_timeout_seconds == 45.5


def test_whoop_log_level_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _minimal_whoop_env(monkeypatch)
    monkeypatch.setenv("WHOOP_LOG_LEVEL", "DEBUG")

    s = WhoopSettings()
    assert s.log_level == "DEBUG"


def test_whoop_token_store_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _minimal_whoop_env(monkeypatch)
    monkeypatch.setenv("WHOOP_TOKEN_STORE_PATH", "/tmp/whoop_tokens.json")

    s = WhoopSettings()
    assert s.token_store_path == "/tmp/whoop_tokens.json"


def test_get_settings_returns_cached_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    _minimal_whoop_env(monkeypatch)

    first = get_settings()
    second = get_settings()
    assert first is second
    assert id(first) == id(second)
