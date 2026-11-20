"""User profiles: captured from the live omp setup, stored outside the checkout, able to switch components off."""

import json
import tomllib

from support import REPO, FakeRunner, HomeTestCase

from slipway import manifest, profiles
from slipway.shell import Result

LIVE = {
    "modelRoles": {"value": {"plan": "openai/gpt:high", "scout": "google/gemini-flash:low"}},
    "task.agentModelOverrides": {"value": {"reviewer": "@review"}},
    "modelPresets": {"value": {"cheap": {"defaultThinkingLevel": "low", "modelRoles": {"plan": "openai/mini"}}}},
    "defaultThinkingLevel": {"value": "auto"},
    "theme.dark": {"value": "titanium"},
}


class ProfileTest(HomeTestCase):
    def test_captured_profile_round_trips_and_reproduces_the_live_routing(self):
        runner = FakeRunner(bins={"omp"}, responses={"omp config list": Result(0, json.dumps(LIVE))})
        data = tomllib.loads(profiles.from_current_setup(runner))
        self.assertEqual(data["omp"]["modelRoles"], LIVE["modelRoles"]["value"])
        self.assertEqual(data["omp"]["task.agentModelOverrides"], {"reviewer": "@review"})
        self.assertEqual(data["omp"]["modelPresets"], LIVE["modelPresets"]["value"])
        self.assertEqual(data["omp"]["defaultThinkingLevel"], "auto")
        self.assertNotIn("theme.dark", data["omp"], "only routing settings, not UI preferences")

    def test_without_omp_the_template_still_parses(self):
        tomllib.loads(profiles.from_current_setup(FakeRunner(bins=set())))

    def test_user_profile_dir_wins_and_can_disable_a_component(self):
        mine = self.home / ".config" / "slipway" / "profiles" / "edwin.toml"
        mine.parent.mkdir(parents=True)
        mine.write_text('[[component]]\nid = "codex"\nenabled = false\n')
        m = manifest.load(REPO, profile="edwin", use_local=False)
        self.assertFalse(m.component("codex").enabled)
        self.assertNotIn("codex", [c.id for c in m.select(all_packs=True)])
        self.assertIn("edwin", manifest.list_profiles(REPO))

    def test_shipped_single_harness_profiles_drop_omp(self):
        for name, harness in (("claude-code", "claude"), ("codex", "codex")):
            with self.subTest(name):
                m = manifest.load(REPO, profile=name, use_local=False)
                ids = [c.id for c in m.select()]
                self.assertNotIn("omp", ids)
                self.assertNotIn("omp-routing", ids)
                self.assertEqual(m.roles["implement"].harness, harness)
