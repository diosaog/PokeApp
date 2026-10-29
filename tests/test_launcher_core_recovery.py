"""Friend's Launcher (2026-10-29): «Sin conexión» and «El núcleo del Launcher
está tardando en responder» on another PC while the account showed signed in.

Root causes pinned here, all reproduced on this machine:
- the previous core keeps the profile lock for 15-90 s after its window closes
  (a network request in flight); the next core died at once on
  LAUNCHER_ALREADY_RUNNING and the shell never started another one;
- any startup error ended the core the same way (an unreadable config.json);
- the core trusted only its bundled CA list: an antivirus or proxy that scans
  HTTPS left it offline while the web (Windows certificate store) worked;
- `state` waited behind the backup verification and the emulator search.
"""

import io
import json
import os
import ssl
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import certifi
import httpx

from app.launcher import stdio
from app.launcher.backend import (
    BackendClient,
    BackendError,
    LauncherSession,
    SessionTokens,
    tls_context,
)
from app.launcher.core import LauncherCore, LauncherLease
from app.launcher.diagnostics import failure, mask
from app.launcher.journal import LocalConflict
from app.launcher.runtime import LauncherRuntime
from app.launcher.write_control import LocalWriteController

ORIGIN = "https://pokeapp.example"
TRAINER = "11111111-1111-4111-8111-111111111111"


def profile_dir(test):
    temp = tempfile.TemporaryDirectory(prefix="pokeapp-core-recovery-")
    test.addCleanup(temp.cleanup)
    return Path(temp.name)


class LeaseTests(unittest.TestCase):
    def test_a_held_profile_is_waited_for_and_taken_over(self):
        root = profile_dir(self)
        first = LauncherLease(root).__enter__()
        told = []

        def sleep(_seconds):
            # The previous core finishes while the new one waits.
            first.__exit__(None, None, None)

        second = LauncherLease(
            root, wait=5, on_wait=lambda: told.append(1), sleep=sleep
        ).__enter__()
        self.addCleanup(second.__exit__, None, None, None)
        self.assertEqual(told, [1])
        self.assertIsNotNone(second.stream)

    def test_without_waiting_or_after_the_wait_it_still_refuses(self):
        root = profile_dir(self)
        first = LauncherLease(root).__enter__()
        self.addCleanup(first.__exit__, None, None, None)
        with self.assertRaises(LocalConflict) as caught:
            LauncherLease(root).__enter__()
        self.assertEqual(str(caught.exception), "LAUNCHER_ALREADY_RUNNING")
        with self.assertRaises(LocalConflict):
            LauncherLease(root, wait=0.3, sleep=lambda s: time.sleep(0.05)).__enter__()


class StartupTests(unittest.TestCase):
    def run_main(self, root, **patches):
        out = io.StringIO()
        argv = ["stdio", "--parser", str(root / "missing-parser.exe"), "--profile", str(root)]
        # No real network and no real emulator folders in a unit test.
        client = Mock(origin=ORIGIN)
        client.json.side_effect = BackendError("BACKEND_UNAVAILABLE")
        with patch.object(sys, "argv", argv), patch.object(sys, "stdout", out), patch.object(
            sys, "stdin", io.StringIO('{"id": 1, "command": "state"}\n')
        ), patch.object(stdio, "BackendClient", return_value=client), patch(
            "app.launcher.discovery.discover_emulator_saves", return_value=([], None)
        ), patch.multiple(stdio, **(patches or {"LEASE_WAIT_SECONDS": stdio.LEASE_WAIT_SECONDS})):
            code = stdio.main()
        return code, [json.loads(line) for line in out.getvalue().splitlines()]

    def test_a_ready_core_says_so_before_answering(self):
        root = profile_dir(self)
        code, lines = self.run_main(root)
        self.assertEqual(code, 0)
        self.assertEqual([l.get("status") for l in lines[:2]], ["STARTING", "READY"])
        self.assertEqual(lines[2]["id"], 1)
        self.assertIn("cloud_status", lines[2]["result"])
        log = (root / "logs" / "core.log").read_text(encoding="utf-8")
        self.assertIn("READY in", log)

    def test_a_profile_never_released_ends_with_a_reason_not_silence(self):
        root = profile_dir(self)
        held = LauncherLease(root).__enter__()
        self.addCleanup(held.__exit__, None, None, None)
        code, lines = self.run_main(root, LEASE_WAIT_SECONDS=0.3)
        self.assertEqual(code, stdio.EXIT_ALREADY_RUNNING)
        self.assertEqual(lines[-1], {"event": "core", "status": "FATAL", "code": "LAUNCHER_ALREADY_RUNNING"})

    def test_a_runtime_that_cannot_start_reports_its_code(self):
        root = profile_dir(self)
        import sqlite3

        with patch.object(stdio, "LauncherRuntime", side_effect=sqlite3.DatabaseError("file is not a database")):
            code, lines = self.run_main(root)
        self.assertEqual(code, stdio.EXIT_STARTUP_FAILED)
        self.assertEqual(lines[-1]["code"], "LOCAL_DATA_UNREADABLE")
        self.assertIn("FATAL LOCAL_DATA_UNREADABLE", (root / "logs" / "core.log").read_text(encoding="utf-8"))

    def test_startup_codes(self):
        self.assertEqual(stdio.startup_code(LocalConflict("LAUNCHER_ALREADY_RUNNING")), "LAUNCHER_ALREADY_RUNNING")
        self.assertEqual(stdio.startup_code(ValueError("unsupported_local_schema")), "LOCAL_DATA_UNREADABLE")
        self.assertEqual(stdio.startup_code(PermissionError(13, "denied")), "PROFILE_ACCESS_DENIED")
        self.assertEqual(stdio.startup_code(ValueError("local_directory_required")), "PROFILE_UNAVAILABLE")
        self.assertEqual(stdio.startup_code(RuntimeError("x")), "STARTUP_FAILED")

    def test_an_unreadable_config_is_set_aside_not_fatal(self):
        root = profile_dir(self)
        (root / "config.json").write_bytes(b'{"schema_version": 1, "selected_save": ')
        core = LauncherCore(root, Mock())
        self.assertTrue(core.config_reset)
        self.assertIsNone(core.config.selected_save)
        kept = list(root.glob("config.invalid-*.json"))
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].read_bytes(), b'{"schema_version": 1, "selected_save": ')


class PipeTests(unittest.TestCase):
    def test_state_answers_while_the_emulator_search_runs(self):
        release = threading.Event()
        runtime = Mock()

        def command(name, args):
            if name == "discover_saves":
                release.wait(5)
                return {"status": "DONE"}
            return {"status": "STATE"}

        runtime.command.side_effect = command
        out = io.StringIO()
        pipe = stdio.Pipe(out)
        lines = [
            '{"id": 1, "command": "discover_saves"}\n',
            '{"id": 2, "command": "discover_saves"}\n',
            '{"id": 3, "command": "state"}\n',
        ]
        stdio.serve(runtime, lines, pipe)
        answers = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(answers[0], {"id": 2, "result": {"status": "BUSY"}})
        self.assertEqual(answers[1], {"id": 3, "result": {"status": "STATE"}})
        release.set()
        deadline = time.monotonic() + 5
        while len(out.getvalue().splitlines()) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(json.loads(out.getvalue().splitlines()[2]), {"id": 1, "result": {"status": "DONE"}})

    def test_backup_verification_never_blocks_the_state_poll(self):
        started, release = threading.Event(), threading.Event()
        engine = Mock()
        engine.pending.return_value = ()
        engine.database.stat.side_effect = OSError

        def slow(_selected):
            started.set()
            release.wait(5)
            return []

        engine.backups_for.side_effect = slow
        gate = Mock()
        gate.recovery_required = False
        gate.writing.return_value.__enter__ = Mock(return_value=None)
        gate.writing.return_value.__exit__ = Mock(return_value=False)
        controller = LocalWriteController(gate, lambda: "C:/save/main", engine)
        controller._transfer_notice = lambda: None
        worker = threading.Thread(target=controller.refresh_backups)
        worker.start()
        self.assertTrue(started.wait(5))
        began = time.monotonic()
        state = controller.state()
        self.assertLess(time.monotonic() - began, 1)
        self.assertTrue(state["busy"])
        release.set()
        worker.join(5)


class ShutdownTests(unittest.TestCase):
    def test_closing_does_not_wait_for_a_hung_network_request(self):
        root = profile_dir(self)
        hung = threading.Event()
        client = Mock(origin=ORIGIN)
        client.json.side_effect = lambda *a, **k: hung.wait(30)
        runtime = LauncherRuntime(root / "profile", Mock(), client=client, token_store=Mock())
        deadline = time.monotonic() + 5
        while not client.json.called and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(client.json.called)
        began = time.monotonic()
        runtime.close()
        self.assertLess(time.monotonic() - began, 6)
        self.assertFalse(runtime.threads[0].is_alive())
        client.close.assert_not_called()
        hung.set()


class TrustTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows certificate store")
    def test_the_windows_store_is_trusted_with_the_bundled_roots(self):
        bundled = {
            ssl.PEM_cert_to_DER_cert(block[block.index("-----BEGIN") :])
            for block in Path(certifi.where()).read_text().split("\n\n")
            if "BEGIN CERTIFICATE" in block
        }
        windows_only = [
            der
            for der, encoding, trust in ssl.enum_certificates("ROOT")
            if encoding == "x509_asn"
            and der not in bundled
            and (trust is True or "1.3.6.1.5.5.7.3.1" in trust)
        ]
        context = tls_context()
        loaded = set(context.get_ca_certs(binary_form=True))
        self.assertTrue(bundled <= loaded)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        if windows_only:  # e.g. an antivirus root on this PC
            self.assertTrue(set(windows_only) & loaded)

    def test_a_certificate_failure_is_named_without_its_text(self):
        self.assertEqual(
            failure(httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed")),
            "TLS_UNTRUSTED",
        )
        self.assertEqual(failure(httpx.ConnectTimeout("t")), "ConnectTimeout")

    def test_transport_failures_keep_their_kind(self):
        def refuse(request):
            raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

        client = BackendClient(ORIGIN, transport=httpx.MockTransport(refuse))
        self.addCleanup(client.close)
        with self.assertRaises(BackendError) as caught:
            client.json("GET", "/health")
        self.assertEqual((str(caught.exception), caught.exception.cause), ("BACKEND_UNAVAILABLE", "TLS_UNTRUSTED"))

    def test_the_cloud_loop_shows_the_cause_and_logs_it_once(self):
        root = profile_dir(self)
        log = Mock()
        runtime = LauncherRuntime(
            root / "profile", Mock(), client=Mock(origin=ORIGIN), token_store=Mock(), start=False, log=log
        )
        runtime.session = Mock(_principal=object())
        runtime.stop = Mock()
        runtime.stop.wait.side_effect = [False, False, True]
        runtime._cloud_step = Mock(side_effect=[BackendError("BACKEND_UNAVAILABLE", cause="TLS_UNTRUSTED")] * 2)
        with patch("app.launcher.runtime.time.monotonic", side_effect=iter(range(0, 50000, 1000))):
            runtime._cloud_loop()
        state = runtime.state()
        self.assertEqual((state["error"], state["error_cause"], state["cloud_status"]), ("BACKEND_UNAVAILABLE", "TLS_UNTRUSTED", "OFFLINE"))
        self.assertEqual(log.warning.call_count, 1)


class SessionRenewalTests(unittest.TestCase):
    def session(self, me, refresh):
        client = Mock()
        client.me.side_effect = me
        client.refresh.side_effect = refresh
        session = LauncherSession(client)
        session._tokens = SessionTokens(
            user_id="u", access_token="old", refresh_token="r", expires_at=int(time.time()) + 3000
        )
        session._principal = Mock(trainer_id=TRAINER)
        return session, client

    def test_a_token_the_server_already_expired_is_renewed_once(self):
        principal = Mock(trainer_id=TRAINER, globally_enabled=True)
        session, client = self.session(
            [BackendError("SESSION_REJECTED", status=401), principal],
            [SessionTokens(user_id="u", access_token="new", refresh_token="r2", expires_at=int(time.time()) + 3600)],
        )
        self.assertIs(session.principal(), principal)
        self.assertEqual(session._tokens.access_token, "new")
        self.assertEqual(client.refresh.call_count, 1)

    def test_a_refused_renewal_still_ends_the_session(self):
        session, client = self.session(
            [BackendError("SESSION_REJECTED", status=401)],
            [BackendError("SESSION_REJECTED", status=401)],
        )
        with self.assertRaises(BackendError):
            session.principal()
        self.assertIsNone(session._principal)

    def test_a_network_failure_keeps_the_session(self):
        session, client = self.session(
            [BackendError("BACKEND_UNAVAILABLE", cause="ConnectTimeout")], []
        )
        with self.assertRaises(BackendError):
            session.principal()
        self.assertIsNotNone(session._principal)
        client.refresh.assert_not_called()


class MaskTests(unittest.TestCase):
    def test_the_user_folder_and_name_never_reach_the_log(self):
        with patch.dict(os.environ, {"USERPROFILE": r"C:\Users\Jesús López", "USERNAME": "Jesús López"}):
            text = mask(r"FileNotFoundError: C:\Users\Jesús López\AppData\Local\PokeApp\x and jesús lópez")
        self.assertNotIn("Jesús", text)
        self.assertIn("%USERPROFILE%", text)
        self.assertIn("<usuario>", text)


if __name__ == "__main__":
    unittest.main()
