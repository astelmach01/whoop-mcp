"""Shared pytest configuration."""

from __future__ import annotations

import pytest

from whoop_mcp.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
