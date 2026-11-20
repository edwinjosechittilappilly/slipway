"""Role routing commands and `slipway init` on a scratch repository."""

import contextlib
import io
import json
import subprocess
import unittest

from support import REPO, FakeRunner, HomeTestCase

from slipway import manifest, project, roles
from slipway.shell import Result


class CommandTest(unittest.TestCase):
    def test_each_harness_gets_its_own_flags(self):
        cases = {
            ("omp", "openai/gpt:high", False): ["omp", "--model", "openai/gpt", "--thinking", "high", "go"],
            ("claude", "opus", True): ["claude", "--model", "opus", "-p", "go"],
            ("codex", "gpt-5", True): ["codex", "exec", "-m", "gpt-5", "go"],
            ("codex", "default", False): ["codex", "go"],
            ("gemini", "gemini-pro", True): ["gemini", "-m", "gemini-pro", "-p", "go"],
            ("omp", "@review", True): ["omp", "--model", "@review", "-p", "go"],
            ("claude", "@review", False): ["claude", "go"],
        }
        for (harness, model, print_mode), expected in cases.items():
            with self.subTest(harness=harness, model=model):
                self.assertEqual(roles.command(harness, model, "go", print_mode), expected)

    def test_resolves_role_aliases_through_chains(self):
        aliases = {"review": "@slow", "slow": "anthropic/opus:high,openai/gpt"}
        self.assertEqual(roles.resolve("@review", aliases), "anthropic/opus:high")
        self.assertEqual(roles.resolve("@missing", aliases), "@missing")


class BeadHandoffTest(HomeTestCase):
    def test_bead_label_picks_the_role_and_the_bead_is_claimed(self):
        issue = [{"id": "x-1", "title": "Add login", "description": "Body", "labels": ["role:review"], "parent": "x-0"}]
        runner = FakeRunner(bins={"bd"}, responses={"bd show x-1 --json": Result(0, json.dumps(issue))})
        role, prompt = roles.bead_prompt(runner, "x-1", claim=True)
        self.assertEqual(role, "review")
        self.assertIn("Add login", prompt)
        self.assertIn("bd close x-1", prompt)
        self.assertEqual(runner.mutations, ["bd update x-1 --claim"])


class ProjectInitTest(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.repo = self.home / "app"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.m = manifest.load(REPO, use_local=False)

    def test_wires_beads_openspec_docs_and_agent_files_idempotently(self):
        runner = FakeRunner(bins={"bd", "openspec", "omp", "claude", "git"}, responses={"git -C": Result(0, ".git")})
        self.assertEqual(project.init(self.m, self.repo, runner), 0)
        self.assertIn("bd init --non-interactive --skip-agents -q", runner.mutations)
        self.assertIn("bd metrics off", runner.mutations)
        self.assertIn("openspec init --tools oh-my-pi,claude --scope global --no-animation", runner.mutations)
        self.assertTrue((self.repo / "docs/agents/issue-tracker.md").read_text().startswith("# Issue tracker: Beads"))
        agents = (self.repo / "AGENTS.md").read_text()
        self.assertIn("Delivery workflow (Slipway)", agents)
        self.assertIn("@AGENTS.md", (self.repo / "CLAUDE.md").read_text())

        (self.repo / "docs/agents/triage-labels.md").write_text("mine")
        project.init(self.m, self.repo, runner)
        self.assertEqual((self.repo / "docs/agents/triage-labels.md").read_text(), "mine", "never overwrites docs")
        self.assertEqual((self.repo / "AGENTS.md").read_text(), agents, "second run changes nothing")

    def test_refresh_updates_an_old_block_and_keeps_an_edited_one(self):
        old = (
            "<!-- slipway:begin slipway-project sha256=0000000000000000 -->\n"
            "old rules\n"
            "<!-- slipway:end slipway-project -->\n"
        )
        (self.repo / "AGENTS.md").write_text("# App\n\n" + old)
        self.assertEqual(project.refresh_blocks(self.m, self.repo)["AGENTS.md"], "edited", "hash mismatch = user edit")
        project.refresh_blocks(self.m, self.repo, force=True)
        self.assertIn("Delivery workflow (Slipway)", (self.repo / "AGENTS.md").read_text())
        self.assertTrue((self.repo / "AGENTS.md").read_text().startswith("# App\n"))

    def test_missing_tools_fail_clearly_without_side_effects(self):
        runner = FakeRunner(bins={"git"}, responses={"git -C": Result(0, ".git")})
        self.assertEqual(project.init(self.m, self.repo, runner, openspec=False), 1)
        self.assertFalse(any(c.startswith("bd ") for c in runner.mutations))


if __name__ == "__main__":
    unittest.main()
