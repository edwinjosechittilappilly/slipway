"""Before changing anything, Slipway snapshots the config files it may touch, and keeps only the newest few."""

import tarfile
from unittest import mock

from support import HomeTestCase

from slipway import backup


class BackupTest(HomeTestCase):
    def test_snapshot_contains_existing_config_and_rotates(self):
        claude = self.home / ".claude" / "CLAUDE.md"
        claude.parent.mkdir()
        claude.write_text("my rules")
        target = backup.snapshot()
        with tarfile.open(target) as tar:
            self.assertEqual(tar.getnames(), [".claude/CLAUDE.md"])
            self.assertEqual(tar.extractfile(".claude/CLAUDE.md").read(), b"my rules")

        for i in range(backup.KEEP + 2):
            with mock.patch("slipway.backup.now", return_value=f"2026-01-0{i}T00:00:00Z"):
                backup.snapshot()
        self.assertEqual(len(list(target.parent.glob("backup-*.tar.gz"))), backup.KEEP)

    def test_nothing_to_save_writes_nothing(self):
        self.assertIsNone(backup.snapshot())
