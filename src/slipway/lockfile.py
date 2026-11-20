"""slipway.lock.json: pinned skill-source commits and the npm/brew versions this repo was tested with.

`slipway lock --refresh` resolves upstream heads and versions, rewrites the lock, and reports what changed (with
compare URLs and the skill files touched) so the weekly workflow can open a reviewable PR.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slipway.manifest import Manifest
from slipway.shell import Runner
from slipway.state import now

SHA = re.compile(r"^[0-9a-f]{40}$")


def path_for(manifest: Manifest) -> Path:
    return manifest.root / "slipway.lock.json"


def load(manifest: Manifest) -> dict[str, Any]:
    path = path_for(manifest)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for key in ("skills", "npm", "brew"):
        data.setdefault(key, {})
    return data


def save(manifest: Manifest, data: dict[str, Any]) -> None:
    path_for(manifest).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass
class Change:
    section: str
    key: str
    old: str | None
    new: str
    url: str = ""
    files: list[str] = field(default_factory=list)


def npm_packages(manifest: Manifest) -> list[str]:
    names = {c.name for c in manifest.components if c.kind == "npm" and c.name}
    names |= {manifest.settings.get("skills_cli", "skills")}
    if any(c.kind == "impeccable" for c in manifest.components):
        names.add("impeccable")
    return sorted(n for n in names if n)


def refresh(
    manifest: Manifest, runner: Runner, only: str | None = None
) -> tuple[dict[str, Any], list[Change], list[str]]:
    """Return (new lock, changes, errors). Never raises for one bad upstream; it is reported and the old pin kept."""
    old = load(manifest)
    new: dict[str, Any] = json.loads(json.dumps(old))
    changes: list[Change] = []
    errors: list[str] = []

    if only in (None, "skills"):
        for comp in manifest.components:
            if comp.kind != "skills" or not comp.source:
                continue
            res = runner.run(
                ["git", "ls-remote", f"https://github.com/{comp.source}.git", "HEAD"], mutate=False, check=False
            )
            sha = res.out.split()[0] if res.ok and res.out.strip() else ""
            if not SHA.match(sha):
                errors.append(f"{comp.source}: cannot resolve HEAD ({(res.err or res.out).strip()[:120]})")
                continue
            prev = old["skills"].get(comp.source, {}).get("commit")
            new["skills"][comp.source] = {"commit": sha}
            if prev != sha:
                change = Change("skills", comp.source, prev, sha)
                if prev:
                    change.url = f"https://github.com/{comp.source}/compare/{prev[:12]}...{sha[:12]}"
                    change.files = _changed_skill_files(runner, comp.source, prev, sha, comp.skills)
                changes.append(change)

    if only in (None, "npm"):
        for pkg in npm_packages(manifest):
            res = runner.run(["npm", "view", pkg, "version"], mutate=False, check=False)
            version = res.out.strip().splitlines()[-1] if res.ok and res.out.strip() else ""
            if not version:
                errors.append(f"npm {pkg}: cannot resolve version")
                continue
            if old["npm"].get(pkg) != version:
                changes.append(Change("npm", pkg, old["npm"].get(pkg), version, f"https://www.npmjs.com/package/{pkg}"))
            new["npm"][pkg] = version

    if only in (None, "brew"):
        for comp in manifest.components:
            if comp.kind not in ("brew", "cask") or not comp.name:
                continue
            version = brew_version(runner, comp.kind, comp.name)
            if not version:
                errors.append(f"brew {comp.name}: cannot resolve version")
                continue
            if old["brew"].get(comp.name) != version:
                changes.append(Change("brew", comp.name, old["brew"].get(comp.name), version))
            new["brew"][comp.name] = version

    if changes:
        new["refreshed"] = now()
    return new, changes, errors


def brew_version(runner: Runner, kind: str, name: str) -> str | None:
    """Stable version from `brew info` (handles taps), else the formulae.brew.sh API via curl (system certs)."""
    cask = kind == "cask"
    if runner.which("brew"):
        res = runner.run(["brew", "info", "--json=v2", *(["--cask"] if cask else []), name], mutate=False, check=False)
        try:
            data = json.loads(res.out) if res.ok else {}
        except ValueError:
            data = {}
        items = data.get("casks" if cask else "formulae") or []
        if items:
            return items[0].get("version") if cask else (items[0].get("versions") or {}).get("stable")
    if "/" in name:
        return None  # third-party tap: only `brew info` knows it
    section = "cask" if cask else "formula"
    res = runner.run(
        ["curl", "-fsSL", f"https://formulae.brew.sh/api/{section}/{name}.json"], mutate=False, check=False
    )
    try:
        data = json.loads(res.out) if res.ok else {}
    except ValueError:
        return None
    return data.get("version") if cask else (data.get("versions") or {}).get("stable")


def _changed_skill_files(runner: Runner, source: str, old: str, new: str, skills: list[str]) -> list[str]:
    res = runner.run(
        ["gh", "api", f"repos/{source}/compare/{old}...{new}", "--jq", ".files[].filename"], mutate=False, check=False
    )
    if not res.ok:
        return []
    wanted = set(skills)
    return [f for f in res.out.splitlines() if wanted.intersection(f.split("/"))]


def changes_markdown(changes: list[Change], errors: list[str]) -> str:
    """PR body for the upstream-watch workflow."""
    lines = ["## Upstream changes", ""]
    if not changes:
        lines.append("No upstream changes.")
    for ch in changes:
        head = f"- **{ch.section}** `{ch.key}`: `{(ch.old or 'none')[:12]}` → `{ch.new[:12]}`"
        lines.append(head + (f" ([diff]({ch.url}))" if ch.url else ""))
        lines += [f"  - `{f}`" for f in ch.files]
    if errors:
        lines += ["", "## Could not refresh", ""] + [f"- {e}" for e in errors]
    lines += [
        "",
        "## Review checklist",
        "",
        "- [ ] Read the changed `SKILL.md` files: skills are prompts that run with your agent's permissions.",
        "- [ ] Renamed or removed skills: update the `skills` lists in `slipway.toml`.",
        "- [ ] CI is green (`make check`).",
    ]
    return "\n".join(lines) + "\n"
