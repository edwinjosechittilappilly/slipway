"""Role -> harness -> model routing, and `slipway run` to launch a harness for a role or a Beads issue."""

from __future__ import annotations

import json
import os

from slipway import ui
from slipway.manifest import Manifest, ManifestError, Role
from slipway.shell import Runner

THINKING = {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto", "inherit"}
# omp's built-in chat roles: `--model @<role>` works even before you assign them (they fall back to the default model).
BUILTIN_ROLES = {"default", "smol", "slow", "vision", "plan", "commit", "tiny", "memory", "task", "advisor"}


def omp_roles(runner: Runner) -> dict[str, str]:
    if not runner.which("omp"):
        return {}
    res = runner.run(["omp", "config", "get", "modelRoles", "--json"], mutate=False, check=False)
    try:
        return json.loads(res.out).get("value") or {}
    except ValueError:
        return {}


def resolve(model: str, roles: dict[str, str]) -> str:
    """`@scout` -> the omp role's selector (first candidate). Other values pass through."""
    seen = set()
    while model.startswith("@") and model not in seen:
        seen.add(model)
        target = roles.get(model[1:])
        if not target:
            return model
        model = target.split(",")[0].strip()
    return model


def split_thinking(selector: str) -> tuple[str, str | None]:
    head, _, tail = selector.rpartition(":")
    if head and tail in THINKING:
        return head, tail
    return selector, None


def command(harness: str, model: str, prompt: str | None, print_mode: bool) -> list[str]:
    """argv for a harness.

    omp gets `@role` aliases as-is (`--model @review`): omp resolves them itself, keeping the role's thinking level
    and fallback chain. Other harnesses do not know omp aliases, so an alias, "" or "default" means their default.
    """
    p = [prompt] if prompt else []
    if harness == "omp" and model.startswith("@"):
        return ["omp", "--model", model, *(["-p"] if print_mode else []), *p]
    model, thinking = split_thinking(model)
    use_default = model in ("", "default") or model.startswith("@")
    m = [] if use_default else [model]
    if harness == "omp":
        flags = (["--model", *m] if m else []) + (["--thinking", thinking] if thinking else [])
        return ["omp", *flags, *(["-p"] if print_mode else []), *p]
    if harness == "claude":
        return ["claude", *(["--model", *m] if m else []), *(["-p"] if print_mode else []), *p]
    if harness == "codex":
        flags = ["-m", *m] if m else []
        return ["codex", "exec", *flags, *p] if print_mode else ["codex", *flags, *p]
    if harness == "gemini":
        prompt_flags = (["-p", prompt] if print_mode else ["-i", prompt]) if prompt else []
        return ["gemini", *(["-m", *m] if m else []), *prompt_flags]
    if harness == "cursor-agent":
        return ["cursor-agent", *(["--model", *m] if m else []), *(["-p"] if print_mode else []), *p]
    if harness == "opencode":
        flags = ["-m", *m] if m else []
        return ["opencode", "run", *flags, *p] if print_mode else ["opencode", *(["--model", *m] if m else []), *p]
    raise ManifestError(f"unknown harness {harness}")


def plan(manifest: Manifest, role_name: str, runner: Runner, harness: str | None = None) -> tuple[Role, str, str]:
    role = manifest.roles.get(role_name)
    if not role:
        raise ManifestError(f"unknown role '{role_name}'; known: {', '.join(manifest.roles)}")
    chosen = harness or role.harness
    # A harness without a mapped model runs with its own configured default.
    model = role.model if chosen == role.harness else role.alt.get(chosen, "default")
    return role, chosen, model


def describe(model: str, aliases: dict[str, str]) -> str:
    """What an omp alias currently points at, for display."""
    if not model.startswith("@"):
        return ""
    resolved = resolve(model, aliases)
    if not resolved.startswith("@"):
        return resolved
    return "omp default model (role not assigned)" if model[1:] in BUILTIN_ROLES else "undefined omp role"


def show(manifest: Manifest, runner: Runner) -> None:
    aliases = omp_roles(runner)
    rows = []
    for role in manifest.roles.values():
        target = describe(role.model, aliases) if role.harness == "omp" else ""
        ok = "yes" if runner.which(role.harness) else "not installed"
        if target == "undefined omp role":
            ok = f"define {role.model} in omp (/model → Roles)"
        alt = ", ".join(f"{h}:{m}" for h, m in role.alt.items())
        rows.append([role.name, role.harness, role.model, target, ok, alt])
    ui.table(rows, ["role", "harness", "model", "resolves to", "ready", "also on"])
    ui.line()
    ui.line("  slipway run <role> [prompt]      launch the harness for a role", "dim")
    ui.line("  slipway run --bead <id>          hand a Beads issue to the harness its role:<name> label picks", "dim")


def bead_prompt(runner: Runner, bead_id: str, claim: bool) -> tuple[str, str]:
    """Return (role, prompt) for a Beads issue; claims it atomically unless claim=False."""
    res = runner.run(["bd", "show", bead_id, "--json"], mutate=False)
    data = json.loads(res.out)
    issue = data[0] if isinstance(data, list) else data
    labels = issue.get("labels") or []
    role = next((label.split(":", 1)[1] for label in labels if label.startswith("role:")), "implement")
    if claim:
        runner.run(["bd", "update", bead_id, "--claim"])
    parts = [
        f"Work on Beads issue {bead_id}: {issue.get('title', '')} (role: {role}).",
        "",
        issue.get("description") or "(no description)",
    ]
    for key, label in (("acceptance_criteria", "Acceptance"), ("design", "Design notes"), ("spec_id", "Spec")):
        if issue.get(key):
            parts += ["", f"{label}: {issue[key]}"]
    if issue.get("parent"):
        parts += ["", f"Parent: {issue['parent']} (run `bd show {issue['parent']}` for context)"]
    parts += [
        "",
        "Run `bd prime` first. Follow AGENTS.md. Keep the change to this issue's scope.",
        f'When done: verify, then `bd close {bead_id} --reason "<one line>"`. If blocked: '
        f'`bd note {bead_id} "<what blocks you>"` and stop.',
    ]
    return role, "\n".join(parts)


def run(
    manifest: Manifest,
    runner: Runner,
    role_name: str | None,
    prompt: str | None,
    harness: str | None = None,
    bead: str | None = None,
    print_mode: bool = False,
    claim: bool = True,
) -> int:
    if bead:
        role_from_bead, prompt = bead_prompt(runner, bead, claim and not runner.dry_run)
        role_name = role_name or role_from_bead
    if not role_name:
        raise ManifestError("give a role (slipway run implement) or --bead <id>")
    role, chosen, model = plan(manifest, role_name, runner, harness)
    argv = command(chosen, model, prompt, print_mode)
    if not runner.which(argv[0]):
        raise ManifestError(f"{argv[0]} is not installed (slipway install --packs harnesses)")
    target = describe(model, omp_roles(runner)) if chosen == "omp" else ""
    ui.line(f"→ {role.name} on {chosen} with {model}" + (f" ({target})" if target else ""), "info")
    if runner.dry_run:
        ui.line("  would run: " + " ".join(a if " " not in a else repr(a) for a in argv), "dim")
        return 0
    os.execvp(argv[0], argv)
    return 0  # unreachable
