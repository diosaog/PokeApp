"""Phase 28: automatic save choice and the Launcher's web session handoff."""

import json
import os
import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock, patch

from app.launcher.discovery import emulator_saves


def save_at(root, emulator, title="00055e00"):
    ids = "0" * 32
    path = (
        root
        / emulator
        / "sdmc"
        / "Nintendo 3DS"
        / ids
        / ids
        / "title"
        / "00040000"
        / title
        / "data"
        / "00000001"
        / "main"
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(b"save")
    return path


class DiscoveryMetadataTests(unittest.TestCase):
    def test_modified_time_comes_from_stat_and_the_file_is_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            path = save_at(Path(temp), "Lime3DS")
            os.utime(path, (1_700_000_000, 1_700_000_000))
            before = path.stat()
            [found] = emulator_saves(Path(temp))
            self.assertEqual(found["modified"], 1_700_000_000)
            after = path.stat()
            self.assertEqual(path.read_bytes(), b"save")
            self.assertEqual(
                (before.st_mtime_ns, before.st_size),
                (after.st_mtime_ns, after.st_size),
            )


class SaveChoiceTests(unittest.TestCase):
    def runtime(self):
        from app.launcher.runtime import LauncherRuntime

        temp = tempfile.TemporaryDirectory(prefix="pokeapp-28-")
        self.addCleanup(temp.cleanup)
        runtime = LauncherRuntime(
            Path(temp.name),
            Mock(),
            client=Mock(origin="https://x.invalid"),
            token_store=Mock(),
            start=False,
        )
        return runtime

    def found(self, *names):
        return [
            {"path": f"C:/fixture/{name}/main", "emulator": "Lime3DS", "game": "Y"}
            for name in names
        ]

    def choose(self, runtime, found):
        with patch("app.launcher.discovery.emulator_saves", return_value=found):
            runtime._discover_on_start()
        return runtime.state()["save_choice"]

    def test_one_save_is_chosen_and_remembered_automatically(self):
        runtime = self.runtime()
        choice = self.choose(runtime, self.found("a"))
        self.assertEqual(choice["status"], "AUTO_SELECTED")
        self.assertEqual(
            runtime.local_commands.get_nowait(),
            ("select", {"path": "C:/fixture/a/main"}),
        )

    def test_several_saves_ask_and_select_nothing(self):
        runtime = self.runtime()
        choice = self.choose(runtime, self.found("a", "b"))
        self.assertEqual((choice["status"], choice["count"]), ("CHOOSE", 2))
        self.assertTrue(runtime.local_commands.empty())

    def test_no_save_is_an_empty_state(self):
        runtime = self.runtime()
        self.assertEqual(self.choose(runtime, [])["status"], "NONE")
        self.assertTrue(runtime.local_commands.empty())

    def test_remembered_save_is_never_replaced_and_new_ones_are_announced(self):
        runtime = self.runtime()
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": "C:/fixture/a/main"}
        )
        # First run sets the baseline: nothing is "new" yet.
        first = self.choose(runtime, self.found("a", "b"))
        self.assertEqual(
            (first["status"], first["count"], first["new"]), ("KEPT", 1, 0)
        )
        later = self.choose(runtime, self.found("a", "b", "c"))
        self.assertEqual(
            (later["status"], later["count"], later["new"]), ("KEPT", 2, 1)
        )
        self.assertTrue(runtime.local_commands.empty())
        self.assertEqual(runtime.core.config.selected_save, "C:/fixture/a/main")
        # The memory holds path hashes only, never paths.
        stored = (runtime.core.profile / "known-saves.json").read_text("utf-8")
        self.assertNotIn("fixture", stored)
        self.assertEqual(len(json.loads(stored)), 3)

    def test_manual_search_with_a_save_selected_keeps_it(self):
        runtime = self.runtime()
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": "C:/fixture/a/main"}
        )
        with patch(
            "app.launcher.discovery.emulator_saves",
            return_value=self.found("a", "b"),
        ):
            result = runtime.command("discover_saves", {})
        self.assertEqual(result, {"status": "DONE", "count": 2, "auto_selected": False})
        self.assertEqual(runtime.state()["save_choice"]["status"], "KEPT")
        self.assertTrue(runtime.local_commands.empty())


class WebSessionTests(unittest.TestCase):
    def runtime(self):
        from app.launcher.runtime import LauncherRuntime

        temp = tempfile.TemporaryDirectory(prefix="pokeapp-28-")
        self.addCleanup(temp.cleanup)
        return LauncherRuntime(
            Path(temp.name),
            Mock(),
            client=Mock(origin="https://x.invalid"),
            token_store=Mock(),
            start=False,
        )

    def test_without_session_the_web_must_sign_in(self):
        runtime = self.runtime()
        runtime.session._principal = None
        self.assertEqual(
            runtime.command("web_session", {}), {"status": "LOGIN_REQUIRED"}
        )

    def test_fresh_access_token_only_and_never_in_state(self):
        runtime = self.runtime()
        runtime._web_token = {
            "access_token": "access-1",
            "expires_at": int(time.time()) + 900,
            "trainer_id": "t1",
        }
        reply = runtime.command("web_session", {})
        self.assertEqual(reply["status"], "OK")
        self.assertEqual(
            set(reply), {"status", "access_token", "expires_at", "trainer_id"}
        )
        self.assertNotIn("access-1", json.dumps(runtime.state()))

    def test_near_expiry_asks_the_core_to_refresh(self):
        runtime = self.runtime()
        runtime.session._principal = {"trainer_id": "t1"}
        runtime._web_token = {
            "access_token": "old",
            "expires_at": int(time.time()) + 60,
            "trainer_id": "t1",
        }
        self.assertEqual(runtime.command("web_session", {}), {"status": "PENDING"})
        self.assertTrue(runtime._web_token_wanted)
        with self.assertRaises(ValueError):
            runtime.command("web_session", {"token": "x"})

    def test_logout_withdraws_the_web_session_at_once(self):
        runtime = self.runtime()
        runtime.session._principal = {"trainer_id": "t1"}
        runtime._web_token = {
            "access_token": "access-1",
            "expires_at": int(time.time()) + 900,
            "trainer_id": "t1",
        }
        # Queued for the cloud loop, but the web is refused right now.
        self.assertEqual(runtime.command("logout", {}), {"status": "QUEUED"})
        self.assertEqual(
            runtime.command("web_session", {}), {"status": "LOGIN_REQUIRED"}
        )
        self.assertIsNone(runtime._web_token)


class AutomaticSyncTests(unittest.TestCase):
    """The selected save reaches the outbox only when stable, once per content,
    for the signed-in trainer, and never after logout."""

    ORIGIN = "https://pokeapp.example"
    SEASON = "22222222-2222-4222-8222-222222222222"
    TRAINER = "11111111-1111-4111-8111-111111111111"
    OTHER = "33333333-3333-4333-8333-333333333333"

    def setUp(self):
        from phase9_fixtures import observed

        from app.launcher.journal import LocalReceipt
        from app.launcher.runtime import LauncherRuntime
        from app.save_parser.models import SaveFingerprint

        temp = tempfile.TemporaryDirectory(prefix="pokeapp-28-sync-")
        self.addCleanup(temp.cleanup)
        self.save = Path(temp.name) / "main"
        self.data = b"synthetic save bytes, never a personal save"
        self.save.write_bytes(self.data)
        self.runtime = LauncherRuntime(
            Path(temp.name) / "profile",
            Mock(),
            client=Mock(origin=self.ORIGIN),
            token_store=Mock(),
            start=False,
        )
        self.receipt = lambda data: LocalReceipt(
            "fixture",
            1,
            SaveFingerprint(sha256=sha256(data).hexdigest(), size=len(data)),
            "pokeapp-reader/3;pkhex/24.11.11",
            observed(),
        )
        self.runtime.receipt = self.receipt(self.data)
        self.runtime._patch(
            selected_save=str(self.save),
            local_status="READY",
            principal={"trainer_id": self.TRAINER, "display_name": "Fixture"},
            cloud={"data": {"season": {"id": self.SEASON}}},
            cloud_sync=self.runtime._auto_consent(self.TRAINER),
        )

    def pending(self):
        return self.runtime.store.summary(self.ORIGIN, self.TRAINER)["pending"]

    def test_first_trainer_signing_in_syncs_automatically(self):
        self.assertTrue(self.runtime.state()["cloud_sync"])
        self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 1)

    def test_without_an_active_season_the_save_goes_to_the_personal_record(self):
        # It used to wait forever («Pendiente · Se enviará en un momento»).
        self.runtime._patch(cloud={"data": {"season": None}})
        self.runtime._enqueue_local()
        row = self.runtime.store.pending(self.ORIGIN, self.TRAINER)
        self.assertEqual((self.pending(), row["season"]), (1, "personal"))

    def test_before_the_first_cloud_answer_nothing_is_queued(self):
        # Until PokeApp says whether a season is active, the scope is unknown.
        self.runtime._patch(cloud=None)
        self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 0)

    def test_same_content_is_queued_once(self):
        for _ in range(3):
            self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 1)

    def test_new_content_replaces_the_unsent_snapshot(self):
        self.runtime._enqueue_local()
        changed = self.data + b" after a save in game"
        self.save.write_bytes(changed)
        self.runtime.receipt = self.receipt(changed)
        self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 1)
        row = self.runtime.store.pending(self.ORIGIN, self.TRAINER)
        self.assertEqual(row["id"], sha256(changed).hexdigest())

    def test_bytes_changing_during_the_read_are_never_queued(self):
        # The emulator is writing: the bytes no longer match the stable read.
        self.save.write_bytes(self.data[:10])
        self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 0)
        state = self.runtime.state()
        self.assertEqual(
            (state["local_status"], state["error"]),
            ("READING", "SAVE_CHANGED_DURING_READ"),
        )

    def test_after_logout_nothing_is_queued(self):
        self.runtime._patch(cloud_sync=False, principal=None)
        self.runtime._enqueue_local()
        self.assertEqual(self.pending(), 0)

    def test_signing_in_is_the_consent_also_on_a_shared_pc(self):
        # Owner decision 2026-10-28: there is no manual sync. The server still
        # refuses another in-game trainer's save for a season.
        self.assertTrue(self.runtime._auto_consent(self.OTHER))
        self.assertTrue(self.runtime.store.enabled(self.ORIGIN, self.OTHER))
        self.assertTrue(self.runtime._auto_consent(self.TRAINER))


if __name__ == "__main__":
    unittest.main()
