"""The 1 s state poll reuses the transfer notice only while nothing changed."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from app.launcher.transfer import TRANSFER_MESSAGES
from app.launcher.write_control import LocalWriteController


class CountingEngine:
    def __init__(self, database):
        self.database, self.opened = database, 0

    def pending(self):
        return ()

    @contextmanager
    def _db(self):
        self.opened += 1
        connection = sqlite3.connect(self.database)
        try:
            with connection:
                yield connection
        finally:
            connection.close()


class TransferNoticeCacheTests(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.save = root / "game.sav"
        self.engine = CountingEngine(root / "engine.sqlite3")
        with self.engine._db() as db:
            db.execute("CREATE TABLE transfer_bindings (record TEXT NOT NULL)")
        self.selection = str(self.save)
        self.control = LocalWriteController(
            SimpleNamespace(recovery_required=False),
            lambda: self.selection,
            self.engine,
        )
        self.engine.opened = 0

    def bind(self, state, path):
        with self.engine._db() as db:
            db.execute(
                "INSERT INTO transfer_bindings VALUES (?)",
                (json.dumps({"state": state, "binding": {"path": path}}),),
            )

    def test_unchanged_database_and_selection_are_read_once(self):
        self.assertIsNone(self.control._transfer_notice())
        opened = self.engine.opened  # the controller may already have read it
        for _ in range(50):
            self.assertIsNone(self.control._transfer_notice())
        self.assertEqual(self.engine.opened, opened)
        self.assertLessEqual(opened, 1)

    def test_a_new_binding_is_seen_at_the_next_poll(self):
        self.assertIsNone(self.control._transfer_notice())
        self.bind("RECIPIENT_PHYSICAL_PENDING", str(self.save.absolute()))
        self.assertIsNotNone(self.control._transfer_notice())

    def test_another_selection_reads_again(self):
        self.bind("RECOVERY_REQUIRED", str(self.save.absolute()))
        self.assertEqual(
            self.control._transfer_notice(), TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
        )
        opened = self.engine.opened
        self.selection = str(self.save.with_name("other.sav"))
        # Another save still sees an open transfer, after a fresh read.
        self.assertEqual(
            self.control._transfer_notice(), TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
        )
        self.assertEqual(self.engine.opened, opened + 1)

    def test_unreadable_database_is_never_cached_as_clear(self):
        self.engine.database.unlink()
        self.engine.database.mkdir()  # sqlite cannot open a directory
        for _ in range(3):
            self.assertEqual(
                self.control._transfer_notice(),
                TRANSFER_MESSAGES["RECOVERY_REQUIRED"],
            )


if __name__ == "__main__":
    unittest.main()
