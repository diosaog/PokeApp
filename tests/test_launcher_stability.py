"""Real-test incidents (2026-10-28): sessions, unattended sync, discovery.

Each class pins one root cause found in the owner's and a friend's Launchers:
a 403 on a season the trainer does not play signed the Launcher out; one
failed item preparation paused every read until a restart; the selector and
search results disappeared within a second; discovery only knew %APPDATA%.
"""

import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from phase9_fixtures import observed

from app.launcher.backend import BackendClient, BackendError, LauncherSession
from app.launcher.journal import LocalReceipt
from app.launcher.runtime import PERSONAL, LauncherRuntime, save_identity
from app.launcher.stdio import error_code
from app.launcher.write_files import WriteSafetyError
from app.save_parser.models import SaveFingerprint

ORIGIN = "https://pokeapp.example"
SEASON = "22222222-2222-4222-8222-222222222222"
TRAINER = "11111111-1111-4111-8111-111111111111"
VERSION = "pokeapp-reader/3;pkhex/24.11.11"


def answer(status, code=None):
    body = {"detail": {"code": code, "message": "x"}} if code else {}
    return httpx.Response(status, json=body)


class RefusalIsNotSignOutTests(unittest.TestCase):
    """401 ends the session; 403 is a refusal of one resource."""

    def client(self, response):
        client = BackendClient(
            ORIGIN, transport=httpx.MockTransport(lambda request: response)
        )
        self.addCleanup(client.close)
        return client

    def test_season_save_refusal_is_forbidden_with_the_api_reason(self):
        client = self.client(answer(403, "SAVE_REQUEST_REJECTED"))
        with self.assertRaises(BackendError) as caught:
            client.json("GET", f"/v1/seasons/{SEASON}/saves/context", token="t")
        self.assertEqual(
            (str(caught.exception), caught.exception.status, caught.exception.detail),
            ("FORBIDDEN", 403, "SAVE_REQUEST_REJECTED"),
        )

    def test_only_401_and_a_disabled_account_end_the_session(self):
        for response, code in (
            (answer(401, "INVALID_SESSION"), "SESSION_REJECTED"),
            (answer(403, "TRAINER_DISABLED"), "ACCOUNT_DISABLED"),
            (answer(403, "ADMIN_REQUIRED"), "FORBIDDEN"),
            (answer(429), "RATE_LIMITED"),
            (answer(409, "SAVE_TRAINER_MISMATCH"), "OBSERVATION_REJECTED"),
            (answer(503), "BACKEND_UNAVAILABLE"),
        ):
            with self.assertRaises(BackendError) as caught:
                self.client(response).json("GET", "/v1/me/pc", token="t")
            self.assertEqual(str(caught.exception), code)

    def test_upload_keeps_the_reason_and_a_busy_parser_is_transient(self):
        client = self.client(answer(409, "SAVE_TRAINER_MISMATCH"))
        with self.assertRaises(BackendError) as caught:
            client.upload(f"/v1/seasons/{SEASON}/saves/raw?x=1", b"b", "t")
        self.assertEqual(
            (str(caught.exception), caught.exception.detail),
            ("SAVE_REJECTED", "SAVE_TRAINER_MISMATCH"),
        )
        with self.assertRaises(BackendError) as caught:
            self.client(answer(429, "SAVE_PARSER_BUSY")).upload(
                "/v1/me/save/raw?x=1", b"b", "t"
            )
        self.assertEqual(str(caught.exception), "RATE_LIMITED")

    def test_session_survives_a_forbidden_resource(self):
        session = LauncherSession(Mock())
        session._tokens, session._principal = Mock(), Mock()
        session.client.json.side_effect = BackendError("FORBIDDEN", status=403)
        with self.assertRaises(BackendError):
            session.request("GET", "/v1/read/seasons/x/shop")
        self.assertIsNotNone(session._principal)


class Harness(unittest.TestCase):
    def runtime(self, **kwargs):
        temp = tempfile.TemporaryDirectory(prefix="pokeapp-stability-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        runtime = LauncherRuntime(
            self.root / "profile",
            Mock(),
            client=Mock(origin=ORIGIN),
            token_store=Mock(),
            start=False,
            **kwargs,
        )
        return runtime

    def ready(self, runtime, data=b"synthetic save bytes"):
        save = self.root / "main"
        save.write_bytes(data)
        runtime.receipt = LocalReceipt(
            "fixture",
            1,
            SaveFingerprint(sha256=sha256(data).hexdigest(), size=len(data)),
            VERSION,
            observed(),
        )
        runtime._patch(
            selected_save=str(save),
            local_status="READY",
            principal={"trainer_id": TRAINER, "display_name": "Fixture"},
            cloud_sync=runtime._auto_consent(TRAINER),
        )
        return save


class CloudLoopSessionTests(Harness):
    def loop(self, runtime, errors):
        runtime.stop = Mock()
        runtime.stop.wait.side_effect = [False] * len(errors) + [True]
        runtime._cloud_step = Mock(side_effect=errors)
        with patch(
            "app.launcher.runtime.time.monotonic",
            side_effect=iter(range(0, 50000, 1000)),
        ):
            runtime._cloud_loop()

    def test_a_forbidden_season_never_signs_the_launcher_out(self):
        runtime = self.runtime()
        runtime.session = Mock(_principal=object())
        self.loop(runtime, [BackendError("FORBIDDEN", status=403)])
        runtime.session.logout.assert_not_called()
        runtime.tokens.clear.assert_not_called()
        self.assertEqual(runtime.state()["error"], "FORBIDDEN")

    def test_a_rejected_session_signs_out_and_withdraws_the_web_token(self):
        runtime = self.runtime()
        runtime.session = Mock(_principal=None)
        runtime._web_token = {"access_token": "a", "expires_at": 1, "trainer_id": "t"}
        self.loop(runtime, [BackendError("SESSION_REJECTED", status=401)])
        runtime.session.logout.assert_called_once()
        runtime.tokens.clear.assert_called_once()
        self.assertIsNone(runtime._web_token)
        self.assertEqual(runtime.state()["auth_status"], "LOGIN_REQUIRED")

    def test_one_slow_answer_is_not_offline_two_in_a_row_are(self):
        runtime = self.runtime()
        runtime.session = Mock(_principal=object())
        runtime._patch(cloud_status="ONLINE", last_online=time.time())
        self.loop(runtime, [BackendError("BACKEND_UNAVAILABLE")])
        self.assertEqual(runtime.value["cloud_status"], "ONLINE")
        self.loop(runtime, [BackendError("BACKEND_UNAVAILABLE")] * 2)
        self.assertEqual(runtime.value["cloud_status"], "OFFLINE")

    def test_the_web_token_request_wakes_the_cloud_loop(self):
        runtime = self.runtime()
        runtime.session._principal = Mock()
        runtime._cloud_wake.clear()
        self.assertEqual(runtime.command("web_session", {}), {"status": "PENDING"})
        self.assertTrue(runtime._cloud_wake.is_set())

    def test_a_wake_runs_the_step_now_instead_of_in_30_s(self):
        runtime = self.runtime()
        runtime.session = Mock(_principal=object())
        calls = []
        runtime._cloud_step = Mock(side_effect=lambda: calls.append(1))
        turns = iter([False, False, False, True])

        class Stop:
            def wait(self, _seconds):
                if len(calls) == 1:
                    runtime._cloud_wake.set()  # a change queued after step 1
                return next(turns)

        runtime.stop = Stop()
        # One second per clock read: without the wake the second step would
        # wait for its 30 s turn and never run here.
        with patch(
            "app.launcher.runtime.time.monotonic", side_effect=iter(range(1000))
        ):
            runtime._cloud_loop()
        self.assertEqual(len(calls), 2)


class SeasonRefusalTests(Harness):
    """The friend: a season they do not play (or bound to another game)
    refuses the save; the personal record must still sync."""

    def test_a_refused_season_copy_does_not_block_the_personal_one(self):
        runtime = self.runtime()
        self.ready(runtime)
        runtime._patch(cloud={"data": {"season": {"id": SEASON}}})  # unknown link
        runtime._enqueue_local()
        session = Mock()
        runtime.session = session
        receipt = {
            "status": "registered",
            "save_id": TRAINER,
            "trainer_id": TRAINER,
            "season_id": PERSONAL,
            "sha256": runtime.receipt.fingerprint.sha256,
            "parser_version": VERSION,
            "observation_digest": None,
            "is_current": True,
        }
        rows = {}
        with runtime.store.journal.connection() as db:
            for row in db.execute("SELECT season,digest FROM trusted_save_outbox"):
                rows[row["season"]] = row["digest"]
        receipt["observation_digest"] = rows[PERSONAL]

        def request(method, path, **kwargs):
            if path.startswith("/v1/me/save/receipt"):
                return None
            if path == "/v1/me/save/context":
                return {"current_save_id": None}
            if path == "/v1/me/pc":
                return {"status": "ready", "save": {"id": TRAINER}}
            if path.startswith(f"/v1/seasons/{SEASON}/saves/receipt"):
                raise BackendError("FORBIDDEN", status=403, detail="SAVE_REQUEST_REJECTED")
            raise AssertionError(path)

        session.request.side_effect = request
        session.upload.return_value = receipt
        runtime._deliver_pending(TRAINER)
        state = runtime.state()
        self.assertEqual(state["cloud_receipt"]["season_id"], PERSONAL)
        self.assertEqual(state["cloud"]["data"]["season_link"]["status"], "NOT_PARTICIPANT")
        self.assertIsNone(runtime.store.pending(ORIGIN, TRAINER))
        self.assertFalse(state["syncing"])

    def test_season_link_reads_the_season_context(self):
        runtime = self.runtime()
        runtime.session = Mock()
        identity = {"game": "SN", "trainer": {"name": "Ami"}}
        for reply, expected in (
            (BackendError("FORBIDDEN", status=403), "NOT_PARTICIPANT"),
            (BackendError("OBSERVATION_REJECTED", status=409), "CLOSED"),
            ({"current_save_id": None}, "UNKNOWN"),
            ({"current_save_id": None, "save_identity": None}, "OPEN"),
            ({"current_save_id": "x", "save_identity": identity}, "BOUND"),
        ):
            runtime.session.request.side_effect = [reply]
            self.assertEqual(runtime._season_link(SEASON)["status"], expected)
        self.assertEqual(runtime._season_link.__name__, "_season_link")

    def test_robbery_steps_refuse_a_save_that_is_not_the_seasons(self):
        runtime = self.runtime()
        self.ready(runtime)
        runtime.session = Mock(_principal=Mock(trainer_id=TRAINER))
        runtime._patch(
            cloud={
                "data": {
                    "season": {"id": SEASON},
                    "season_link": {
                        "status": "BOUND",
                        "game": "SN",
                        "identity": {"game": "SN", "trainer": {}},
                    },
                }
            }
        )
        with patch("app.launcher.transfer.LauncherTransfers") as transfers:
            runtime._transfer_step("transfer_apply", {"authorization_id": "a" * 36})
        transfers.assert_not_called()
        self.assertIn("Pokémon Sol", runtime.state()["write_error"])
        self.assertNotEqual(save_identity(runtime.receipt)["game"], "SN")


class NoFreezeUntilRestartTests(Harness):
    def test_a_failed_preparation_does_not_pause_reads_and_sync(self):
        runtime = self.runtime()
        runtime.writes.engine = Mock()
        runtime.writes.engine.pending.return_value = ()
        runtime.writes._transfer_notice = Mock(return_value=None)
        runtime.writes.selected = Mock(return_value=str(self.root / "main"))
        runtime.writes.engine.files.read_path.side_effect = RuntimeError("boom")
        runtime._quick_step("quick_item_offer", {"item": "rare_candy", "quantity": 1})
        self.assertFalse(runtime.save_activity.recovery_required)
        self.assertIn("no ha cambiado", runtime.state()["quick_item_error"])

    def test_a_really_uncertain_write_still_pauses(self):
        runtime = self.runtime()
        runtime.writes.engine = Mock()
        runtime.writes.engine.pending.return_value = (Mock(status="RECOVERY_REQUIRED"),)
        runtime.writes._transfer_notice = Mock(return_value=None)
        self.assertTrue(runtime._settle_recovery())
        self.assertTrue(runtime.save_activity.recovery_required)

    def test_an_unwatched_selected_save_is_watched_again(self):
        runtime = self.runtime()
        save = self.ready(runtime)
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": str(save)}
        )
        runtime.watch = None  # as after a write that ended without a verified apply
        runtime._local_step()
        self.assertIsNotNone(runtime.watch)
        self.assertEqual(runtime.watch.poll_seconds, 1.0)
        self.assertEqual(runtime.watch.debounce_seconds, 0.75)


class OneClickItemTests(Harness):
    def engine(self, confirm_status="APPLIED_VERIFIED", error=None):
        engine = Mock()
        engine.native = Mock()
        engine.native.inventory.return_value = {
            "game": "Y",
            "trainer_key": "b" * 64,
            "source_sha256": sha256(b"save").hexdigest(),
            "items": {
                "rare_candy": {"count": 3, "max": 999, "addable": 996},
                "heart_scale": {"count": 0, "max": 999, "addable": 999},
            },
        }
        engine.files.read_path.return_value = b"save"
        engine.allows.return_value = True
        engine.status.return_value = Mock(error=error)
        return engine

    def test_apply_prepares_confirms_and_rereads_without_a_checkbox(self):
        runtime = self.runtime()
        self.assertEqual(
            runtime.command("quick_item_apply", {"item": "rare_candy", "quantity": 5}),
            {"status": "QUEUED"},
        )
        with self.assertRaises(ValueError):
            runtime.command("quick_item_apply", {"item": "nugget", "quantity": 5})
        runtime.writes.engine = self.engine()
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime.writes.offer = Mock()
        runtime.writes.state = Mock(
            return_value={"status": "AWAITING_CONFIRMATION", "operation_id": "op-1"}
        )
        runtime.writes.confirm = Mock(return_value={"status": "APPLIED_VERIFIED"})
        runtime._write_step()
        runtime.writes.offer.assert_called_once()
        runtime.writes.confirm.assert_called_once_with(
            "op-1", closed_emulator_confirmed=True
        )
        state = runtime.state()
        self.assertIsNone(state["quick_item_error"])
        self.assertEqual(
            (state["quick_item_result"]["item"], state["quick_item_result"]["quantity"]),
            ("rare_candy", 5),
        )

    def test_a_running_emulator_is_detected_and_explained(self):
        runtime = self.runtime()
        runtime.writes.engine = self.engine()
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime.writes.offer = Mock(side_effect=WriteSafetyError("EMULATOR_RUNNING"))
        runtime._quick_step("quick_item_apply", {"item": "rare_candy", "quantity": 1})
        self.assertIn("emulador está abierto", runtime.state()["quick_item_error"])
        self.assertFalse(runtime.save_activity.recovery_required)

    def test_a_locked_file_rejected_at_apply_is_explained(self):
        runtime = self.runtime()
        runtime.writes.engine = self.engine(error="FILE_LOCKED_OR_ACCESS_DENIED")
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime.writes.offer = Mock()
        runtime.writes.state = Mock(
            return_value={"status": "AWAITING_CONFIRMATION", "operation_id": "op-1"}
        )
        runtime.writes.confirm = Mock(return_value={"status": "REJECTED"})
        runtime._quick_step("quick_item_apply", {"item": "rare_candy", "quantity": 1})
        self.assertIn("otro programa", runtime.state()["quick_item_error"])


class DiscoveryCoverageTests(unittest.TestCase):
    def save(self, user_dir, title="00055e00"):
        ids = "0" * 32
        path = (
            user_dir / "sdmc" / "Nintendo 3DS" / ids / ids / "title" / "00040000"
            / title / "data" / "00000001" / "main"
        )
        path.parent.mkdir(parents=True)
        path.write_bytes(b"save")
        return path

    def test_portable_running_and_custom_storage_are_found(self):
        from app.launcher.discovery import discover_emulator_saves

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            appdata = root / "AppData"
            self.save(appdata / "Lime3DS", "00055e00")  # Y, normal install
            running = root / "Games" / "azahar-2121"
            self.save(running / "user", "00164800")  # Sun, portable, running
            desktop = root / "Desktop"
            portable = desktop / "lime3ds-2119.1-windows-msvc"
            (portable / "user" / "config").mkdir(parents=True)
            custom = root / "SD"
            self.save(custom.parent / "custom-holder", "001b5100")  # UM
            sd = custom.parent / "custom-holder" / "sdmc"
            (portable / "user" / "config" / "qt-config.ini").write_text(
                "[Data%20Storage]\nuse_custom_storage=true\n"
                f"sdmc_directory={sd.as_posix()}/\n",
                encoding="utf-8",
            )
            found, report = discover_emulator_saves(
                appdata, process_dirs=[running], portable_bases=[desktop]
            )
            self.assertEqual(
                sorted((s["emulator"], s["location"], s["game"]) for s in found),
                [
                    ("Azahar", "portable", "SN"),
                    ("Lime3DS", "appdata", "Y"),
                    ("Lime3DS", "custom", "UM"),
                ],
            )
            self.assertEqual(report["found"], 3)

    def test_an_emulator_without_supported_games_is_reported(self):
        from app.launcher.discovery import discover_emulator_saves

        with tempfile.TemporaryDirectory() as temp:
            appdata = Path(temp)
            self.save(appdata / "Citra", "00030000")  # some other 3DS title
            found, report = discover_emulator_saves(
                appdata, process_dirs=[], portable_bases=[]
            )
            self.assertEqual(found, [])
            self.assertEqual(
                report["checked"],
                [
                    {
                        "emulator": "Citra",
                        "location": "appdata",
                        "saves": 0,
                        "other_titles": 1,
                        "error": None,
                    }
                ],
            )

    def test_nothing_installed_is_an_empty_report(self):
        from app.launcher.discovery import discover_emulator_saves

        with tempfile.TemporaryDirectory() as temp:
            found, report = discover_emulator_saves(
                Path(temp), process_dirs=[], portable_bases=[]
            )
        self.assertEqual((found, report["checked"]), ([], []))


class PipeErrorCodeTests(unittest.TestCase):
    def test_refusals_keep_their_code_and_nothing_else_leaks(self):
        self.assertEqual(error_code(ValueError("invalid_selection")), "INVALID_SELECTION")
        self.assertEqual(
            error_code(ValueError("C:\\Users\\secret\\main")), "LAUNCHER_REQUEST_FAILED"
        )
        self.assertEqual(error_code(RuntimeError("boom")), "LAUNCHER_REQUEST_FAILED")
        self.assertEqual(error_code(KeyError("id")), "LAUNCHER_REQUEST_FAILED")


if __name__ == "__main__":
    unittest.main()


class SeasonContextApiTests(unittest.TestCase):
    """The API tells the trainer which save a season uses, and why it refuses."""

    def test_context_returns_the_trainers_own_bound_identity(self):
        from test_phase16d_save_sync import Repository

        from app.application.save_ingestion import TrustedSaveIngestion

        repo = Repository()
        service = TrustedSaveIngestion(repo, Mock())
        self.assertEqual(
            service.context(SEASON, TRAINER),
            {"current_save_id": None, "save_identity": None},
        )
        identity = {"game": "SN", "trainer": {"name": "Ami", "tid": 1}}
        repo.context.update(current_save_id="s1", save_identity=identity)
        self.assertEqual(
            service.context(SEASON, TRAINER),
            {"current_save_id": "s1", "save_identity": identity},
        )

    def test_sql_reasons_become_stable_public_codes(self):
        from app.repositories.supabase.save_ingestion import (
            SupabaseSaveIngestionRepository,
        )
        from app.repositories.supabase.season_admin import SeasonAdminRejected

        for message, status, code in (
            ("save_owner_required", "PT403", "SEASON_PARTICIPANT_REQUIRED"),
            ("save_identity_changed", "PT409", "SAVE_IDENTITY_CHANGED"),
            ("anything else", "PT409", "SAVE_REQUEST_REJECTED"),
        ):
            failure = Exception(message)
            failure.code, failure.message = status, message
            client = Mock()
            client.rpc.return_value.execute.side_effect = failure
            with self.assertRaises(SeasonAdminRejected) as caught:
                SupabaseSaveIngestionRepository(client).execute("context", {})
            self.assertEqual(
                (caught.exception.code, caught.exception.status),
                (code, int(status[2:])),
            )
