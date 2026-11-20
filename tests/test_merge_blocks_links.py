"""The ownership rules: never clobber what the user changed, clean up what Slipway left behind."""

import unittest

from support import HomeTestCase

from slipway import blocks, links
from slipway.merge import merge_record
from slipway.state import State


class MergeRecordTest(unittest.TestCase):
    def test_sets_missing_keys_and_adopts_matching_ones(self):
        res = merge_record(live={"plan": "a"}, last={}, desired={"plan": "a", "smol": "b"})
        self.assertEqual(res.value, {"plan": "a", "smol": "b"})
        self.assertEqual(res.written, {"plan": "a", "smol": "b"})
        self.assertEqual(res.changes, ["set smol = b"])

    def test_updates_a_value_the_user_never_touched(self):
        res = merge_record(live={"plan": "old"}, last={"plan": "old"}, desired={"plan": "new"})
        self.assertEqual(res.value["plan"], "new")

    def test_keeps_a_value_the_user_changed(self):
        res = merge_record(live={"plan": "mine"}, last={"plan": "old"}, desired={"plan": "new"})
        self.assertEqual(res.value["plan"], "mine")
        self.assertFalse(res.changed)
        self.assertIn("plan", res.drift[0])
        self.assertEqual(res.written, {"plan": "old"}, "remembers what Slipway wrote, so --force can tell later")

    def test_keeps_a_pre_existing_user_value(self):
        res = merge_record(live={"plan": "mine"}, last={}, desired={"plan": "new"})
        self.assertEqual(res.value["plan"], "mine")
        self.assertTrue(res.drift)

    def test_respects_a_key_the_user_deleted(self):
        res = merge_record(live={}, last={"plan": "x"}, desired={"plan": "x"})
        self.assertNotIn("plan", res.value)
        self.assertTrue(res.drift)

    def test_removes_a_key_the_manifest_dropped_only_if_untouched(self):
        dropped = merge_record(live={"plan": "x", "other": "u"}, last={"plan": "x"}, desired={})
        self.assertEqual(dropped.value, {"other": "u"})
        kept = merge_record(live={"plan": "mine"}, last={"plan": "x"}, desired={})
        self.assertEqual(kept.value, {"plan": "mine"})

    def test_force_overrides_user_values(self):
        res = merge_record(live={"plan": "mine"}, last={}, desired={"plan": "new"}, force=True)
        self.assertEqual(res.value["plan"], "new")


class BlocksTest(HomeTestCase):
    def test_lifecycle(self):
        path = self.home / "AGENTS.md"
        path.write_text("# Mine\n\nKeep this.\n")
        self.assertEqual(blocks.upsert(path, "rules", "Rule one").action, "created")
        self.assertEqual(blocks.upsert(path, "rules", "Rule one").action, "unchanged")
        self.assertEqual(blocks.upsert(path, "rules", "Rule two").action, "updated")
        text = path.read_text()
        self.assertIn("Keep this.", text)
        self.assertIn("Rule two", text)
        self.assertNotIn("Rule one", text)
        self.assertEqual(text.count("slipway:begin rules"), 1)

    def test_user_edits_inside_the_block_survive_until_forced(self):
        path = self.home / "CLAUDE.md"
        blocks.upsert(path, "rules", "Rule one")
        path.write_text(path.read_text().replace("Rule one", "Rule one, my way"))
        self.assertEqual(blocks.upsert(path, "rules", "Rule two").action, "edited")
        self.assertIn("my way", path.read_text())
        self.assertEqual(blocks.upsert(path, "rules", "Rule two", force=True).action, "updated")
        self.assertNotIn("my way", path.read_text())

    def test_remove_touches_only_the_block(self):
        path = self.home / "AGENTS.md"
        user = "# Mine\n\n```text\nline\n\n\n\nspaced on purpose\n```\n"
        path.write_text(user)
        blocks.upsert(path, "rules", "Rule")
        path.write_text(path.read_text() + "\n## After\n")
        self.assertEqual(blocks.remove(path, "rules").action, "removed")
        self.assertEqual(path.read_text(), user.rstrip("\n") + "\n\n## After\n")

    def test_dry_run_writes_nothing(self):
        path = self.home / "AGENTS.md"
        self.assertEqual(blocks.upsert(path, "rules", "Rule", dry_run=True).action, "created")
        self.assertFalse(path.exists())


class LinksTest(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.state = State.load(self.home / "state.json")
        self.target = self.home / "repo" / "skills" / "demo"
        self.target.mkdir(parents=True)
        (self.target / "SKILL.md").write_text("---\nname: demo\n---\n")
        self.link = self.home / ".agents" / "skills" / "demo"

    def test_creates_then_reports_ok(self):
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own").action, "created")
        self.assertTrue(self.link.is_symlink())
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own").action, "ok")

    def test_adopts_an_identical_copy_but_never_a_git_clone(self):
        self.link.mkdir(parents=True)
        (self.link / "SKILL.md").write_text("---\nname: demo\n---\n")
        (self.link / ".git").mkdir()
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own").action, "drift")
        self.assertTrue((self.link / ".git").is_dir(), "a clone with history is never deleted")
        (self.link / ".git").rmdir()
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own").action, "adopted")
        self.assertTrue(self.link.is_symlink())

    def test_keeps_a_different_user_copy_unless_forced_and_then_backs_it_up(self):
        self.link.mkdir(parents=True)
        (self.link / "SKILL.md").write_text("mine")
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own").action, "drift")
        self.assertFalse(self.link.is_symlink())
        self.assertEqual(links.ensure(self.link, self.target, self.state, "own", force=True).action, "replaced")
        self.assertEqual(list(self.link.parent.glob("demo*")), [self.link], "no backup left where harnesses load it")
        backups = list((self.home / ".local/state/slipway/backups/links").glob("skills-demo-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "SKILL.md").read_text(), "mine")

    def test_prune_removes_links_of_dropped_components_but_not_repointed_ones(self):
        links.ensure(self.link, self.target, self.state, "own")
        other = self.home / ".claude" / "skills" / "demo"
        links.ensure(other, self.target, self.state, "own")
        other.unlink()
        other.symlink_to(self.home)  # user re-pointed it
        removed = links.prune(self.state, components=set())
        self.assertEqual([r.link for r in removed], [self.link])
        self.assertFalse(self.link.exists())
        self.assertTrue(other.is_symlink())
        self.assertEqual(self.state.section("links"), {})


if __name__ == "__main__":
    unittest.main()
