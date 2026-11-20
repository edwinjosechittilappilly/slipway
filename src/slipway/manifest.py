"""Load slipway.toml, apply the profile and local overlays, validate, and select packs."""

from __future__ import annotations

import copy
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slipway import paths

KIND_FIELDS: dict[str, tuple[str, ...]] = {
    # kind -> required fields (besides id, kind, pack)
    "brew": ("name",),
    "cask": ("name",),
    "npm": ("name",),
    "script": ("install",),
    "skills": ("source", "skills"),
    "impeccable": ("providers",),
    "claude-plugin": ("marketplace", "plugin"),
    "omp-plugin": ("plugin",),
    "link": ("dir", "targets"),
    "block": ("file", "targets"),
    "omp-config": (),
}
HARNESSES = ("omp", "claude", "codex", "gemini", "cursor-agent", "opencode")


class ManifestError(ValueError):
    pass


@dataclass
class Component:
    id: str
    kind: str
    pack: str
    why: str = ""
    name: str | None = None  # brew formula, cask, or npm package
    bin: str | None = None  # executable that proves the tool is installed
    install: str | None = None  # script kind: shell command
    upgrade: str | None = None  # script kind: shell command
    check: str | None = None  # shell command; exit 0 means installed (overrides the `bin` lookup)
    source: str | None = None  # skills: owner/repo
    agents: list[str] = field(default_factory=list)  # skills: npx skills -a targets (default settings.skill_agents)
    skills: list[str] = field(default_factory=list)
    marketplace: str | None = None
    plugin: str | None = None
    providers: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    dir: str | None = None  # link: repo-relative source dir
    pattern: str = "*"  # link: glob inside dir
    targets: list[str] = field(default_factory=list)
    file: str | None = None  # block: repo-relative content file
    platforms: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    enabled: bool = True  # set false in a profile or local overlay to skip one component

    @property
    def label(self) -> str:
        return self.id


@dataclass
class Role:
    name: str
    harness: str
    model: str
    why: str = ""
    alt: dict[str, str] = field(default_factory=dict)  # harness -> model for `slipway run --harness`


@dataclass
class Manifest:
    root: Path
    settings: dict[str, Any]
    packs: dict[str, dict[str, Any]]
    components: list[Component]
    roles: dict[str, Role]
    omp: dict[str, Any]
    project: dict[str, Any]
    profile: str | None
    default_packs: list[str]

    def component(self, cid: str) -> Component:
        for comp in self.components:
            if comp.id == cid:
                return comp
        raise KeyError(cid)

    def select(self, packs: list[str] | None = None, all_packs: bool = False) -> list[Component]:
        chosen = list(self.packs) if all_packs else (packs or self.default_packs)
        unknown = [p for p in chosen if p not in self.packs]
        if unknown:
            raise ManifestError(f"unknown pack(s): {', '.join(unknown)}; known: {', '.join(self.packs)}")
        platform = "darwin" if os.uname().sysname == "Darwin" else "linux"
        return [
            c
            for c in self.components
            if c.enabled and c.pack in chosen and (not c.platforms or platform in c.platforms)
        ]


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in over.items():
        if key == "component":
            out[key] = _merge_components(out.get(key, []), value)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _merge_components(base: list[dict], over: list[dict]) -> list[dict]:
    merged = [dict(c) for c in base]
    index = {c.get("id"): i for i, c in enumerate(merged)}
    for comp in over:
        if comp.get("id") in index:
            merged[index[comp["id"]]].update(comp)
        else:
            index[comp.get("id")] = len(merged)
            merged.append(dict(comp))
    return merged


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{path}: {exc}") from exc


def remember_profile(name: str) -> bool:
    """Persist `profile = "<name>"` in the local config so later runs need no flag. Returns True if it changed."""
    path = paths.local_config_file()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    line = f'profile = "{name}"'
    if re.search(rf"^{re.escape(line)}\s*$", text, re.MULTILINE):
        return False
    if re.search(r"^profile\s*=.*$", text, re.MULTILINE):
        text = re.sub(r"^profile\s*=.*$", line, text, count=1, flags=re.MULTILINE)
    else:
        header = "# Machine-local Slipway settings (overlay on slipway.toml; see docs/configuration.md)\n"
        text = f"{line}\n{text}" if text else f"{header}{line}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def profile_dirs(root: Path) -> list[Path]:
    """Your profiles (~/.config/slipway/profiles, never touched by git pull) first, then the ones shipped here."""
    return [paths.local_config_file().parent / "profiles", root / "profiles"]


def find_profile(root: Path, name: str) -> Path | None:
    return next((d / f"{name}.toml" for d in profile_dirs(root) if (d / f"{name}.toml").is_file()), None)


def list_profiles(root: Path) -> list[str]:
    return sorted({p.stem for d in profile_dirs(root) for p in d.glob("*.toml")})


def load(root: Path | None = None, profile: str | None = None, use_local: bool = True) -> Manifest:
    root = root or paths.repo_root()
    base_file = root / "slipway.toml"
    if not base_file.exists():
        raise ManifestError(f"no slipway.toml in {root} (set SLIPWAY_HOME to your Slipway checkout)")
    data = _read_toml(base_file)
    overlays: list[dict[str, Any]] = []

    local: dict[str, Any] = {}
    local_file = paths.local_config_file()
    if use_local and local_file.exists():
        local = _read_toml(local_file)
    chosen_profile = profile or os.environ.get("SLIPWAY_PROFILE") or local.get("profile")
    if chosen_profile:
        prof_file = find_profile(root, chosen_profile)
        if not prof_file:
            known = ", ".join(list_profiles(root)) or "none"
            raise ManifestError(f"profile '{chosen_profile}' not found; known: {known} (slipway profile new <name>)")
        overlays.append(_read_toml(prof_file))
    if local:
        overlays.append(local)

    packs = list(data.get("settings", {}).get("default_packs", []))
    for over in overlays:
        data = _deep_merge(data, {k: v for k, v in over.items() if k not in ("enable_packs", "disable_packs")})
        packs += [p for p in over.get("enable_packs", []) if p not in packs]
        packs = [p for p in packs if p not in over.get("disable_packs", [])]
    return _build(root, data, chosen_profile, packs)


def _build(root: Path, data: dict[str, Any], profile: str | None, default_packs: list[str]) -> Manifest:
    if data.get("version") != 1:
        raise ManifestError("slipway.toml: `version = 1` is required")
    packs = data.get("packs", {})
    components: list[Component] = []
    seen: set[str] = set()
    for raw in data.get("component", []):
        cid = raw.get("id")
        if not cid:
            raise ManifestError(f"component without id: {raw}")
        if cid in seen:
            raise ManifestError(f"duplicate component id: {cid}")
        seen.add(cid)
        kind = raw.get("kind")
        if kind not in KIND_FIELDS:
            raise ManifestError(f"{cid}: unknown kind '{kind}'; known: {', '.join(KIND_FIELDS)}")
        if raw.get("pack") not in packs:
            raise ManifestError(f"{cid}: pack '{raw.get('pack')}' is not declared under [packs]")
        missing = [f for f in KIND_FIELDS[kind] if not raw.get(f)]
        if missing:
            raise ManifestError(f"{cid}: kind '{kind}' needs {', '.join(missing)}")
        unknown = set(raw) - set(Component.__dataclass_fields__)
        if unknown:
            raise ManifestError(f"{cid}: unknown field(s) {', '.join(sorted(unknown))}")
        components.append(Component(**raw))

    roles: dict[str, Role] = {}
    for name, raw in data.get("roles", {}).items():
        if raw.get("harness") not in HARNESSES:
            raise ManifestError(f"roles.{name}: harness must be one of {', '.join(HARNESSES)}")
        if not raw.get("model"):
            raise ManifestError(f"roles.{name}: model is required")
        roles[name] = Role(name=name, **raw)

    unknown_packs = [p for p in default_packs if p not in packs]
    if unknown_packs:
        raise ManifestError(f"default/enabled packs not declared: {', '.join(unknown_packs)}")
    return Manifest(
        root=root,
        settings=data.get("settings", {}),
        packs=packs,
        components=components,
        roles=roles,
        omp=data.get("omp", {}),
        project=data.get("project", {}),
        profile=profile,
        default_packs=default_packs,
    )
