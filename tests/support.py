"""Test helpers: a temporary HOME and a fake command runner (no network, no real installs)."""

from __future__ import annotations

import os
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from slipway.shell import Result, Runner, StepError, render

REPO = Path(__file__).resolve().parents[1]

Response = Result | Callable[[str], Result]


class FakeRunner(Runner):
    """Records every command. `bins` are the executables `which` finds; `responses` maps command prefixes to results."""

    def __init__(self, bins=(), responses: dict[str, Response] | None = None, dry_run: bool = False):
        super().__init__(dry_run=dry_run)
        self.bins = set(bins)
        self.responses = responses or {}
        self.mutations: list[str] = []

    def which(self, name: str) -> str | None:
        return f"/fake/bin/{name}" if name in self.bins else None

    def run(self, cmd, *, mutate=True, check=True, cwd=None, stream=False) -> Result:
        text = render(cmd)
        self.calls.append(text)
        if mutate:
            self.mutations.append(text)
            if self.dry_run:
                return Result(0)
        result = Result(0)
        for prefix, response in self.responses.items():
            if text.startswith(prefix):
                result = response(text) if callable(response) else response
                break
        if check and not result.ok:
            raise StepError(text, result)
        return result


class HomeTestCase(unittest.TestCase):
    """Each test gets an empty HOME and no XDG overrides, so nothing touches the real machine."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        env = {"HOME": str(self.home), "SLIPWAY_HOME": str(REPO)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        for var in (
            "XDG_STATE_HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "OMP_PROFILE",
            "PI_PROFILE",
            "PI_CODING_AGENT_DIR",
            "CLAUDE_CONFIG_DIR",
            "CODEX_HOME",
            "SLIPWAY_PROFILE",
        ):
            os.environ.pop(var, None)
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
