"""Command execution with dry-run support. Every external command goes through Runner so tests can fake it."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field

from slipway import ui

QUIET_ENV = {
    # npx-based installers (skills, impeccable, openspec) phone home unless told not to.
    "DISABLE_TELEMETRY": "1",
    "DO_NOT_TRACK": "1",
    "OPENSPEC_NO_UPDATE_CHECK": "1",
    "HOMEBREW_NO_ENV_HINTS": "1",
    "NONINTERACTIVE": "1",
}


@dataclass
class Result:
    code: int
    out: str = ""
    err: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0


class StepError(RuntimeError):
    """A mutating command failed; carries the command so the summary can print a retry line."""

    def __init__(self, command: str, result: Result):
        lines = [ln.strip() for ln in (result.err or result.out).strip().splitlines() if ln.strip()]
        # Prefer the tool's own error line (Homebrew, npm) over whatever trailing help text follows it.
        error_at = next((i for i, ln in enumerate(lines) if ln.lower().startswith(("error:", "npm err!"))), None)
        tail = lines[error_at : error_at + 2] if error_at is not None else lines[-3:]
        super().__init__(f"`{command}` exited {result.code}" + (": " + " | ".join(tail) if tail else ""))
        self.command = command
        self.result = result


def render(cmd: list[str] | str) -> str:
    return cmd if isinstance(cmd, str) else shlex.join(cmd)


def search_path() -> str:
    """PATH plus the dirs upstream installers write to, which may not be on this process's PATH yet."""
    home = os.environ.get("HOME", "")
    extra = [
        f"{home}/.local/bin",
        f"{home}/.bun/bin",
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/home/linuxbrew/.linuxbrew/bin",
    ]
    current = os.environ.get("PATH", "")
    return os.pathsep.join([current, *(d for d in extra if d not in current.split(os.pathsep))])


@dataclass
class Runner:
    dry_run: bool = False
    verbose: bool = False
    calls: list[str] = field(default_factory=list)

    def which(self, name: str) -> str | None:
        return shutil.which(name, path=search_path())

    def run(
        self,
        cmd: list[str] | str,
        *,
        mutate: bool = True,
        check: bool = True,
        cwd: str | None = None,
        stream: bool = False,
    ) -> Result:
        """Run a command. Read-only probes pass mutate=False and run even in dry-run mode."""
        text = render(cmd)
        self.calls.append(text)
        if mutate and self.dry_run:
            ui.line(f"  would run: {text}", style="dim")
            return Result(0)
        if mutate or self.verbose:
            ui.line(f"  $ {text}", style="dim")
        env = {**os.environ, **QUIET_ENV, "PATH": search_path()}
        # Shell strings (upstream `curl … | sh` installers) run with pipefail, so a failed download is a failure.
        argv = ["/bin/bash", "-o", "pipefail", "-c", cmd] if isinstance(cmd, str) else cmd
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                text=True,
                stdin=subprocess.DEVNULL,
                capture_output=not stream,
            )
        except FileNotFoundError as exc:
            result = Result(127, "", str(exc))
        else:
            result = Result(proc.returncode, proc.stdout or "", proc.stderr or "")
        if check and not result.ok:
            raise StepError(text, result)
        return result
