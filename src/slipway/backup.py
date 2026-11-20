"""Snapshot the user config files a run may touch, before it touches them. Keeps the newest few snapshots."""

from __future__ import annotations

import tarfile
from pathlib import Path

from slipway import paths
from slipway.state import now

KEEP = 5


def candidates() -> list[Path]:
    """Files Slipway or the installers it calls may modify (instruction files, harness settings, omp config, locks)."""
    files = [f() for f in paths.INSTRUCTION_FILES.values()]
    files += [
        paths.omp_agent_dir() / "config.yml",
        paths.claude_dir() / "settings.json",
        paths.codex_dir() / "hooks.json",
        paths.codex_dir() / "config.toml",
        paths.skill_lock_file(),
    ]
    return [f for f in files if f.is_file()]


def snapshot(directory: Path | None = None) -> Path | None:
    """Write `backup-<time>.tar.gz` of the existing candidate files; return its path (None if nothing to save)."""
    files = candidates()
    if not files:
        return None
    directory = directory or paths.state_file().parent / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"backup-{now().replace(':', '')}.tar.gz"
    home = paths.home()
    with tarfile.open(target, "w:gz") as tar:
        for file in files:
            try:
                arcname = str(file.relative_to(home))
            except ValueError:
                arcname = str(file).lstrip("/")
            tar.add(file, arcname=arcname)
    for old in sorted(directory.glob("backup-*.tar.gz"))[:-KEEP]:
        old.unlink()
    return target
