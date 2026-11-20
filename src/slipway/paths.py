"""Filesystem locations. Every function reads the environment at call time so tests can swap HOME."""

from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())


def repo_root() -> Path:
    """The Slipway checkout: $SLIPWAY_HOME, else the repo this package was installed from (editable install)."""
    env = os.environ.get("SLIPWAY_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _xdg(var: str, default: str) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else home() / default


def state_file() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "slipway" / "state.json"


def local_config_file() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "slipway" / "config.toml"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "slipway"


def agents_skills_dir() -> Path:
    """Shared skill folder read by omp, Codex and Pi; `npx skills -a pi` writes here."""
    return home() / ".agents" / "skills"


def skill_lock_file() -> Path:
    """Global lock written by `npx skills` (vercel-labs/skills)."""
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg) / "skills" / ".skill-lock.json"
    return home() / ".agents" / ".skill-lock.json"


def claude_dir() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else home() / ".claude"


def codex_dir() -> Path:
    env = os.environ.get("CODEX_HOME")
    return Path(env).expanduser() if env else home() / ".codex"


def gemini_dir() -> Path:
    return home() / ".gemini"


def omp_agent_dir() -> Path:
    """Active omp agent dir, honouring OMP_PROFILE / PI_CODING_AGENT_DIR like omp does."""
    profile = os.environ.get("OMP_PROFILE", os.environ.get("PI_PROFILE", "")).strip()
    if profile and profile != "default":
        return home() / ".omp" / "profiles" / profile / "agent"
    env = os.environ.get("PI_CODING_AGENT_DIR")
    if env:
        return Path(env).expanduser()
    return home() / ".omp" / "agent"


TARGET_DIRS = {
    "agents-skills": agents_skills_dir,
    "claude-skills": lambda: claude_dir() / "skills",
    "claude-agents": lambda: claude_dir() / "agents",
    "omp-agents": lambda: omp_agent_dir() / "agents",
    "omp-skills": lambda: omp_agent_dir() / "skills",
}

INSTRUCTION_FILES = {
    "omp": lambda: omp_agent_dir() / "AGENTS.md",
    "claude": lambda: claude_dir() / "CLAUDE.md",
    "codex": lambda: codex_dir() / "AGENTS.md",
    "gemini": lambda: gemini_dir() / "GEMINI.md",
}


def contract(path: Path) -> str:
    """Show a path with ~ for the home directory."""
    try:
        return "~/" + str(path.relative_to(home()))
    except ValueError:
        return str(path)
