"""`slipway doctor`: what is installed, what drifted, and what needs a human (logins, keys)."""

from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path

from slipway import __version__, blocks, kinds, paths, project, roles, ui
from slipway.kinds import Ctx, Status
from slipway.manifest import Component

AGENT_MODEL = re.compile(r"^model:\s*(.+)$", re.MULTILINE)


@dataclass
class Check:
    state: str
    label: str
    detail: str
    fix: str = ""


def collect(ctx: Ctx, comps: list[Component]) -> list[tuple[Component, Status]]:
    return [(c, kinds.status(c, ctx)) for c in comps]


def environment_checks(ctx: Ctx) -> list[Check]:
    run, which = ctx.runner.run, ctx.runner.which
    checks: list[Check] = []

    node = run(["node", "--version"], mutate=False, check=False) if which("node") else None
    major = int(re.sub(r"\D", "", node.out.split(".")[0]) or 0) if node and node.ok else 0
    checks.append(
        Check(
            "ok" if major >= 22 else "missing",
            "node >= 22",
            node.out.strip() if node else "not found",
            "brew install node  (skills CLI, OpenSpec and beads-ui need Node 22+)",
        )
    )
    if which("gh"):
        auth = run(["gh", "auth", "status"], mutate=False, check=False)
        checks.append(
            Check(
                "ok" if auth.ok else "missing", "gh auth", "logged in" if auth.ok else "not logged in", "gh auth login"
            )
        )
    if which("omp"):
        has_key = (
            bool(os.environ.get("TYPESAFE_API_KEY")) or run(["omp", "token", "typesafe"], mutate=False, check=False).ok
        )
        checks.append(
            Check(
                "ok" if has_key else "drift",
                "Jev judge (TypeSafe)",
                "credential found"
                if has_key
                else "no TypeSafe credential: omp `find`, judged rules, auto-thinking "
                "and prewalk fall back or stay off",
                "export TYPESAFE_API_KEY=… (https://typesafe.ai) and restart omp",
            )
        )
        aliases = roles.omp_roles(ctx.runner)
        undefined = sorted(_undefined_aliases(ctx, aliases))
        checks.append(
            Check(
                "drift" if undefined else "ok",
                "omp role aliases",
                f"undefined: {', '.join(undefined)}" if undefined else f"{len(aliases)} roles defined",
                "define them under [omp.modelRoles] in your profile, or /model → Roles in omp",
            )
        )
    broken = [
        paths.contract(p)
        for root in (paths.agents_skills_dir(), paths.claude_dir() / "skills")
        if root.exists()
        for p in root.iterdir()
        if p.is_symlink() and not p.exists()
    ]
    checks.append(
        Check(
            "drift" if broken else "ok",
            "skill symlinks",
            f"broken: {', '.join(broken)}" if broken else "no broken links",
            "slipway update --prune, or delete the broken links",
        )
    )
    projects = [Path(p) for p in ctx.state.section("projects") if Path(p).is_dir()]
    if projects:
        block = project.agents_block(ctx.manifest)
        behind = [
            paths.contract(p)
            for p in projects
            if (p / "AGENTS.md").exists() and blocks.inspect(p / "AGENTS.md", "slipway-project", block) == "updated"
        ]
        checks.append(
            Check(
                "drift" if behind else "ok",
                "project repos",
                f"older Slipway block in {', '.join(behind)}" if behind else f"{len(projects)} up to date",
                "slipway update    (refreshes the managed block in each repo)",
            )
        )
    return checks


def _undefined_aliases(ctx: Ctx, aliases: dict[str, str]) -> set[str]:
    used: set[str] = set()
    for role in ctx.manifest.roles.values():
        if role.harness == "omp" and role.model.startswith("@"):
            used.add(role.model[1:])
    for value in ctx.manifest.omp.get("task.agentModelOverrides", {}).values():
        if isinstance(value, str) and value.startswith("@"):
            used.add(value[1:])
    for agent in (ctx.manifest.root / "agents" / "omp").glob("*.md"):
        match = AGENT_MODEL.search(agent.read_text(encoding="utf-8"))
        if match:
            used |= {m.strip().strip("\"'-[] ")[1:] for m in match.group(1).split(",") if "@" in m}
    planned = set(ctx.manifest.omp.get("modelRoles", {}))
    return {u for u in used if u and u not in aliases and u not in planned and u not in roles.BUILTIN_ROLES}


def print_report(ctx: Ctx, results: list[tuple[Component, Status]], checks: list[Check]) -> int:
    ui.heading(
        f"Slipway {__version__} · profile {ctx.manifest.profile or 'default'} · {paths.contract(ctx.manifest.root)}"
    )
    current = None
    for comp, st in results:
        if comp.pack != current:
            current = comp.pack
            ui.heading(f"{current}: {ctx.manifest.packs[current].get('description', '')}")
        ui.status(st.state, comp.id, st.detail)
    ui.heading("environment")
    for check in checks:
        ui.status(check.state, check.label, check.detail)
    todo = [c for c in checks if c.state != "ok" and c.fix]
    missing = [c for c, st in results if st.state in ("missing", "outdated")]
    stale = sorted({name for _c, st in results for name in st.stale})
    leftover = sorted({name for _c, st in results for name in st.leftover})
    if missing or todo or stale or leftover:
        ui.heading("fix")
        if missing:
            ui.line(
                f"  slipway {'install' if any(r[1].state == 'missing' for r in results) else 'update'}"
                "    # installs/updates: " + ", ".join(c.id for c in missing)
            )
        if stale:
            ui.line(
                "  slipway update --prune    # removes skills Slipway installed that you dropped: " + ", ".join(stale)
            )
        if leftover:
            ui.line(
                f"  npx skills remove {' '.join(leftover)} -g -y"
                "    # older installs, renamed or dropped upstream; Slipway never removes these itself"
            )
        for check in todo:
            ui.line(f"  {check.fix}    # {check.label}")
    return 1 if any(st.state == "missing" for _c, st in results) else 0


def markdown(ctx: Ctx, results: list[tuple[Component, Status]]) -> str:
    """Shareable summary: no paths, no secrets."""
    lines = [
        f"### My agentic dev environment (Slipway {__version__})",
        "",
        f"Platform: {platform.system()} {platform.machine()} · profile: `{ctx.manifest.profile or 'default'}`",
        "",
        "| Pack | Component | Status | Version |",
        "|---|---|---|---|",
    ]
    for comp, st in results:
        lines.append(f"| {comp.pack} | {comp.id} | {st.state} | {st.version or ''} |")
    skills = sum(len(c.skills) for c, _ in results if c.kind == "skills")
    lines += [
        "",
        f"{skills} pinned upstream skills · {len(ctx.manifest.roles)} roles · "
        "built with [Slipway](https://github.com/edwinjosechittilappilly/slipway)",
    ]
    return "\n".join(lines) + "\n"


def as_json(results: list[tuple[Component, Status]], checks: list[Check]) -> str:
    return json.dumps(
        {
            "components": [{"id": c.id, "pack": c.pack, "kind": c.kind, **st.__dict__} for c, st in results],
            "checks": [c.__dict__ for c in checks],
        },
        indent=2,
    )
