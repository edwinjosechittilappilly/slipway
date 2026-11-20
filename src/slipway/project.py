"""`slipway init`: wire a repository for the delivery flow (Beads, OpenSpec, docs the engineering skills read)."""

from __future__ import annotations

import shutil
from pathlib import Path

from slipway import blocks, ui
from slipway.manifest import Manifest
from slipway.shell import Runner, StepError

OPENSPEC_TOOL_IDS = {
    "omp": "oh-my-pi",
    "claude": "claude",
    "codex": "codex",
    "gemini": "gemini",
    "cursor-agent": "cursor",
    "opencode": "opencode",
}


def detected_openspec_tools(runner: Runner) -> list[str]:
    return [tool for binary, tool in OPENSPEC_TOOL_IDS.items() if runner.which(binary)]


def init(
    manifest: Manifest,
    target: Path,
    runner: Runner,
    *,
    stealth: bool = False,
    beads: bool = True,
    openspec: bool = True,
    tools: list[str] | None = None,
    force: bool = False,
) -> int:
    target = target.resolve()
    if not target.is_dir():
        ui.line(f"✘ {target} is not a directory", "err")
        return 1
    settings = manifest.project
    failures: list[str] = []
    dry = runner.dry_run
    ui.heading(f"Slipway project setup: {target}")
    if not runner.run(["git", "-C", str(target), "rev-parse", "--git-dir"], mutate=False, check=False).ok:
        ui.status("drift", "git", "not a git repository; Beads sync and PR flow need one (git init)")

    if beads:
        if (target / ".beads").exists():
            ui.status("ok", "beads", "already initialised")
        elif not runner.which("bd"):
            ui.status("missing", "beads", "bd not installed (slipway install --packs tasks)")
            failures.append("beads")
        else:
            argv = ["bd", "init", "--non-interactive", "--skip-agents", "-q"]
            if stealth or settings.get("beads_stealth"):
                argv.append("--stealth")
            try:
                runner.run(argv, cwd=str(target))
                ui.status("ok", "beads", "initialised (.beads/)" + (" in stealth mode" if "--stealth" in argv else ""))
                if not settings.get("beads_metrics", False):
                    runner.run(["bd", "metrics", "off"], cwd=str(target), check=False)
            except StepError as exc:
                ui.status("error", "beads", str(exc))
                failures.append("beads")

    if openspec:
        if not runner.which("openspec"):
            ui.status("missing", "openspec", "not installed (slipway install --packs spec)")
            failures.append("openspec")
        else:
            chosen = tools or detected_openspec_tools(runner) or ["agents"]
            scope = settings.get("openspec_scope", "global")
            if (target / "openspec").exists():
                argv = ["openspec", "update"]
                label = "updated skills for this machine"
            else:
                argv = ["openspec", "init", "--tools", ",".join(chosen), "--scope", scope, "--no-animation"]
                label = f"initialised (openspec/, tools: {', '.join(chosen)}, skills scope: {scope})"
            try:
                runner.run(argv, cwd=str(target))
                ui.status("ok", "openspec", label)
            except StepError as exc:
                ui.status("error", "openspec", str(exc))
                failures.append("openspec")

    templates = manifest.root / "templates" / "project"
    for src in sorted(templates.rglob("*")):
        rel = src.relative_to(templates)
        if src.is_dir() or rel.name.endswith(".block.md"):
            continue
        dest = target / rel
        if dest.exists():
            ui.status("ok", str(rel), "kept (exists)")
            continue
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        ui.status("ok", str(rel), "would create" if dry else "created")

    for label, action in refresh_blocks(manifest, target, force=force, dry_run=dry).items():
        ui.status("drift" if action == "edited" else "ok", label, _block_text(action))

    ui.heading("Next")
    ui.line("  slipway ui                     open the Beads board (beads-ui) for this repo")
    ui.line("  /ship-flow                     in your agent: walks idea → one-pager → design → spec → beads → PR")
    ui.line("  /setup-matt-pocock-skills      optional: review docs/agents/*.md (pre-filled for Beads)")
    return 1 if failures else 0


def agents_block(manifest: Manifest) -> str:
    return (manifest.root / "templates" / "project" / "AGENTS.block.md").read_text(encoding="utf-8")


def refresh_blocks(manifest: Manifest, target: Path, force: bool = False, dry_run: bool = False) -> dict[str, str]:
    """Write or update the managed AGENTS.md block and the CLAUDE.md import. Edited blocks are kept unless forced."""
    block = agents_block(manifest)
    out = {
        "AGENTS.md": blocks.upsert(target / "AGENTS.md", "slipway-project", block, force=force, dry_run=dry_run).action
    }
    claude_md = target / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    if "@AGENTS.md" in text and "slipway:begin slipway-import" not in text:
        out["CLAUDE.md"] = "imports"  # the user already imports AGENTS.md their own way
    else:
        out["CLAUDE.md"] = blocks.upsert(claude_md, "slipway-import", "@AGENTS.md", force=force, dry_run=dry_run).action
    return out


def _block_text(action: str) -> str:
    return {
        "created": "added Slipway block",
        "updated": "updated Slipway block",
        "unchanged": "Slipway block up to date",
        "edited": "your edits kept (use --force to replace)",
        "imports": "already imports AGENTS.md",
    }.get(action, action)
