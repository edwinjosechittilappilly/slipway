"""What Slipway last wrote on this machine. Enables the 3-way rule: never clobber values the user changed."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from slipway import paths

IGNORED_NAMES = {".DS_Store", "__pycache__", ".git"}


@dataclass
class State:
    path: Path
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> State:
        path = path or paths.state_file()
        data: dict[str, Any] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("links", "omp", "skills", "installed", "projects"):
            data.setdefault(key, {})
        data.setdefault("version", 1)
        return cls(path, data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def section(self, name: str) -> dict[str, Any]:
        return self.data.setdefault(name, {})

    def mark_installed(self, cid: str, by_slipway: bool, version: str | None = None) -> None:
        entry = self.section("installed").setdefault(cid, {"by_slipway": by_slipway})
        entry["by_slipway"] = entry.get("by_slipway", False) or by_slipway
        entry["at"] = now()
        if version:
            entry["version"] = version


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def tree_hash(path: Path) -> str | None:
    """Content hash of a file or directory tree (relative paths + bytes); None when the path is missing."""
    if not path.exists():
        return None
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for child in sorted(path.rglob("*")):
        if IGNORED_NAMES.intersection(child.relative_to(path).parts) or not child.is_file():
            continue
        digest.update(child.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
