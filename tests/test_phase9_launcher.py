from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from app.launcher.backend import BackendClient, BackendError, LauncherSession
from app.launcher.backup import BackupService, PhysicalWritesDisabled
from app.launcher.config import LauncherConfig, backend_origin
from app.launcher.core import LauncherCore, LauncherLease
from app.launcher.discovery import FolderProvider, ManualProvider, SaveDiscoveryService
from app.launcher.journal import LocalConflict, LocalJournal, LocalOperationQueue
from app.launcher.sync import SaveSyncService, SaveWatchService
from app.save_parser.adapter import SaveInspector
from app.save_parser.files import SaveSource, SnapshotReader
from app.save_parser.models import ErrorCode, SaveError
from phase9_fixtures import FakeParser, observed, pokemon


class Phase9LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "Pokémon español.sav"
        self.path.write_bytes(b"synthetic save one")
        self.source = SaveSource.enroll(self.path)
        self.parser = FakeParser()
        self.inspector = SaveInspector(self.parser)
        self.journal = LocalJournal(self.root / "profile" / "local.sqlite3")
        self.sync = SaveSyncService(self.inspector, self.journal)

    def test_discovery_none_single_multiple_and_manual(self):
        empty = self.root / "empty"
        empty.mkdir()
        discover = SaveDiscoveryService()
        self.assertEqual(discover.discover((FolderProvider(empty),)).candidates, ())
        result = discover.discover(
            (FolderProvider(self.root), ManualProvider(self.path))
        )
        self.assertEqual(len(result.candidates), 1)
        self.path.with_name("second.dsv").write_bytes(b"candidate")
        result = discover.discover((FolderProvider(self.root),))
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(result.errors, ())
        self.assertEqual(
            discover.discover((ManualProvider(self.root / "missing.sav"),)).errors,
            ("SAVE_NOT_FOUND",),
        )

    def test_config_roundtrip_no_secrets_and_invalid_file_not_reset(self):
        config = LauncherConfig(
            selected_save=str(self.path),
            folders=(str(self.root),),
            backend_url="https://pokeapp.example/",
        )
        path = self.root / "config.json"
        config.save(path)
        self.assertEqual(config, LauncherConfig.load(path))
        self.assertEqual(config.source(), self.source)
        self.assertNotIn("token", path.read_text())
        path.write_text('{"access_token":"secret"}')
        with self.assertRaises(ValueError):
            LauncherConfig.load(path)
        self.assertEqual(path.read_text(), '{"access_token":"secret"}')

    def test_unsafe_backend_origins_rejected(self):
        for value in (
            "http://example.com",
            "https://user:pass@example.com",
            "https://x.example/path",
            "https://x.example/#secret",
        ):
            with self.assertRaises(ValueError):
                backend_origin(value)
        self.assertEqual(
            backend_origin("http://127.0.0.1:8000"), "http://127.0.0.1:8000"
        )

    def test_first_unchanged_modified_and_restart_sync(self):
        first = self.sync.sync(self.source)
        self.assertEqual(first.status, "SYNCED")
        second = self.sync.sync(self.source)
        self.assertEqual(second.status, "NO_CHANGE")
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(self.parser.calls, 1)
        restarted = SaveSyncService(self.inspector, LocalJournal(self.journal.path))
        self.assertEqual(restarted.sync(self.source).receipt_id, first.receipt_id)
        self.path.write_bytes(b"synthetic save two")
        third = restarted.sync(self.source)
        self.assertEqual(third.status, "SYNCED")
        self.assertNotEqual(third.receipt_id, first.receipt_id)
        self.assertEqual(self.journal.head(self.source).revision, 2)
        # Returning to old bytes is a new local transition, NOT proof of newer gameplay.
        self.path.write_bytes(b"synthetic save one")
        self.assertEqual(restarted.sync(self.source).status, "SYNCED")
        self.assertEqual(self.journal.head(self.source).revision, 3)

    def test_error_recovery_does_not_advance_head(self):
        first = self.sync.sync(self.source)
        self.path.write_bytes(b"changed")
        with patch.object(
            self.parser, "parse", side_effect=SaveError(ErrorCode.CORRUPT_SAVE)
        ):
            result = self.sync.sync(self.source)
        self.assertEqual(result.status, "INVALID")
        self.assertEqual(self.journal.head(self.source).id, first.receipt_id)
        self.assertEqual(self.sync.sync(self.source).status, "SYNCED")

    def test_concurrent_write_rejected_without_receipt(self):
        def parse(data):
            self.path.write_bytes(b"changed while parsing")
            return observed()

        with patch.object(self.parser, "parse", side_effect=parse):
            result = self.sync.sync(self.source)
        self.assertEqual(result.status, "CONFLICT")
        self.assertIsNone(self.journal.head(self.source))

    def test_polling_detects_change_without_event_and_coalesces_duplicates(self):
        watch = SaveWatchService(
            self.sync, self.source, poll_seconds=5, debounce_seconds=1
        )
        self.assertIsNone(watch.tick(0))
        for _ in range(10):
            watch.notify(0.1)
        self.assertIsNone(watch.tick(0.5))
        self.assertEqual(watch.tick(1).status, "SYNCED")
        for _ in range(10):
            watch.notify(1.1)
        self.assertEqual(watch.tick(2).status, "NO_CHANGE")
        self.assertEqual(self.parser.calls, 1)
        self.path.write_bytes(b"new without notification")
        self.assertIsNone(watch.tick(7))
        self.assertEqual(watch.tick(8).status, "SYNCED")
        self.assertEqual(self.parser.calls, 2)

    def test_journal_cas_and_same_input_race_independent_connections(self):
        snapshot = SnapshotReader().read(self.source)
        barrier = threading.Barrier(2)

        def record():
            journal = LocalJournal(self.journal.path)
            barrier.wait()
            return journal.record(
                self.source,
                expected=None,
                fingerprint=snapshot.fingerprint,
                parser_version="fixture/1",
                observation=observed(),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: record(), range(2)))
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(results[0][0].id, results[1][0].id)
        self.path.write_bytes(b"other input")
        with self.assertRaises(LocalConflict):
            self.journal.record(
                self.source,
                expected=None,
                fingerprint=SnapshotReader().read(self.source).fingerprint,
                parser_version="fixture/1",
                observation=observed(),
            )

    def test_operation_state_idempotency_cancel_and_recovery(self):
        queue = LocalOperationQueue(self.journal)
        fp = SnapshotReader().read(self.source).fingerprint
        op = queue.enqueue(kind="backup", requested_by="local", expected=fp)
        self.assertEqual(
            queue.enqueue(
                kind="backup", requested_by="local", expected=fp, operation_id=op
            ),
            op,
        )
        with self.assertRaises(LocalConflict):
            queue.enqueue(
                kind="future_write", requested_by="local", expected=fp, operation_id=op
            )
        queue.transition(op, "PENDING", "RUNNING")
        self.assertEqual(queue.recover_interrupted(), 1)
        self.assertEqual(queue.get(op)["status"], "FAILED")
        self.assertEqual(queue.get(op)["error"], "RECOVERY_REQUIRED")
        with self.assertRaises(ValueError):
            queue.transition(op, "FAILED", "RUNNING")
        cancelled = queue.enqueue(
            kind="future_write",
            requested_by="local",
            expected=fp,
            payload={"pokemon_id": "untrusted"},
        )
        queue.transition(cancelled, "PENDING", "CANCELLED")
        with self.assertRaises(LocalConflict):
            queue.transition(cancelled, "PENDING", "RUNNING")

    def test_operation_only_one_atomic_claim(self):
        queue = LocalOperationQueue(self.journal)
        op = queue.enqueue(
            kind="backup",
            requested_by="local",
            expected=SnapshotReader().read(self.source).fingerprint,
        )

        def claim():
            try:
                LocalOperationQueue(LocalJournal(self.journal.path)).transition(
                    op, "PENDING", "RUNNING"
                )
                return True
            except LocalConflict:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(lambda _: claim(), range(2))), 1)

    def test_backup_verified_bound_to_operation_and_no_write_execution(self):
        backups = BackupService(self.root / "backups", self.inspector)
        before = self.path.read_bytes()
        fp = SnapshotReader().read(self.source).fingerprint
        ticket = backups.prepare(self.source, operation_id=str(uuid4()), expected=fp)
        backups.verify(ticket)
        self.assertEqual(
            (backups.root / (ticket.backup_id + ".sav")).read_bytes(), before
        )
        with self.assertRaises(PhysicalWritesDisabled):
            backups.apply(ticket, self.source)
        self.assertEqual(self.path.read_bytes(), before)
        (backups.root / (ticket.backup_id + ".sav")).write_bytes(b"tampered")
        with self.assertRaises(LocalConflict):
            backups.verify(ticket)

    def test_backup_failure_cannot_mark_operation_success(self):
        core = LauncherCore(self.root / "core", self.inspector)
        core.select(self.path)
        with patch.object(core.backups, "prepare", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                core.backup()
        with core.journal.connection() as db:
            row = db.execute("SELECT status,error FROM operations").fetchone()
        self.assertEqual(tuple(row), ("FAILED", "BACKUP_FAILED"))

    def test_backup_conflict_and_invalid_operation_cannot_read_other_paths(self):
        backups = BackupService(self.root / "backups", self.inspector)
        fp = SnapshotReader().read(self.source).fingerprint
        self.path.write_bytes(b"new")
        with self.assertRaises(LocalConflict):
            backups.prepare(self.source, operation_id=str(uuid4()), expected=fp)
        with self.assertRaises(ValueError):
            backups.prepare(self.source, operation_id="../../outside", expected=fp)
        self.assertEqual(list(backups.root.iterdir()), [])

    def test_profile_single_instance_lock_and_restart_release(self):
        with LauncherLease(self.root / "lease"):
            with self.assertRaises(LocalConflict):
                with LauncherLease(self.root / "lease"):
                    pass
        with LauncherLease(self.root / "lease"):
            pass

    def test_core_manual_selection_restart_and_automatic_configuration(self):
        core = LauncherCore(self.root / "core", self.inspector)
        with self.assertRaises(ValueError):
            core.manual_sync()
        core.select(self.path)
        self.assertEqual(core.manual_sync().status, "SYNCED")
        restarted = LauncherCore(self.root / "core", self.inspector)
        self.assertEqual(restarted.manual_sync().status, "NO_CHANGE")
        with self.assertRaises(ValueError):
            restarted.watcher()
        ticket = restarted.backup()
        self.assertEqual(restarted.queue.get(ticket.operation_id)["status"], "SUCCESS")

    def test_sync_logs_exclude_paths_payload_and_identity(self):
        with self.assertLogs("pokeapp.launcher", level="INFO") as logs:
            self.sync.sync(self.source)
        text = " ".join(logs.output)
        self.assertNotIn(str(self.path), text)
        self.assertNotIn("Fixture", text)
        self.assertNotIn("123", text.split("parser=")[-1])
        self.assertIn("status=SYNCED", text)

    def test_history_isolation_architecture_and_frozen_snapshot(self):
        # Only pure 023 evidence types may be imported; no repository/service that
        # can write Team Lock, Hall, archive or an authoritative identity head.
        for folder in ("app/launcher", "app/save_parser"):
            for file in Path(folder).glob("*.py"):
                tree = ast.parse(file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    names = (
                        [x.name for x in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                        if isinstance(node, ast.ImportFrom)
                        else []
                    )
                    for name in names:
                        self.assertFalse(
                            name.startswith(
                                (
                                    "app.repositories",
                                    "app.application",
                                    "app.api",
                                    "storage",
                                    "supabase",
                                )
                            ),
                            (file, name),
                        )
        from app.domain.pokemon import PrivatePokemon
        from copy import deepcopy

        historical_lock = {
            "private_team_snapshot": [
                asdict(PrivatePokemon(species="Pikachu", nickname="Original"))
            ]
            * 6
        }
        persisted = json.dumps(deepcopy(historical_lock), sort_keys=True)
        self.sync.sync(self.source)
        changed = pokemon()
        changed["nickname"] = "Now changed"
        self.parser.value = observed(party=[changed] + [None] * 5)
        self.path.write_bytes(b"new save observation")
        self.sync.sync(self.source)
        self.assertEqual(json.dumps(historical_lock, sort_keys=True), persisted)
        self.assertEqual(
            self.journal.head(self.source).observation.party[0].nickname, "Now changed"
        )


class Phase9BackendTests(unittest.TestCase):
    def client(self, handler):
        client = BackendClient(
            "https://pokeapp.example", transport=httpx.MockTransport(handler)
        )
        self.addCleanup(client.close)
        return client

    def token(self, **changes):
        return (
            dict(
                user_id="auth-1",
                access_token="secret-access",
                refresh_token="secret-refresh",
                expires_at=4102444800,
                expires_in=3600,
            )
            | changes
        )

    def test_existing_auth_routes_refresh_and_no_token_persistence(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            if request.url.path.endswith("pin-login"):
                self.assertEqual(json.loads(request.content)["pin"], "1234")
                return httpx.Response(
                    200,
                    json=dict(
                        trainer_id="trainer-1",
                        auth_user_id="auth-1",
                        session=self.token(expires_at=1),
                    ),
                )
            if request.url.path.endswith("refresh"):
                self.assertEqual(
                    json.loads(request.content), {"refresh_token": "secret-refresh"}
                )
                return httpx.Response(
                    200, json=dict(session=self.token(access_token="rotated"))
                )
            self.assertIn(
                request.headers["authorization"],
                ("Bearer secret-access", "Bearer rotated"),
            )
            return httpx.Response(
                200,
                json=dict(
                    trainer_id="trainer-1",
                    display_name="Fixture",
                    is_admin=False,
                    globally_enabled=True,
                ),
            )

        session = LauncherSession(self.client(handler))
        session.login("fixture", "1234")
        self.assertEqual(session.principal().trainer_id, "trainer-1")
        self.assertIn("/v1/auth/refresh", calls)
        self.assertNotIn("secret", repr(session))
        session.logout()
        with self.assertRaises(BackendError):
            session.principal()

    def test_backend_unavailable_redirect_and_malformed_responses(self):
        for status, body in ((503, {}), (302, {}), (200, {"service_role": "secret"})):
            with self.subTest(status=status):
                client = self.client(
                    lambda request: httpx.Response(
                        status, json=body, headers={"Location": "https://evil.example"}
                    )
                )
                with self.assertRaises(BackendError) as cm:
                    client.me("secret")
                self.assertEqual(str(cm.exception), "BACKEND_UNAVAILABLE")

        def offline(request):
            raise httpx.ConnectError("secret connection details")

        with self.assertRaises(BackendError) as cm:
            self.client(offline).me("secret")
        self.assertEqual(str(cm.exception), "BACKEND_UNAVAILABLE")

    def test_disabled_and_mismatched_identity_fail_closed(self):
        def handler(request):
            if request.url.path.endswith("pin-login"):
                return httpx.Response(
                    200,
                    json=dict(
                        trainer_id="trainer-1",
                        auth_user_id="auth-1",
                        session=self.token(),
                    ),
                )
            return httpx.Response(
                200,
                json=dict(
                    trainer_id="trainer-2",
                    display_name="x",
                    is_admin=True,
                    globally_enabled=False,
                ),
            )

        session = LauncherSession(self.client(handler))
        with self.assertRaises(BackendError):
            session.login("fixture", "1234")
        with self.assertRaises(BackendError):
            session.principal()
