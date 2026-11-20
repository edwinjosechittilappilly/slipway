"""Symlinks from harness folders into the Slipway checkout, so `git pull` updates skills and agents in place."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from slipway import paths
from slipway.state import State, now, tree_hash


@dataclass
class LinkResult:
    action: str  # ok | created | retargeted | adopted | replaced | drift | removed | would-<action>
    link: Path
    target: Path
    detail: str = ""


def _points_to(link: Path, target: Path) -> bool:
    try:
        return link.is_symlink() and link.resolve() == target.resolve()
    except OSError:
        return False


def inspect(link: Path, target: Path, state: State) -> str:
    """ok | missing | ours-stale | same-content | foreign (read-only classification)."""
    if _points_to(link, target):
        return "ok"
    if link.is_symlink():
        return "ours-stale" if str(link) in state.section("links") else "foreign"
    if not link.exists():
        return "missing"
    if link.is_dir() and (link / ".git").exists():
        return "foreign"  # a clone with history: never delete it, even if its files match
    if tree_hash(link) == tree_hash(target):
        return "same-content"
    return "foreign"


def ensure(
    link: Path, target: Path, state: State, component: str, force: bool = False, dry_run: bool = False
) -> LinkResult:
    kind = inspect(link, target, state)
    record = {"target": str(target), "component": component}
    if kind == "ok":
        state.section("links")[str(link)] = record
        return LinkResult("ok", link, target)
    if kind == "foreign" and not force:
        return LinkResult("drift", link, target, "yours differs; kept (rerun with --force to back it up and link)")
    action = {"missing": "created", "ours-stale": "retargeted", "same-content": "adopted", "foreign": "replaced"}[kind]
    if dry_run:
        return LinkResult(f"would-{action}", link, target)
    if kind == "ours-stale":
        link.unlink()
    elif kind == "same-content":
        _remove(link)
    elif kind == "foreign":
        # Back up outside the harness folder, or the backup would load as a second skill with the same name.
        backups = paths.state_file().parent / "backups" / "links"
        backups.mkdir(parents=True, exist_ok=True)
        shutil.move(str(link), str(backups / f"{link.parent.name}-{link.name}-{now().replace(':', '')}"))
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=target.is_dir())
    state.section("links")[str(link)] = record
    return LinkResult(action, link, target)


def prune(state: State, components: set[str], dry_run: bool = False) -> list[LinkResult]:
    """Remove links Slipway created whose component left the manifest or whose target left the repo.

    A link is only deleted while it still points where Slipway left it; anything the user re-pointed is forgotten.
    """
    results = []
    recorded = state.section("links")
    for link_str, rec in list(recorded.items()):
        target = Path(rec["target"])
        if rec.get("component") in components and target.exists():
            continue
        link = Path(link_str)
        if link.is_symlink() and str(link.readlink()) == str(target):
            if not dry_run:
                link.unlink()
            results.append(LinkResult("would-remove" if dry_run else "removed", link, target))
        if not dry_run:
            del recorded[link_str]
    return results


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
