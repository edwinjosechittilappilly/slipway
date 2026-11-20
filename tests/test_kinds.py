"""Component kinds against a fake runner and a temporary HOME: the commands Slipway would run, and what it refuses."""

import json
import unittest

from support import REPO, FakeRunner, HomeTestCase

from slipway import kinds, manifest
from slipway.kinds import Ctx
from slipway.manifest import Component
from slipway.shell import Result, StepError
from slipway.state import State

PIN = "a" * 40


class SkillsKindTest(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.m = manifest.load(REPO, use_local=False)
        self.comp = Component(
            id="matt", kind="skills", pack="engineering", source="mattpocock/skills", skills=["tdd", "grill-me"]
        )
        self.runner = FakeRunner(bins={"npx", "git"})
        self.ctx = Ctx(
            self.m,
            {"skills": {"mattpocock/skills": {"commit": PIN}}, "npm": {"skills": "1.9.0"}},
            State.load(self.home / "state.json"),
            self.runner,
        )

    def install_skill(self, name: str, source: str, commit: str | None = PIN) -> None:
        folder = self.home / ".agents" / "skills" / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        lock_file = self.home / ".agents" / ".skill-lock.json"
        lock = json.loads(lock_file.read_text()) if lock_file.exists() else {"version": 3, "skills": {}}
        lock["skills"][name] = {"source": source, "commit": commit}
        lock_file.write_text(json.dumps(lock))

    def test_installs_missing_skills_at_the_locked_commit_with_pinned_cli(self):
        kinds.apply(self.comp, self.ctx)
        self.assertEqual(
            self.runner.mutations,
            [f"npx -y skills@1.9.0 add mattpocock/skills@{PIN} -g -a pi claude-code -s tdd grill-me -y"],
        )

    def test_never_overwrites_a_same_named_skill_from_another_source(self):
        self.install_skill("tdd", "someone/else")
        changes = kinds.apply(self.comp, self.ctx)
        self.assertNotIn("-s tdd", " ".join(self.runner.mutations))
        self.assertTrue(any("kept existing tdd" in c for c in changes))
        self.assertIn("name taken by another source: tdd", kinds.status(self.comp, self.ctx).detail)

    def test_prune_removes_only_skills_slipway_installed_and_reports_older_ones(self):
        self.install_skill("tdd", "mattpocock/skills")
        self.install_skill("grill-me", "mattpocock/skills")
        self.install_skill("to-prd", "mattpocock/skills", commit="old")  # installed by hand before Slipway
        self.install_skill("wayfinder", "mattpocock/skills")  # installed by Slipway, later dropped from the manifest
        self.ctx.state.section("skills")["wayfinder"] = {"source": "mattpocock/skills"}
        status = kinds.status(self.comp, self.ctx)
        self.assertEqual(status.state, "drift")
        self.assertEqual(status.stale, ["wayfinder"])
        self.assertEqual(status.leftover, ["to-prd"])
        kinds.apply(self.comp, self.ctx)
        self.assertEqual(self.runner.mutations, [], "install alone removes nothing")
        kinds.apply(self.comp, self.ctx, prune=True)
        self.assertEqual(self.runner.mutations, ["npx -y skills@1.9.0 remove wayfinder -g -y"])

    def test_a_new_lock_commit_reinstalls_unless_the_skill_was_edited(self):
        self.install_skill("tdd", "mattpocock/skills", commit="b" * 40)
        self.install_skill("grill-me", "mattpocock/skills", commit="b" * 40)
        self.ctx.state.section("skills")["tdd"] = {"hash": "not-the-current-hash"}  # user edited tdd
        self.assertEqual(kinds.status(self.comp, self.ctx).state, "outdated")
        kinds.apply(self.comp, self.ctx, upgrade=True)
        self.assertEqual(
            self.runner.mutations,
            [f"npx -y skills@1.9.0 add mattpocock/skills@{PIN} -g -a pi claude-code -s grill-me -y"],
        )

    def test_missing_prerequisite_is_a_skip_not_a_failure(self):
        ctx = Ctx(self.m, {}, State.load(self.home / "s.json"), FakeRunner(bins=set()))
        with self.assertRaises(kinds.Skipped):
            kinds.apply(self.comp, ctx)


class OmpConfigKindTest(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.m = manifest.load(REPO, use_local=False)
        self.m.omp = {"modelRoles": {"plan": "p/new", "smol": "s/1"}}
        self.comp = Component(id="omp-routing", kind="omp-config", pack="routing")
        self.live = {"modelRoles": {"value": {"plan": "p/mine", "tiny": "t/1"}}}
        self.runner = FakeRunner(
            bins={"omp"},
            responses={
                "omp config list --scope global --json": lambda _t: Result(0, json.dumps(self.live)),
            },
        )
        self.ctx = Ctx(self.m, {}, State.load(self.home / "state.json"), self.runner)

    def test_adds_missing_roles_keeps_user_roles_and_untouched_extras(self):
        changes = kinds.apply(self.comp, self.ctx)
        self.assertEqual(len(self.runner.mutations), 1)
        written = json.loads(self.runner.mutations[0].split(" ", 4)[4].strip("'"))
        self.assertEqual(written, {"plan": "p/mine", "tiny": "t/1", "smol": "s/1"})
        self.assertTrue(any("kept local modelRoles.plan" in c for c in changes))

    def test_reports_drift_without_writing(self):
        self.live = {"modelRoles": {"value": {"plan": "p/mine", "smol": "s/1"}}}
        status = kinds.status(self.comp, self.ctx)
        self.assertEqual(status.state, "drift")
        self.assertEqual(self.runner.mutations, [])

    def test_unreadable_omp_config_writes_nothing(self):
        for broken in (Result(1, "", "unknown flag --scope"), Result(0, "omp 20.0 is available!\n{}")):
            with self.subTest(broken=broken):
                runner = FakeRunner(bins={"omp"}, responses={"omp config list": broken})
                ctx = Ctx(self.m, {}, State.load(self.home / "s.json"), runner)
                self.assertEqual(kinds.status(self.comp, ctx).state, "skipped")
                with self.assertRaises(StepError):
                    kinds.apply(self.comp, ctx)
                self.assertEqual(runner.mutations, [], "never overwrite roles we could not read")


class ScriptKindTest(HomeTestCase):
    def test_installer_that_exits_zero_without_the_tool_is_a_failure(self):
        m = manifest.load(REPO, use_local=False)
        runner = FakeRunner(bins={"curl"})  # the installer "succeeds" but `omp` never appears
        with self.assertRaisesRegex(StepError, "still not found"):
            kinds.apply(m.component("omp"), Ctx(m, {}, State.load(self.home / "s.json"), runner))
        self.assertEqual(runner.mutations, ["curl -fsSL https://omp.sh/install | sh"])


class PackageKindTest(HomeTestCase):
    def test_npm_install_uses_the_lock_and_never_downgrades_on_install(self):
        m = manifest.load(REPO, use_local=False)
        comp = m.component("openspec")
        missing = FakeRunner(bins={"npm"})
        kinds.apply(comp, Ctx(m, {"npm": {"@fission-ai/openspec": "2.1.1"}}, State.load(self.home / "a"), missing))
        self.assertEqual(missing.mutations, ["npm install -g @fission-ai/openspec@2.1.1"])

        owned = Result(0, json.dumps({"dependencies": {"@fission-ai/openspec": {"version": "2.0.0"}}}))
        present = FakeRunner(
            bins={"npm", "openspec"},
            responses={"openspec --version": Result(0, "2.0.0\n"), "npm ls -g": owned},
        )
        ctx = Ctx(m, {"npm": {"@fission-ai/openspec": "2.1.1"}}, State.load(self.home / "b"), present)
        self.assertEqual(kinds.status(comp, ctx).state, "outdated")
        kinds.apply(comp, ctx)
        self.assertEqual(present.mutations, [], "install leaves existing versions alone")
        kinds.apply(comp, ctx, upgrade=True)
        self.assertEqual(present.mutations, ["npm install -g @fission-ai/openspec@2.1.1"])

    def test_update_never_shadows_a_standalone_install_with_an_npm_copy(self):
        m = manifest.load(REPO, use_local=False)
        comp = m.component("codex")
        runner = FakeRunner(
            bins={"npm", "codex"},
            responses={"codex --version": Result(0, "codex-cli 0.144.6\n"), "npm ls -g": Result(0, '{"name":"lib"}')},
        )
        ctx = Ctx(m, {"npm": {"@openai/codex": "0.171.0"}}, State.load(self.home / "c"), runner)
        self.assertEqual(kinds.status(comp, ctx).state, "ok")
        kinds.apply(comp, ctx, upgrade=True)
        self.assertEqual(runner.mutations, [])


if __name__ == "__main__":
    unittest.main()
