"""One handler per component kind: how to check, install/upgrade, and remove it.

Adding a tool is a manifest edit. Adding a kind is a new handler here plus a test.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slipway import blocks, links, paths
from slipway.manifest import Component, Manifest
from slipway.merge import merge_record
from slipway.shell import Result, Runner, StepError
from slipway.state import State, tree_hash

VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?(?:[-+.][0-9A-Za-z.]+)?")

PREREQS = {
    "brew": ["brew"],
    "cask": ["brew"],
    "npm": ["npm"],
    "skills": ["npx", "git"],
    "impeccable": ["npx"],
    "claude-plugin": ["claude"],
    "omp-plugin": ["omp"],
    "omp-config": ["omp"],
}
# Harness -> (binary, config root). A target is written when either exists, so a fresh install that has the binary
# but has not created its config dir yet still gets its skills, agents and rules.
HARNESS_OF_TARGET = {
    "claude-skills": "claude",
    "claude-agents": "claude",
    "omp-agents": "omp",
    "omp-skills": "omp",
}
HARNESS_ROOTS = {
    "omp": ("omp", paths.omp_agent_dir),
    "claude": ("claude", paths.claude_dir),
    "codex": ("codex", paths.codex_dir),
    "gemini": ("gemini", paths.gemini_dir),
}


def harness_present(name: str, runner: Runner) -> bool:
    binary, root = HARNESS_ROOTS[name]
    return bool(runner.which(binary)) or root().exists()


@dataclass
class Status:
    state: str  # ok | missing | outdated | drift | skipped
    detail: str = ""
    version: str | None = None
    stale: list[str] = field(default_factory=list)  # skills Slipway installed that the manifest no longer lists
    leftover: list[str] = field(default_factory=list)  # same source, installed outside Slipway; never auto-removed


@dataclass
class Ctx:
    manifest: Manifest
    lock: dict[str, Any]
    state: State
    runner: Runner
    force: bool = False
    latest: bool = False  # ignore lock pins and take upstream latest
    _omp_global: dict[str, Any] | None = field(default=None, repr=False)

    def omp_global(self) -> dict[str, Any]:
        """Keys the user's global omp config.yml sets (not defaults): `omp config list --scope global --json`.

        Fails closed: if omp cannot report its config, nothing is merged, because treating an unreadable config as
        empty would overwrite every role and preset the user defined.
        """
        if self._omp_global is None:
            cmd = ["omp", "config", "list", "--scope", "global", "--json"]
            res = self.runner.run(cmd, mutate=False, check=False)
            try:
                raw = json.loads(res.out)
            except ValueError:
                raw = None
            if not res.ok or not isinstance(raw, dict):
                raise StepError(" ".join(cmd), Result(res.code or 1, res.out, res.err or "output is not a JSON object"))
            self._omp_global = {k: v.get("value") if isinstance(v, dict) else v for k, v in raw.items()}
        return self._omp_global

    def npm_spec(self, pkg: str) -> str:
        pin = None if self.latest else self.lock.get("npm", {}).get(pkg)
        return f"{pkg}@{pin or 'latest'}"

    def npx(self, pkg: str, *args: str) -> list[str]:
        return ["npx", "-y", self.npm_spec(pkg), *args]

    def skills_pin(self, source: str) -> str | None:
        if self.latest:
            return None
        return self.lock.get("skills", {}).get(source, {}).get("commit")


def missing_prereqs(comp: Component, runner: Runner) -> list[str]:
    return [b for b in PREREQS.get(comp.kind, []) + comp.requires if not runner.which(b)]


def probe_version(runner: Runner, binary: str) -> str | None:
    res = runner.run([binary, "--version"], mutate=False, check=False)
    match = VERSION.search(res.out + res.err) if res.ok else None
    return match.group(0) if match else None


# ---------------------------------------------------------------- status


def status(comp: Component, ctx: Ctx) -> Status:
    missing = missing_prereqs(comp, ctx.runner)
    if missing and comp.kind not in ("brew", "cask", "npm", "script"):
        return Status("skipped", f"needs {', '.join(missing)}")
    return _STATUS[comp.kind](comp, ctx)


def _present(comp: Component, ctx: Ctx) -> bool:
    if comp.check:
        return ctx.runner.run(comp.check, mutate=False, check=False).ok
    return bool(ctx.runner.which(comp.bin or (comp.name or comp.id).split("/")[-1]))


def _npm_owned(comp: Component, ctx: Ctx) -> bool:
    """True when the tool is in npm's global tree (not a standalone or Homebrew install of the same binary)."""
    res = ctx.runner.run(["npm", "ls", "-g", "--depth=0", "--json", comp.name or ""], mutate=False, check=False)
    try:
        return (comp.name or "") in (json.loads(res.out or "{}").get("dependencies") or {})
    except ValueError:
        return False


def _status_package(comp: Component, ctx: Ctx) -> Status:
    if not _present(comp, ctx):
        return Status("missing")
    binary = comp.bin or (comp.name or comp.id).split("/")[-1]
    version = probe_version(ctx.runner, binary) if ctx.runner.which(binary) else None
    pin = ctx.lock.get("npm", {}).get(comp.name or "") if comp.kind == "npm" else None
    if pin and version and version != pin and not ctx.latest:
        if not _npm_owned(comp, ctx):
            return Status("ok", f"{version} (installed outside npm; its own updater manages it)", version)
        return Status("outdated", f"{version} (lock {pin})", version)
    return Status("ok", version or "", version)


def _status_skills(comp: Component, ctx: Ctx) -> Status:
    lock = _skill_lock()
    pin = ctx.skills_pin(comp.source or "")
    missing, outdated, modified, conflicts = [], [], [], []
    for name in comp.skills:
        folder = paths.agents_skills_dir() / name
        entry = lock.get(name, {})
        if folder.exists() and entry.get("source") != comp.source:
            conflicts.append(name)
            continue
        if not (folder / "SKILL.md").exists():
            missing.append(name)
            continue
        recorded = ctx.state.section("skills").get(name, {})
        if recorded.get("hash") and recorded["hash"] != tree_hash(folder):
            modified.append(name)
        elif pin and entry.get("commit") != pin:
            outdated.append(name)
    from_source = {n for n, e in lock.items() if e.get("source") == comp.source and n not in comp.skills}
    owned = ctx.state.section("skills")
    # Prunable: Slipway installed it and the manifest no longer lists it. Leftover: same source, installed before
    # Slipway or by hand; reported with the exact remove command, never removed automatically.
    stale = sorted(n for n in from_source if owned.get(n, {}).get("source") == comp.source)
    leftover = sorted(from_source - set(stale))
    detail = []
    if missing:
        detail.append(f"missing {', '.join(missing)}")
    if outdated:
        detail.append(f"behind lock: {', '.join(outdated)}")
    if modified:
        detail.append(f"edited locally: {', '.join(modified)}")
    if conflicts:
        detail.append(f"name taken by another source: {', '.join(conflicts)}")
    if stale:
        detail.append(f"dropped from manifest: {', '.join(stale)}")
    if leftover:
        detail.append(f"older installs not in manifest: {', '.join(leftover)}")
    pin_text = f"@{pin[:7]}" if pin else "@HEAD (unpinned)"
    drifted = modified or stale or conflicts or leftover
    state = "missing" if missing else "outdated" if outdated else "drift" if drifted else "ok"
    count = f"{len(comp.skills)} skill{'s' if len(comp.skills) != 1 else ''}"
    text = "; ".join(detail) if detail else f"{count} {pin_text}"
    return Status(state, text, pin[:7] if pin else None, stale, leftover)


def _status_impeccable(comp: Component, ctx: Ctx) -> Status:
    installed = ctx.state.section("installed").get(comp.id, {}).get("version")
    if not (paths.agents_skills_dir() / "impeccable" / "SKILL.md").exists():
        return Status("missing")
    pin = ctx.lock.get("npm", {}).get("impeccable")
    if pin and installed and installed != pin and not ctx.latest:
        return Status("outdated", f"{installed} (lock {pin})", installed)
    return Status("ok", installed or "installed", installed)


def _claude_plugins() -> dict[str, Any]:
    file = paths.claude_dir() / "plugins" / "installed_plugins.json"
    try:
        return json.loads(file.read_text(encoding="utf-8")).get("plugins", {})
    except (OSError, ValueError):
        return {}


def _status_claude_plugin(comp: Component, ctx: Ctx) -> Status:
    entries = _claude_plugins().get(comp.plugin or "")
    if not entries:
        return Status("missing")
    return Status("ok", entries[0].get("version", ""), entries[0].get("version"))


def _omp_plugins(ctx: Ctx) -> list[dict[str, Any]]:
    res = ctx.runner.run(["omp", "plugin", "list", "--json"], mutate=False, check=False)
    try:
        data = json.loads(res.out)
    except ValueError:
        return []
    return [*data.get("npm", []), *data.get("marketplace", [])]


def _status_omp_plugin(comp: Component, ctx: Ctx) -> Status:
    wanted = {comp.name, (comp.plugin or "").split("@")[0], comp.plugin} - {None, ""}
    for entry in _omp_plugins(ctx):
        ident = entry.get("id") or entry.get("name") or ""
        if ident in wanted or ident.split("@")[0] in wanted:
            return Status("ok", entry.get("version", ""), entry.get("version"))
    return Status("missing")


def link_pairs(comp: Component, ctx: Ctx) -> list[tuple[Path, Path]]:
    """(link, target) pairs for a link component, only for harnesses that are present."""
    source = ctx.manifest.root / (comp.dir or "")
    keys = [k for k in comp.targets if k not in HARNESS_OF_TARGET or harness_present(HARNESS_OF_TARGET[k], ctx.runner)]
    pairs = []
    for item in sorted(source.glob(comp.pattern)):
        if item.name.startswith(".") or (item.is_dir() and not (item / "SKILL.md").exists()):
            continue
        pairs += [(paths.TARGET_DIRS[key]() / item.name, item) for key in keys]
    return pairs


def _status_link(comp: Component, ctx: Ctx) -> Status:
    pairs = link_pairs(comp, ctx)
    kinds = [links.inspect(link, target, ctx.state) for link, target in pairs]
    foreign = [p[0].name for p, k in zip(pairs, kinds, strict=True) if k == "foreign"]
    todo = [p[0].name for p, k in zip(pairs, kinds, strict=True) if k in ("missing", "ours-stale", "same-content")]
    if todo:
        return Status("missing", f"{len(todo)} to link: {', '.join(sorted(set(todo)))}")
    if foreign:
        return Status("drift", f"your own copy kept: {', '.join(sorted(set(foreign)))}")
    return Status("ok", f"{len(pairs)} links")


def block_targets(comp: Component, ctx: Ctx) -> list[Path]:
    return [paths.INSTRUCTION_FILES[t]() for t in comp.targets if harness_present(t, ctx.runner)]


def _status_block(comp: Component, ctx: Ctx) -> Status:
    content = (ctx.manifest.root / (comp.file or "")).read_text(encoding="utf-8")
    actions = {path: blocks.inspect(path, comp.id, content) for path in block_targets(comp, ctx)}
    if not actions:
        return Status("skipped", "no harness installed yet")
    edited = [paths.contract(p) for p, a in actions.items() if a == "edited"]
    pending = [paths.contract(p) for p, a in actions.items() if a in ("created", "updated")]
    if pending:
        return Status("missing", f"to write: {', '.join(pending)}")
    if edited:
        return Status("drift", f"edited by you: {', '.join(edited)}")
    return Status("ok", f"{len(actions)} files")


def omp_get(ctx: Ctx, key: str) -> Any:
    return ctx.omp_global().get(key)


def _omp_plan(ctx: Ctx) -> list[tuple[str, Any, Any, Any]]:
    """[(key, desired, merge-result, is_record)] for every [omp] key."""
    plan = []
    for key, desired in ctx.manifest.omp.items():
        is_record = isinstance(desired, dict)
        live = omp_get(ctx, key)
        live_rec = (live or {}) if is_record else ({} if live is None else {"value": live})
        want = desired if is_record else {"value": desired}
        last = ctx.state.section("omp").get(key, {})
        plan.append((key, want, merge_record(live_rec, last, want, ctx.force), is_record))
    return plan


def _status_omp_config(comp: Component, ctx: Ctx) -> Status:
    try:
        ctx.omp_global()
    except StepError as exc:
        return Status("skipped", f"cannot read omp config, nothing merged: {exc}")
    changes, drift = [], []
    for key, _want, result, _rec in _omp_plan(ctx):
        changes += [f"{key}.{c}" for c in result.changes]
        drift += [f"{key}.{d}" for d in result.drift]
    if changes:
        return Status(
            "missing", f"{len(changes)} to apply: " + "; ".join(changes[:3]) + ("…" if len(changes) > 3 else "")
        )
    if drift:
        return Status("drift", "; ".join(drift[:3]) + ("…" if len(drift) > 3 else ""))
    return Status("ok", f"{len(ctx.manifest.omp)} keys in sync")


_STATUS = {
    "brew": _status_package,
    "cask": _status_package,
    "npm": _status_package,
    "script": _status_package,
    "skills": _status_skills,
    "impeccable": _status_impeccable,
    "claude-plugin": _status_claude_plugin,
    "omp-plugin": _status_omp_plugin,
    "link": _status_link,
    "block": _status_block,
    "omp-config": _status_omp_config,
}


def _skill_lock() -> dict[str, Any]:
    try:
        return json.loads(paths.skill_lock_file().read_text(encoding="utf-8")).get("skills", {})
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- apply


class Skipped(Exception):
    """A prerequisite (e.g. the `claude` CLI for a Claude plugin) is absent; not a failure."""


def apply(comp: Component, ctx: Ctx, upgrade: bool = False, prune: bool = False) -> list[str]:
    """Install (or upgrade) one component. Returns human-readable changes; raises Skipped or StepError."""
    missing = missing_prereqs(comp, ctx.runner)
    if missing:
        raise Skipped(f"needs {', '.join(missing)}")
    return _APPLY[comp.kind](comp, ctx, upgrade, prune)


def _verify_installed(comp: Component, ctx: Ctx, command: str) -> None:
    """An installer that exits 0 without producing the tool is a failure, not a success."""
    if not ctx.runner.dry_run and not _present(comp, ctx):
        raise StepError(command, Result(1, "", f"finished but `{comp.bin or comp.name or comp.id}` is still not found"))


def _apply_brew(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    cask = ["--cask"] if comp.kind == "cask" else []
    if not _present(comp, ctx):
        ctx.runner.run(["brew", "install", *cask, comp.name or ""])
        _verify_installed(comp, ctx, f"brew install {' '.join(cask)} {comp.name}".replace("  ", " "))
        ctx.state.mark_installed(comp.id, by_slipway=True)
        return [f"installed {comp.name}"]
    ctx.state.mark_installed(comp.id, by_slipway=False)
    if upgrade:
        # Only formulae brew owns and reports as outdated; anything else is a no-op, not a reinstall.
        outdated = ctx.runner.run(["brew", "outdated", "--quiet", *cask, comp.name or ""], mutate=False, check=False)
        if not outdated.out.strip():
            return []
        res = ctx.runner.run(["brew", "upgrade", *cask, comp.name or ""], check=False)
        if not res.ok:
            raise StepError(f"brew upgrade {' '.join(cask)} {comp.name}".replace("  ", " "), res)
        return [f"upgraded {comp.name}"]
    return []


def _apply_npm(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    st = _status_package(comp, ctx)
    if st.state != "missing" and not upgrade:
        ctx.state.mark_installed(comp.id, by_slipway=False)
        return []  # install never changes the version of a tool you already have; `update` does
    if st.state == "ok" and not ctx.latest:
        return []  # at the locked version, or managed by another installer
    if st.state != "missing" and not _npm_owned(comp, ctx):
        return []  # never install a second npm copy over a standalone install
    spec = ctx.npm_spec(comp.name or "")
    ctx.runner.run(["npm", "install", "-g", spec])
    ctx.state.mark_installed(comp.id, by_slipway=st.state == "missing", version=spec.rsplit("@", 1)[-1])
    return [f"{'installed' if st.state == 'missing' else 'updated'} {spec}"]


def _apply_script(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    if not _present(comp, ctx):
        ctx.runner.run(comp.install or "true")
        _verify_installed(comp, ctx, comp.install or "")
        ctx.state.mark_installed(comp.id, by_slipway=True)
        return [f"installed {comp.id}"]
    ctx.state.mark_installed(comp.id, by_slipway=False)
    if upgrade and comp.upgrade:
        ctx.runner.run(comp.upgrade)
        return [f"upgraded {comp.id}"]
    return []


def _apply_skills(comp: Component, ctx: Ctx, upgrade: bool, prune: bool) -> list[str]:
    st = _status_skills(comp, ctx)
    lock = _skill_lock()
    pin = ctx.skills_pin(comp.source or "")
    changes: list[str] = []
    wanted, conflicts = [], []
    for name in comp.skills:
        folder = paths.agents_skills_dir() / name
        entry = lock.get(name, {})
        recorded = ctx.state.section("skills").get(name, {})
        edited = recorded.get("hash") and recorded["hash"] != tree_hash(folder)
        if folder.exists() and entry.get("source") != comp.source and not ctx.force:
            conflicts.append(name)  # same name, different origin: never overwrite someone else's skill
            continue
        present = (folder / "SKILL.md").exists() and entry.get("source") == comp.source
        behind = bool(pin) and entry.get("commit") != pin
        if not present or ((behind or (upgrade and not pin)) and (not edited or ctx.force)):
            wanted.append(name)
    if conflicts:
        changes.append(f"kept existing {', '.join(conflicts)} (installed from elsewhere; --force replaces)")
    if wanted:
        source = f"{comp.source}@{pin}" if pin else comp.source or ""
        agents = comp.agents or ctx.manifest.settings.get("skill_agents", ["pi", "claude-code"])
        cli = ctx.manifest.settings.get("skills_cli", "skills")
        ctx.runner.run(ctx.npx(cli, "add", source, "-g", "-a", *agents, "-s", *wanted, "-y", *comp.args))
        changes.append(f"{'pinned' if pin else 'latest'} {comp.source}: {', '.join(wanted)}")
    if not ctx.runner.dry_run:
        fresh = _skill_lock()
        for name in comp.skills:
            folder = paths.agents_skills_dir() / name
            if name in wanted or name not in ctx.state.section("skills"):
                ctx.state.section("skills")[name] = {
                    "source": comp.source,
                    "commit": fresh.get(name, {}).get("commit"),
                    "hash": tree_hash(folder),
                }
    if prune and st.stale:
        cli = ctx.manifest.settings.get("skills_cli", "skills")
        ctx.runner.run(ctx.npx(cli, "remove", *st.stale, "-g", "-y"))
        for name in st.stale:
            ctx.state.section("skills").pop(name, None)
        changes.append(f"{'would prune' if ctx.runner.dry_run else 'pruned'} {', '.join(st.stale)}")
    return changes


def _apply_impeccable(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    st = _status_impeccable(comp, ctx)
    if st.state == "ok" and not (upgrade and ctx.latest):
        return []
    args = ["install", f"--providers={','.join(comp.providers)}", "--scope=global", "-y", *comp.args]
    if st.state != "missing":
        args.append("--force")
    ctx.runner.run(ctx.npx("impeccable", *args))
    version = ctx.npm_spec("impeccable").rsplit("@", 1)[-1]
    ctx.state.mark_installed(comp.id, by_slipway=st.state == "missing", version=version)
    return [f"impeccable {version} for {', '.join(comp.providers)}"]


def _apply_claude_plugin(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    if _status_claude_plugin(comp, ctx).state == "ok":
        ctx.state.mark_installed(comp.id, by_slipway=False)
        if upgrade:
            ctx.runner.run(["claude", "plugin", "marketplace", "update"], check=False)
            ctx.runner.run(["claude", "plugin", "update", comp.plugin or ""], check=False)
            return [f"checked {comp.plugin} for updates"]
        return []
    ctx.runner.run(["claude", "plugin", "marketplace", "add", comp.marketplace or ""], check=False)
    ctx.runner.run(["claude", "plugin", "install", comp.plugin or ""])
    ctx.state.mark_installed(comp.id, by_slipway=True)
    return [f"installed Claude plugin {comp.plugin}"]


def _apply_omp_plugin(comp: Component, ctx: Ctx, upgrade: bool, _prune: bool) -> list[str]:
    if _status_omp_plugin(comp, ctx).state == "ok":
        ctx.state.mark_installed(comp.id, by_slipway=False)
        if upgrade:
            ctx.runner.run(["omp", "plugin", "upgrade", comp.plugin or ""], check=False)
            return [f"checked {comp.plugin} for updates"]
        return []
    if comp.marketplace:
        ctx.runner.run(["omp", "plugin", "marketplace", "add", comp.marketplace], check=False)
        ctx.runner.run(["omp", "plugin", "install", "--scope", "user", comp.plugin or ""])
    else:  # npm package or github:owner/repo source
        ctx.runner.run(["omp", "plugin", "install", comp.plugin or ""])
    ctx.state.mark_installed(comp.id, by_slipway=True)
    return [f"installed omp plugin {comp.plugin}"]


def _apply_link(comp: Component, ctx: Ctx, _upgrade: bool, _prune: bool) -> list[str]:
    changes = []
    for link, target in link_pairs(comp, ctx):
        res = links.ensure(link, target, ctx.state, comp.id, force=ctx.force, dry_run=ctx.runner.dry_run)
        if res.action != "ok":
            changes.append(f"{res.action} {paths.contract(link)}" + (f" ({res.detail})" if res.detail else ""))
    return changes


def _apply_block(comp: Component, ctx: Ctx, _upgrade: bool, _prune: bool) -> list[str]:
    content = (ctx.manifest.root / (comp.file or "")).read_text(encoding="utf-8")
    changes = []
    for path in block_targets(comp, ctx):
        res = blocks.upsert(path, comp.id, content, force=ctx.force, dry_run=ctx.runner.dry_run)
        if res.action == "edited":
            changes.append(f"kept your edits in {paths.contract(path)} (use --force to replace)")
        elif res.action != "unchanged":
            verb = f"would write ({res.action})" if ctx.runner.dry_run else res.action
            changes.append(f"{verb} block in {paths.contract(path)}")
    return changes


def _apply_omp_config(comp: Component, ctx: Ctx, _upgrade: bool, _prune: bool) -> list[str]:
    changes = []
    for key, _want, result, is_record in _omp_plan(ctx):
        for item in result.drift:
            changes.append(f"kept local {key}.{item}")
        if result.changed:
            value = result.value if is_record else result.value.get("value")
            payload = json.dumps(value) if is_record or not isinstance(value, str) else value
            ctx.runner.run(["omp", "config", "set", key, payload])
            ctx._omp_global = None
            changes += [f"{'would ' if ctx.runner.dry_run else ''}{key}: {c}" for c in result.changes]
        if not ctx.runner.dry_run:
            ctx.state.section("omp")[key] = result.written
    return changes


_APPLY = {
    "brew": _apply_brew,
    "cask": _apply_brew,
    "npm": _apply_npm,
    "script": _apply_script,
    "skills": _apply_skills,
    "impeccable": _apply_impeccable,
    "claude-plugin": _apply_claude_plugin,
    "omp-plugin": _apply_omp_plugin,
    "link": _apply_link,
    "block": _apply_block,
    "omp-config": _apply_omp_config,
}


# ---------------------------------------------------------------- uninstall


def remove(comp: Component, ctx: Ctx) -> list[str]:
    """Undo what Slipway wrote for this component. Packages are only reported, never uninstalled automatically."""
    dry = ctx.runner.dry_run
    if comp.kind == "block":
        return [
            f"removed block from {paths.contract(r.path)}"
            for r in (blocks.remove(p, comp.id, dry_run=dry) for p in block_targets(comp, ctx))
            if r.action == "removed"
        ]
    if comp.kind == "omp-config" and ctx.runner.which("omp"):
        out = []
        for key, last in list(ctx.state.section("omp").items()):
            live = omp_get(ctx, key)
            if isinstance(live, dict):
                kept = {k: v for k, v in live.items() if last.get(k) != v}
                if kept != live:
                    ctx.runner.run(["omp", "config", "set", key, json.dumps(kept)])
                    out.append(f"removed {len(live) - len(kept)} Slipway entries from {key}")
            elif live is not None and "value" in last and live == last["value"]:
                ctx.runner.run(["omp", "config", "reset", key])
                out.append(f"reset {key}")
            if not dry:
                ctx.state.section("omp").pop(key, None)
        return out
    installed = ctx.state.section("installed").get(comp.id, {})
    if installed.get("by_slipway"):
        hint = {
            "brew": f"brew uninstall {comp.name}",
            "cask": f"brew uninstall --cask {comp.name}",
            "npm": f"npm uninstall -g {comp.name}",
            "claude-plugin": f"claude plugin uninstall {comp.plugin}",
            "omp-plugin": f"omp plugin uninstall {comp.plugin}",
        }.get(comp.kind)
        if hint:
            return [f"left installed (remove with: {hint})"]
    return []
