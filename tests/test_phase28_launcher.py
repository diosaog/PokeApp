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

    def report(self, found):
        return {"checked": [], "found": len(found), "at": 0}

    def remember(self, runtime):
        """A remembered save that really exists on disk."""
        path = runtime.core.profile / "remembered" / "main"
        path.parent.mkdir()
        path.write_bytes(b"save")
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": str(path)}
        )
        return [{"path": str(path), "emulator": "Lime3DS", "game": "Y"}]

    def choose(self, runtime, found):
        with patch(
            "app.launcher.discovery.discover_emulator_saves",
            return_value=(found, self.report(found)),
        ):
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
        mine = self.remember(runtime)
        # First run sets the baseline: nothing is "new" yet.
        first = self.choose(runtime, mine + self.found("b"))
        self.assertEqual(
            (first["status"], first["count"], first["new"]), ("KEPT", 1, 0)
        )
        later = self.choose(runtime, mine + self.found("b", "c"))
        self.assertEqual(
            (later["status"], later["count"], later["new"]), ("KEPT", 2, 1)
        )
        self.assertTrue(runtime.local_commands.empty())
        self.assertEqual(runtime.core.config.selected_save, mine[0]["path"])
        # The memory holds path hashes only, never paths.
        stored = (runtime.core.profile / "known-saves.json").read_text("utf-8")
        self.assertNotIn("fixture", stored)
        self.assertEqual(len(json.loads(stored)), 3)

    def test_a_remembered_file_that_is_gone_is_said_plainly(self):
        # Renamed, moved or deleted: the trainer is told instead of a silent
        # read failure, and nothing is chosen in their place.
        runtime = self.runtime()
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": "C:/fixture/gone/main"}
        )
        choice = self.choose(runtime, self.found("b"))
        self.assertEqual((choice["status"], choice["count"]), ("MISSING", 1))
        self.assertTrue(runtime.local_commands.empty())

    def test_manual_search_with_a_save_selected_keeps_it(self):
        runtime = self.runtime()
        found = self.remember(runtime) + self.found("b")
        with patch(
            "app.launcher.discovery.discover_emulator_saves",
            return_value=(found, self.report(found)),
        ):
            result = runtime.command("discover_saves", {})
        # The answer itself carries the list and what was checked, so the
        # selector never opens on an older state poll.
        self.assertEqual(
            (result["status"], result["count"], result["auto_selected"]),
            ("DONE", 2, False),
        )
        self.assertEqual(result["saves"], found)
        self.assertEqual(result["discovery"], self.report(found))
        self.assertEqual(result["save_choice"]["status"], "KEPT")
        self.assertEqual(runtime.state()["save_choice"]["status"], "KEPT")
        self.assertEqual(runtime.state()["discovery"], self.report(found))
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

    def scopes(self):
        with self.runtime.store.journal.connection() as db:
            return sorted(
                (r["season"], r["id"])
                for r in db.execute(
                    "SELECT season,id FROM trusted_save_outbox WHERE verified=0 AND blocked=0"
                )
            )

    def test_first_trainer_signing_in_syncs_automatically(self):
        # The selected save is the active save everywhere: personal record
        # and, while it is the season's save, the active season too.
        self.assertTrue(self.runtime.state()["cloud_sync"])
        self.runtime._enqueue_local()
        digest = sha256(self.data).hexdigest()
        self.assertEqual(
            self.scopes(), sorted([("personal", digest), (self.SEASON, digest)])
        )

    def test_a_season_bound_to_another_game_keeps_it_and_personal_still_syncs(self):
        # The friend's case: «Prueba» uses their Sun save, the Launcher has Y.
        self.runtime._patch(
            cloud={
                "data": {
                    "season": {"id": self.SEASON},
                    "season_link": {
                        "status": "BOUND",
                        "game": "SN",
                        "identity": {"game": "SN", "trainer": {"name": "Other"}},
                    },
                }
            }
        )
        self.runtime._enqueue_local()
        self.assertEqual(
            self.scopes(), [("personal", sha256(self.data).hexdigest())]
        )

    def test_a_season_this_trainer_does_not_play_never_receives_the_save(self):
        self.runtime._patch(
            cloud={
                "data": {
                    "season": {"id": self.SEASON},
                    "season_link": {"status": "NOT_PARTICIPANT"},
                }
            }
        )
        self.runtime._enqueue_local()
        self.assertEqual([s for s, _ in self.scopes()], ["personal"])

    def test_the_same_save_already_bound_keeps_syncing_to_the_season(self):
        from app.launcher.runtime import save_identity

        self.runtime._patch(
            cloud={
                "data": {
                    "season": {"id": self.SEASON},
                    "season_link": {
                        "status": "BOUND",
                        "identity": save_identity(self.runtime.receipt),
                    },
                }
            }
        )
        self.runtime._enqueue_local()
        self.assertEqual(
            [s for s, _ in self.scopes()], sorted(["personal", self.SEASON])
        )

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
        self.assertEqual(self.pending(), 2)  # one per scope, never repeated

    def test_new_content_replaces_the_unsent_snapshot(self):
        self.runtime._enqueue_local()
        changed = self.data + b" after a save in game"
        self.save.write_bytes(changed)
        self.runtime.receipt = self.receipt(changed)
        self.runtime._enqueue_local()
        digest = sha256(changed).hexdigest()
        self.assertEqual(
            self.scopes(), sorted([("personal", digest), (self.SEASON, digest)])
        )

    def test_a_queued_change_wakes_the_cloud_loop_at_once(self):
        self.runtime._cloud_wake.clear()
        self.runtime._enqueue_local()
        self.assertTrue(self.runtime._cloud_wake.is_set())
        self.runtime._cloud_wake.clear()
        self.runtime._enqueue_local()  # nothing new: no wake-up
        self.assertFalse(self.runtime._cloud_wake.is_set())

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
