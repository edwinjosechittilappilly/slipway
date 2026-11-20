"""slipway: install, update and inspect your agentic development environment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slipway import (
    __version__,
    backup,
    doctor,
    kinds,
    links,
    lockfile,
    manifest,
    paths,
    profiles,
    project,
    roles,
    ui,
)
from slipway.kinds import Ctx
from slipway.manifest import ManifestError
from slipway.shell import Runner, StepError
from slipway.state import State, now

# (component id, probe that succeeds when logged in or None, hint). Hints without a probe show only right after
# Slipway installs that harness, so returning users are not nagged.
LOGINS = [
    ("gh", ["gh", "auth", "status"], "gh auth login"),
    ("omp", None, "omp  →  /login  (then /model → Roles to check routing)"),
    ("claude", None, "claude  →  log in once"),
    ("codex", None, "codex login"),
]


def _context(args: argparse.Namespace, upgrade_latest: bool = False) -> Ctx:
    m = manifest.load(profile=getattr(args, "profile", None))
    runner = Runner(dry_run=getattr(args, "dry_run", False), verbose=getattr(args, "verbose", False))
    return Ctx(m, lockfile.load(m), State.load(), runner, force=getattr(args, "force", False), latest=upgrade_latest)


def _packs(args: argparse.Namespace) -> list[str] | None:
    return [p.strip() for p in args.packs.split(",") if p.strip()] if getattr(args, "packs", None) else None


def _apply_all(ctx: Ctx, args: argparse.Namespace, upgrade: bool) -> int:
    comps = ctx.manifest.select(_packs(args), args.all)
    failures: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    current = None
    installed_now: set[str] = set()
    if not ctx.runner.dry_run:
        saved = backup.snapshot()
        if saved:
            ui.line(f"  backed up your agent config to {paths.contract(saved)}", "dim")
    for comp in comps:
        if comp.pack != current:
            current = comp.pack
            ui.heading(f"{current}: {ctx.manifest.packs[current].get('description', '')}")
        try:
            changes = kinds.apply(comp, ctx, upgrade=upgrade, prune=args.prune)
        except kinds.Skipped as exc:
            skipped.append((comp.id, str(exc)))
            ui.status("skipped", comp.id, str(exc))
            continue
        except StepError as exc:
            failures.append((comp.id, exc.command))
            ui.status("error", comp.id, str(exc))
            continue
        if any(c.startswith("installed") for c in changes):
            installed_now.add(comp.id)
        ui.status("ok", comp.id, "; ".join(changes) if changes else "up to date")
    if not _packs(args) and not args.all:
        for res in links.prune(ctx.state, {c.id for c in ctx.manifest.components}, dry_run=ctx.runner.dry_run):
            ui.status("ok", "prune", f"{res.action} {paths.contract(res.link)}")
    if not ctx.runner.dry_run:
        ctx.state.save()

    ui.heading("summary")
    ui.line(
        f"  {len(comps) - len(failures) - len(skipped)} ok · {len(skipped)} skipped · {len(failures)} failed"
        + ("  (dry run: nothing changed)" if ctx.runner.dry_run else "")
    )
    for cid, command in failures:
        ui.line(f"  ✘ {cid}: retry with  {command}", "err")
    needs = [
        hint
        for cid, probe, hint in LOGINS
        if ctx.runner.which(cid)
        and (cid in installed_now if probe is None else not ctx.runner.run(probe, mutate=False, check=False).ok)
    ]
    if needs and not ctx.runner.dry_run:
        ui.heading("one-time logins (skip any you have done)")
        for hint in needs:
            ui.line(f"  {hint}")
    ui.line()
    ui.line("  next: slipway doctor  ·  cd <repo> && slipway init  ·  slipway roles", "dim")
    return 1 if failures else 0


def cmd_install(args: argparse.Namespace) -> int:
    code = _apply_all(_context(args), args, upgrade=False)
    if args.profile and not args.dry_run and manifest.remember_profile(args.profile):
        ui.line(f"  remembered profile '{args.profile}' in {paths.contract(paths.local_config_file())}", "dim")
    return code


def cmd_update(args: argparse.Namespace) -> int:
    root = paths.repo_root()
    runner = Runner(dry_run=args.dry_run)
    if not args.no_pull and (root / ".git").exists():
        # Untracked files (notes, scratch) never block a pull; edits to tracked files do.
        status = ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"]
        if runner.run(status, mutate=False, check=False).out.strip():
            ui.line(
                f"! {paths.contract(root)} has local edits; skipping git pull (commit them or use --no-pull)", "warn"
            )
        else:
            try:
                runner.run(["git", "-C", str(root), "pull", "--ff-only", "--quiet"])
            except StepError as exc:
                ui.line(f"! git pull failed, continuing with the current checkout: {exc}", "warn")
    ctx = _context(args, upgrade_latest=args.latest)
    code = _apply_all(ctx, args, upgrade=True)
    _refresh_projects(ctx)
    return code


def _refresh_projects(ctx: Ctx) -> None:
    """Carry rule changes into every repo `slipway init` set up (managed blocks only; your files stay yours)."""
    projects = ctx.state.section("projects")
    if not projects:
        return
    ui.heading("projects")
    for path_str in sorted(projects):
        target = Path(path_str)
        if not (target / "AGENTS.md").exists():
            ui.status("skipped", paths.contract(target), "no AGENTS.md (moved or deleted?)")
            continue
        actions = project.refresh_blocks(ctx.manifest, target, force=ctx.force, dry_run=ctx.runner.dry_run)
        changed = {k: v for k, v in actions.items() if v not in ("unchanged", "imports")}
        state = "drift" if "edited" in changed.values() else "ok"
        ui.status(state, paths.contract(target), ", ".join(f"{k} {v}" for k, v in changed.items()) or "up to date")


def cmd_doctor(args: argparse.Namespace) -> int:
    ctx = _context(args)
    results = doctor.collect(ctx, ctx.manifest.select(_packs(args), args.all))
    if args.markdown:
        sys.stdout.write(doctor.markdown(ctx, results))
        return 0
    checks = doctor.environment_checks(ctx)
    if args.json:
        sys.stdout.write(doctor.as_json(results, checks) + "\n")
        return 0
    return doctor.print_report(ctx, results, checks)


def cmd_packs(args: argparse.Namespace) -> int:
    m = manifest.load(profile=args.profile)
    rows = []
    for name, pack in m.packs.items():
        comps = [c.id for c in m.components if c.pack == name]
        rows.append([name, "yes" if name in m.default_packs else "", str(len(comps)), pack.get("description", "")])
    ui.table(rows, ["pack", "default", "items", "what it gives you"])
    ui.line()
    ui.line("  slipway install --packs a,b   ·   enable_packs = [..] in ~/.config/slipway/config.toml", "dim")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    m = manifest.load(profile=args.profile)
    runner = Runner(dry_run=args.dry_run)
    tools = [t for t in args.tools.split(",") if t] if args.tools else None
    target = Path(args.path).resolve()
    code = project.init(
        m,
        target,
        runner,
        stealth=args.stealth,
        beads=not args.no_beads,
        openspec=not args.no_openspec,
        tools=tools,
        force=args.force,
    )
    if not args.dry_run and target.is_dir():
        st = State.load()
        st.section("projects")[str(target)] = {"at": now()}
        st.save()
    return code


def cmd_profile(args: argparse.Namespace) -> int:
    root = paths.repo_root()
    dest = paths.local_config_file().parent / "profiles" / f"{args.name}.toml"
    if dest.exists() and not args.force:
        ui.line(f"✘ {paths.contract(dest)} exists (edit it, or --force to overwrite)", "err")
        return 1
    if args.copy:
        src = manifest.find_profile(root, args.copy)
        if not src:
            raise ManifestError(f"profile '{args.copy}' not found; known: {', '.join(manifest.list_profiles(root))}")
        text = f"# Copied from {args.copy}. Edit freely; this file lives outside the Slipway checkout.\n\n"
        text += src.read_text(encoding="utf-8")
    else:
        text = profiles.from_current_setup(Runner())
    if args.dry_run:
        sys.stdout.write(text)
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    manifest.remember_profile(args.name)
    ui.line(f"✔ wrote {paths.contract(dest)} and made it your profile", "ok")
    ui.line("  review it, then: slipway install --dry-run  ·  slipway install", "dim")
    return 0


def cmd_roles(args: argparse.Namespace) -> int:
    roles.show(manifest.load(profile=args.profile), Runner())
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    m = manifest.load(profile=args.profile)
    prompt = " ".join(args.prompt) if args.prompt else None
    role = args.role
    if role and role not in m.roles and not args.bead:
        raise ManifestError(f"unknown role '{role}'; known: {', '.join(m.roles)}")
    return roles.run(
        m,
        Runner(dry_run=args.dry_run),
        role,
        prompt,
        harness=args.harness,
        bead=args.bead,
        print_mode=args.print,
        claim=not args.no_claim,
    )


def cmd_ui(args: argparse.Namespace) -> int:
    runner = Runner()
    if not runner.which("bdui"):
        ui.line("beads-ui is not installed: slipway install --packs tasks", "err")
        return 1
    import os

    os.chdir(args.path)
    os.execvp("bdui", ["bdui", "start", "--open"])
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    m = manifest.load(profile=args.profile, use_local=False)
    if not args.refresh:
        data = lockfile.load(m)
        rows = [[s, v.get("commit", "")[:12]] for s, v in sorted(data["skills"].items())]
        rows += [[f"npm {k}", v] for k, v in sorted(data["npm"].items())]
        rows += [[f"brew {k}", v] for k, v in sorted(data["brew"].items())]
        ui.table(rows, ["source", "pin"])
        return 0
    new, changes, errors = lockfile.refresh(m, Runner(), only=args.only)
    if not args.dry_run:
        lockfile.save(m, new)
    body = lockfile.changes_markdown(changes, errors)
    if args.markdown:
        Path(args.markdown).write_text(body, encoding="utf-8")
    sys.stdout.write(body)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    ctx = _context(args)
    for comp in ctx.manifest.components:
        try:
            for change in kinds.remove(comp, ctx):
                ui.status("ok", comp.id, change)
        except StepError as exc:
            ui.status("error", comp.id, f"left in place: {exc}")
    for res in links.prune(ctx.state, set(), dry_run=ctx.runner.dry_run):
        ui.status("ok", "links", f"{res.action} {paths.contract(res.link)}")
    if not ctx.runner.dry_run:
        ctx.state.save()
    ui.line()
    ui.line("  Remove the CLI itself with: uv tool uninstall slipway", "dim")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slipway", description=__doc__)
    parser.add_argument("--version", action="version", version=f"slipway {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, packs: bool = True, mutate: bool = True) -> None:
        p.add_argument("--profile", help="profile overlay from profiles/<name>.toml (or SLIPWAY_PROFILE)")
        if packs:
            p.add_argument("--packs", help="comma-separated packs (default: the profile's default packs)")
            p.add_argument("--all", action="store_true", help="every pack")
        if mutate:
            p.add_argument("--dry-run", action="store_true", help="show what would change; change nothing")
            p.add_argument("--force", action="store_true", help="overwrite values and files you changed")
            p.add_argument("-v", "--verbose", action="store_true")

    p = sub.add_parser("install", help="install everything in the selected packs (idempotent)")
    common(p)
    p.add_argument("--prune", action="store_true", help="also remove skills this manifest no longer lists")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("update", help="git pull this repo, then move every component to the lock")
    common(p)
    p.add_argument("--latest", action="store_true", help="ignore the lock and take upstream latest")
    p.add_argument("--no-pull", action="store_true", help="do not git pull the Slipway checkout")
    p.add_argument("--prune", action="store_true", help="remove skills this manifest no longer lists")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("doctor", help="show what is installed, outdated, drifted, or needs a login")
    common(p, mutate=False)
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true", help="shareable summary (no paths or secrets)")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("packs", help="list packs and what each one installs")
    common(p, packs=False, mutate=False)
    p.set_defaults(func=cmd_packs)

    p = sub.add_parser("init", help="set up a repo: Beads, OpenSpec, docs/agents, AGENTS.md block")
    common(p, packs=False)
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--stealth", action="store_true", help="keep Beads files out of git (bd init --stealth)")
    p.add_argument("--tools", help="OpenSpec tool ids (default: detected harnesses)")
    p.add_argument("--no-beads", action="store_true")
    p.add_argument("--no-openspec", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("profile", help="create your own profile in ~/.config/slipway/profiles")
    psub = p.add_subparsers(dest="profile_action", required=True)
    new = psub.add_parser("new", help="write a profile from your current omp setup (or --copy a shipped one)")
    new.add_argument("name")
    new.add_argument("--copy", metavar="PROFILE", help="start from a shipped profile (edwin, claude-code, codex)")
    new.add_argument("--force", action="store_true", help="overwrite an existing profile of that name")
    new.add_argument("--dry-run", action="store_true", help="print the profile instead of writing it")
    new.set_defaults(func=cmd_profile)

    p = sub.add_parser("roles", help="show the role → harness → model matrix")
    common(p, packs=False, mutate=False)
    p.set_defaults(func=cmd_roles)

    p = sub.add_parser("run", help="launch the harness mapped to a role, or hand it a Beads issue")
    common(p, packs=False, mutate=False)
    p.add_argument("role", nargs="?")
    p.add_argument("prompt", nargs="*")
    p.add_argument("--bead", help="Beads issue id; role comes from its role:<name> label")
    p.add_argument("--harness", help="override the role's harness (uses roles.<role>.alt)")
    p.add_argument("--print", action="store_true", help="non-interactive (omp -p, claude -p, codex exec)")
    p.add_argument("--no-claim", action="store_true", help="do not bd update --claim the issue")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("ui", help="open the Beads board (beads-ui) for a repo")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_ui)

    p = sub.add_parser("lock", help="show pins, or --refresh them from upstream")
    common(p, packs=False, mutate=False)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--only", choices=["skills", "npm", "brew"])
    p.add_argument("--dry-run", action="store_true", help="with --refresh: report, do not write the lock")
    p.add_argument("--markdown", help="with --refresh: also write the PR body to this file")
    p.set_defaults(func=cmd_lock)

    p = sub.add_parser("uninstall", help="remove links, managed blocks and omp entries Slipway wrote")
    common(p, packs=False)
    p.set_defaults(func=cmd_uninstall)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ManifestError as exc:
        ui.line(f"✘ {exc}", "err")
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
