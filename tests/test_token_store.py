"""Tests for file-backed token persistence."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from whoop_mcp.models import TokenBundle
from whoop_mcp.token_store import FileTokenStore


def test_file_token_store_roundtrip_matches_token_bundle(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "tokens.json"
    store = FileTokenStore(path)
    bundle = TokenBundle(
        access_token="access",
        refresh_token="refresh",
        expires_in=3600,
        token_type="bearer",
        scope="offline",
    )
    store.save(bundle)

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert TokenBundle.model_validate(data) == bundle

    loaded = store.load()
    assert loaded == bundle


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode assertions")
def test_saved_file_mode_is_0600_on_posix(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    store = FileTokenStore(path)
    store.save(TokenBundle(access_token="x"))

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_then_load_integration(tmp_path: Path) -> None:
    """After a successful save, the final path exists and load() returns the bundle."""
    path = tmp_path / "tokens.json"
    store = FileTokenStore(path)
    bundle = TokenBundle(access_token="after-save", refresh_token="rt")
    store.save(bundle)

    assert path.is_file()
    assert store.load() == bundle
