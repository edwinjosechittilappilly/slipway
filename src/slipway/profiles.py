"""`slipway profile new`: write a profile from the setup you already have, so adopting Slipway changes nothing."""

from __future__ import annotations

import json
import re
from typing import Any

from slipway.shell import Runner

# omp record settings worth carrying into a profile (all of them are merged with the 3-way rule).
OMP_KEYS = ("modelRoles", "task.agentModelOverrides", "modelPresets", "retry.fallbackChains")
BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _key(key: str) -> str:
    return key if BARE_KEY.match(key) else json.dumps(key)


def _value(value: Any) -> str:
    """TOML value for strings, numbers, booleans, string lists and nested tables (inline)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)  # JSON string escapes are valid TOML basic-string escapes
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_value(v)}" for k, v in value.items()) + " }"
    raise TypeError(f"cannot write {type(value).__name__} to TOML")


def _omp_settings(runner: Runner) -> dict[str, Any]:
    if not runner.which("omp"):
        return {}
    res = runner.run(["omp", "config", "list", "--scope", "global", "--json"], mutate=False, check=False)
    try:
        raw = json.loads(res.out) if res.ok else {}
    except ValueError:
        return {}
    values = {k: v.get("value") if isinstance(v, dict) else v for k, v in raw.items()}
    out = {k: values[k] for k in OMP_KEYS if isinstance(values.get(k), dict) and values[k]}
    if isinstance(values.get("defaultThinkingLevel"), str):
        out["defaultThinkingLevel"] = values["defaultThinkingLevel"]
    return out


def from_current_setup(runner: Runner) -> str:
    """Profile TOML capturing the omp routing you use today (empty template when omp is absent)."""
    settings = _omp_settings(runner)
    lines = [
        "# Your Slipway profile. Lives in ~/.config/slipway/profiles/, outside the checkout, so `slipway update`",
        "# never conflicts with it. It overlays slipway.toml; see docs/configuration.md.",
        "",
        "# Opt-in packs (slipway packs lists them):",
        'enable_packs = []  # e.g. ["shipshape", "jev", "security", "parallel"]',
        "",
        "# Skip single components you do not want, e.g. a harness you never use:",
        "# [[component]]",
        '# id = "codex"',
        "# enabled = false",
        "",
    ]
    if not settings:
        lines += [
            "# No omp config found. Point roles at the harness you use, for example Claude Code:",
            "# [roles.implement]",
            '# harness = "claude"',
            '# model = "sonnet"',
        ]
        return "\n".join(lines) + "\n"
    lines += ["# Captured from your current omp config (`omp config list --scope global`).", "[omp]"]
    scalars = {k: v for k, v in settings.items() if not isinstance(v, dict)}
    lines += [f"{_key(k)} = {_value(v)}" for k, v in scalars.items()]
    for key, record in settings.items():
        if not isinstance(record, dict):
            continue
        lines += ["", f"[omp.{_key(key)}]"]
        lines += [f"{_key(k)} = {_value(v)}" for k, v in record.items()]
    return "\n".join(lines) + "\n"
