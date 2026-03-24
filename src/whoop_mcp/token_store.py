"""Token persistence with atomic writes and restrictive POSIX permissions."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from whoop_mcp.exceptions import TokenStoreError
from whoop_mcp.models import TokenBundle


@runtime_checkable
class TokenStore(Protocol):
    """Stores WHOOP OAuth tokens (`offline` scope yields refresh tokens)."""

    def load(self) -> TokenBundle | None:
        """Return stored tokens, or None if the store is empty."""

    def save(self, bundle: TokenBundle) -> None:
        """Persist tokens. Implementations must not partially overwrite on failure."""


def _atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically (same directory) with mode 0600 on POSIX."""

    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp = Path(tmp_path)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if os.name == "posix":
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


class FileTokenStore:
    """JSON file–backed token store (atomic replace, owner read/write only on POSIX)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> TokenBundle | None:
        if not self._path.is_file():
            return None
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError as e:
            raise TokenStoreError(
                f"Cannot read token file: {e}",
                path=str(self._path),
            ) from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise TokenStoreError(
                "Token file does not contain valid JSON.",
                path=str(self._path),
            ) from e
        try:
            return TokenBundle.model_validate(data)
        except Exception as e:
            raise TokenStoreError(
                "Token file JSON does not match the TokenBundle schema.",
                path=str(self._path),
            ) from e

    def save(self, bundle: TokenBundle) -> None:
        payload = bundle.model_dump(mode="json")
        text = json.dumps(payload, indent=2, sort_keys=True)
        try:
            _atomic_write_text(self._path, text + "\n")
        except OSError as e:
            raise TokenStoreError(
                f"Cannot write token file: {e}",
                path=str(self._path),
            ) from e
