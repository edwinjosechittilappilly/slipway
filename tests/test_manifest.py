"""Manifest loading, overlays and validation, plus a contract check on the repository's own manifest and skills."""

import re
import unittest
from pathlib import Path

from support import REPO, HomeTestCase

from slipway import manifest
from slipway.manifest import ManifestError

BASE = """
version = 1
[settings]
default_packs = ["core"]
[packs.core]
description = "core"
[packs.extra]
description = "extra"
[[component]]
id = "jq"
pack = "core"
kind = "brew"
name = "jq"
[roles.plan]
harness = "omp"
model = "@plan"
"""


class OverlayTest(HomeTestCase):
    def write_repo(self, base: str = BASE, profile: str | None = None) -> Path:
        root = self.home / "repo"
        (root / "profiles").mkdir(parents=True)
        (root / "slipway.toml").write_text(base)
        if profile:
            (root / "profiles" / "me.toml").write_text(profile)
        return root

    def test_profile_and_local_config_overlay_the_base(self):
        root = self.write_repo(
            profile='enable_packs = ["extra"]\n[roles.plan]\nmodel = "@slow"\n[[component]]\nid = "jq"\nname = "jq@1"\n'
        )
        local = self.home / ".config" / "slipway" / "config.toml"
        local.parent.mkdir(parents=True)
        local.write_text('profile = "me"\ndisable_packs = ["core"]\n')
        m = manifest.load(root)
        self.assertEqual(m.profile, "me")
        self.assertEqual(m.default_packs, ["extra"])
        self.assertEqual(m.roles["plan"].model, "@slow")
        self.assertEqual(m.roles["plan"].harness, "omp", "overlay keeps fields it does not set")
        self.assertEqual(m.component("jq").name, "jq@1")

    def test_unknown_profile_names_the_known_ones(self):
        root = self.write_repo(profile="# empty profile\n")
        with self.assertRaisesRegex(ManifestError, "known: me"):
            manifest.load(root, profile="nobody")

    def test_validation_errors_name_the_component(self):
        cases = {
            'kind = "brew"': ('kind = "teleport"', "unknown kind 'teleport'"),
            'pack = "core"': ('pack = "nope"', "pack 'nope' is not declared"),
            'name = "jq"': ("bogus = 1", "needs name"),
        }
        for old, (new, message) in cases.items():
            with self.subTest(message):
                root = self.home / message.replace(" ", "_").replace("'", "")
                (root).mkdir()
                (root / "slipway.toml").write_text(BASE.replace(old, new, 1))
                with self.assertRaisesRegex(ManifestError, re.escape(message)):
                    manifest.load(root, use_local=False)

    def test_duplicate_ids_are_rejected(self):
        root = self.write_repo(BASE + '[[component]]\nid = "jq"\npack = "core"\nkind = "brew"\nname = "jq"\n')
        with self.assertRaisesRegex(ManifestError, "duplicate component id: jq"):
            manifest.load(root)

    def test_select_rejects_unknown_packs(self):
        m = manifest.load(self.write_repo())
        with self.assertRaisesRegex(ManifestError, "unknown pack"):
            m.select(["nope"])

    def test_remember_profile_is_idempotent_and_replaces(self):
        self.assertTrue(manifest.remember_profile("me"))
        self.assertFalse(manifest.remember_profile("me"))
        self.assertTrue(manifest.remember_profile("you"))
        text = (self.home / ".config" / "slipway" / "config.toml").read_text()
        self.assertEqual(text.count("profile ="), 1)
        self.assertIn('profile = "you"', text)


class RepositoryContractTest(HomeTestCase):
    """What a forker relies on: the shipped manifest, profiles, skills and files are consistent."""

    def test_base_and_every_profile_load(self):
        manifest.load(REPO, use_local=False)
        for prof in (REPO / "profiles").glob("*.toml"):
            with self.subTest(prof.stem):
                m = manifest.load(REPO, profile=prof.stem, use_local=False)
                self.assertTrue(m.select(all_packs=True))

    def test_referenced_files_exist(self):
        m = manifest.load(REPO, use_local=False)
        for comp in m.components:
            if comp.kind == "link":
                self.assertTrue((REPO / comp.dir).is_dir(), comp.id)
            if comp.kind == "block":
                self.assertTrue((REPO / comp.file).is_file(), comp.id)

    def test_own_skills_have_valid_frontmatter(self):
        for skill in sorted((REPO / "skills").iterdir()):
            if not skill.is_dir():
                continue
            with self.subTest(skill.name):
                text = (skill / "SKILL.md").read_text()
                front = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
                self.assertIsNotNone(front, "frontmatter")
                self.assertRegex(front.group(1), rf"(?m)^name: {re.escape(skill.name)}$")
                desc = re.search(r"(?m)^description: (.+)$", front.group(1))
                self.assertIsNotNone(desc)
                self.assertLessEqual(len(desc.group(1)), 1024, "Agent Skills spec limit")
                for link in re.findall(r"\]\(([^)#:<]+)\)", text):
                    self.assertTrue((skill / link).exists(), f"broken link {link}")

    def test_upstream_skill_names_do_not_collide_with_own_skills(self):
        m = manifest.load(REPO, use_local=False)
        own = {p.name for p in (REPO / "skills").iterdir() if p.is_dir()}
        upstream = [name for c in m.components if c.kind == "skills" for name in c.skills]
        self.assertEqual(len(upstream), len(set(upstream)), "two packs install the same skill name")
        self.assertFalse(own & set(upstream))


if __name__ == "__main__":
    unittest.main()
