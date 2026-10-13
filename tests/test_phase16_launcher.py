"""Cloud foundation tests. Synthetic observations never imply authority."""

import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from phase9_fixtures import FakeParser, observed
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.launcher.backend import (
    BackendClient,
    BackendError,
    BackendPrincipal,
    LauncherSession,
    SessionTokens,
)
from app.launcher.cloud_store import CloudStore, deliver
from app.launcher.core import LauncherCore
from app.launcher.journal import LocalConflict, LocalJournal
from app.launcher.runtime import LauncherRuntime
from app.launcher.secrets import TokenStore, protect
from app.save_parser.adapter import SaveInspector
from app.save_parser.cloud import CloudObservation, ObservationReceipt
from app.save_parser.models import SaveFingerprint

SID = "22222222-2222-4222-8222-222222222222"
ORIGIN = "https://pokeapp.example"


def body(seed="a"):
    return CloudObservation(
        fingerprint=SaveFingerprint(sha256=seed * 64, size=100),
        parser_version="pokeapp-reader/3;pkhex/24.11.11",
        observation=observed(),
    )


def receipt(value=None):
    value = value or body()
    return {
        "id": value.identifier(TRAINER_ID, SID),
        "trainer_id": TRAINER_ID,
        "season_id": SID,
        "payload_digest": value.digest(),
        "received_at": "2026-10-13T10:00:00Z",
        "trust": "client_observed",
        "competitive_authority": False,
    }


def authenticated(client):
    session = LauncherSession(client)
    session._tokens = SessionTokens(
        user_id="fixture",
        access_token="private-token",
        refresh_token="private-refresh",
        expires_at=int(time.time()) + 3600,
    )
    session._principal = BackendPrincipal(
        trainer_id=TRAINER_ID,
        display_name="Fixture",
        globally_enabled=True,
        is_admin=False,
    )
    return session


class CloudApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.repo.execute.return_value = receipt()
        self.principals = FakePrincipalRepository()
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    launcher_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.path = f"/v1/launcher/seasons/{SID}/observations/{receipt()['id']}"
        self.headers = {"Authorization": "Bearer validated"}

    def test_verified_participant_can_submit_private_dto_without_admin(self):
        result = self.client.put(
            self.path, headers=self.headers, content=body().model_dump_json()
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json(), receipt())
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertFalse(result.json()["competitive_authority"])
        self.assertNotIn("observation", result.json())
        args = self.repo.execute.call_args.args
        self.assertEqual(args[0], "receive")
        self.assertEqual(args[1]["trainer_id"], TRAINER_ID)
        self.assertIsNone(args[1]["body"]["observation"]["progress"])

    def test_denials_before_repository(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.assertEqual(self.client.put(self.path, json={}).status_code, 401)
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(
            self.client.get(self.path, headers=self.headers).status_code, 403
        )
        self.repo.execute.assert_not_called()

    def test_identity_cannot_be_forged_and_payload_is_bounded(self):
        alien = body().identifier(str(uuid4()), SID)
        self.assertEqual(
            self.client.put(
                self.path.rsplit("/", 1)[0] + "/" + alien,
                headers=self.headers,
                content=body().model_dump_json(),
            ).status_code,
            409,
        )
        payload = body().model_dump(mode="json") | {"trainer_id": str(uuid4())}
        self.assertEqual(
            self.client.put(self.path, headers=self.headers, json=payload).status_code,
            422,
        )
        payload = body().model_dump(mode="json")
        payload["observation"]["progress"] = {"badges_count": 8}
        self.assertEqual(
            self.client.put(self.path, headers=self.headers, json=payload).status_code,
            422,
        )
        self.assertEqual(
            self.client.put(
                self.path, headers=self.headers, content=b"x" * (2097153)
            ).status_code,
            413,
        )
        self.repo.execute.assert_not_called()

    def test_cross_scope_or_authoritative_receipt_fails_closed(self):
        for change in (
            {"trainer_id": str(uuid4())},
            {"competitive_authority": True},
            {"body": {}},
            {"received_at": "not-a-date"},
        ):
            self.repo.execute.return_value = receipt() | change
            response = self.client.get(self.path, headers=self.headers)
            self.assertEqual(response.status_code, 503, response.text)

    def test_schema_and_receipt_strict(self):
        for version in (True, "1", 1.0):
            with self.assertRaises(ValueError):
                CloudObservation.model_validate(
                    body().model_dump() | {"schema_version": version}
                )
        for authority in (0, "false", True):
            with self.assertRaises(ValueError):
                ObservationReceipt.model_validate(
                    receipt() | {"competitive_authority": authority}
                )


class CloudLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = CloudStore(LocalJournal(self.root / "journal.sqlite3"))

    def test_healthy_heartbeat_uses_only_health_between_cloud_refreshes(self):
        client = Mock(origin=ORIGIN)
        client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        runtime = LauncherRuntime(
            self.root / "heartbeat",
            SaveInspector(FakeParser()),
            client=client,
            token_store=Mock(),
            start=False,
        )
        self.addCleanup(runtime.close)
        runtime.session = authenticated(client)
        runtime.next_cloud_refresh = time.monotonic() + 120
        runtime._cloud_step()
        client.json.assert_called_once_with("GET", "/health")
        client.me.assert_not_called()

    def test_unknown_put_outcome_reconciles_after_restart_without_second_put(self):
        calls, saved = [], {}

        class Session:
            def request(self, method, path, **kwargs):
                calls.append(method)
                if method == "GET":
                    return saved.get("receipt")
                saved["receipt"] = receipt()
                raise BackendError("BACKEND_UNAVAILABLE")

        self.store.enqueue(ORIGIN, TRAINER_ID, SID, body())
        with self.assertRaises(BackendError):
            deliver(Session(), self.store, self.store.pending(ORIGIN, TRAINER_ID))
        restarted = CloudStore(LocalJournal(self.root / "journal.sqlite3"))
        self.assertEqual(
            deliver(Session(), restarted, restarted.pending(ORIGIN, TRAINER_ID)).id,
            receipt()["id"],
        )
        self.assertEqual(calls, ["GET", "PUT", "GET"])
        self.assertIsNone(restarted.pending(ORIGIN, TRAINER_ID))
        self.assertEqual(
            restarted.receipt(ORIGIN, TRAINER_ID, SID, receipt()["id"]).model_dump(),
            receipt(),
        )
        self.assertIsNone(restarted.receipt(ORIGIN, str(uuid4()), SID, receipt()["id"]))
        self.assertEqual(
            restarted.enqueue(ORIGIN, TRAINER_ID, SID, body()), receipt()["id"]
        )
        self.assertIsNone(restarted.pending(ORIGIN, TRAINER_ID))

    def test_scope_limits_receipts_and_bounded_retry(self):
        self.store.enqueue(ORIGIN, TRAINER_ID, SID, body())
        self.assertIsNone(self.store.pending(ORIGIN, str(uuid4())))
        self.assertIsNone(self.store.pending("https://other.example", TRAINER_ID))
        session = Mock()
        session.request.side_effect = BackendError("BACKEND_UNAVAILABLE")
        for _ in range(5):
            with self.assertRaises(BackendError):
                deliver(session, self.store, self.store.pending(ORIGIN, TRAINER_ID))
        self.assertIsNone(self.store.pending(ORIGIN, TRAINER_ID))
        self.assertEqual(
            self.store.summary(ORIGIN, TRAINER_ID), {"pending": 1, "paused": 1}
        )
        self.store.retry(ORIGIN, TRAINER_ID)
        row = self.store.pending(ORIGIN, TRAINER_ID)
        with self.assertRaises(LocalConflict):
            self.store.accept(row, receipt() | {"trainer_id": str(uuid4())})
        self.store.block(row)
        self.store.retry(ORIGIN, TRAINER_ID)
        self.assertIsNone(self.store.pending(ORIGIN, TRAINER_ID))

    def test_cache_is_scoped_and_restored_stale_on_offline_restart(self):
        client = Mock(origin=ORIGIN)
        core = LauncherCore(self.root / "profile", SaveInspector(FakeParser()))
        save = self.root / "sample.sav"
        save.write_bytes(b"fixture")
        core.select(save)
        core.manual_sync()
        CloudStore(core.journal).save_cache(ORIGIN, TRAINER_ID, {"wallet": "1.6"})

        def load(origin, session):
            cached = authenticated(client)
            session._tokens, session._principal = cached._tokens, cached._principal

        tokens = Mock()
        tokens.load.side_effect = load
        save.unlink()
        runtime = LauncherRuntime(
            core.profile,
            SaveInspector(FakeParser()),
            client=client,
            token_store=tokens,
            start=False,
        )
        self.addCleanup(runtime.close)
        state = runtime.state()
        self.assertEqual(state["local_status"], "CACHED")
        self.assertEqual(state["observation"]["trainer"]["name"], "Fixture")
        self.assertEqual(state["cloud"]["data"]["wallet"], "1.6")
        self.assertTrue(state["cloud_stale"])
        self.assertEqual(state["auth_status"], "STALE")
        client.json.assert_not_called()

    def test_blocked_network_never_blocks_local_state_or_selection(self):
        entered, release = threading.Event(), threading.Event()

        def json_call(*args, **kwargs):
            entered.set()
            release.wait(5)
            raise BackendError("BACKEND_UNAVAILABLE")

        client = Mock(origin=ORIGIN)
        client.json.side_effect = json_call
        runtime = LauncherRuntime(
            self.root / "runtime",
            SaveInspector(FakeParser()),
            client=client,
            token_store=Mock(),
        )
        try:
            self.assertTrue(entered.wait(2))
            before = time.perf_counter()
            for _ in range(100):
                runtime.state()
            self.assertLess(time.perf_counter() - before, 0.2)
            with self.assertRaises(ValueError):
                runtime.command("purchase")
            save = self.root / "local.sav"
            save.write_bytes(b"fixture")
            self.assertEqual(
                runtime.command("select", {"path": str(save)})["status"], "QUEUED"
            )
            end = time.monotonic() + 3
            while runtime.state()["local_status"] != "READY" and time.monotonic() < end:
                time.sleep(0.03)
            self.assertEqual(runtime.state()["local_status"], "READY")
            self.assertEqual(save.read_bytes(), b"fixture")
        finally:
            release.set()
            runtime.close()

    def test_dpapi_roundtrip_origin_binding_tamper_and_no_plaintext(self):
        client = Mock(origin=ORIGIN)
        session = authenticated(client)
        tokens = TokenStore(self.root)
        tokens.save(ORIGIN, session)
        self.assertNotIn(b"private-token", tokens.path.read_bytes())
        self.assertNotIn(b"private-refresh", tokens.path.read_bytes())
        self.assertNotIn("private-token", repr(session))
        restored = LauncherSession(client)
        tokens.load("https://other.example", restored)
        self.assertIsNone(restored._tokens)
        tokens.load(ORIGIN, restored)
        self.assertEqual(restored._tokens, session._tokens)
        with self.assertRaises(ValueError):
            protect(tokens.path.read_bytes()[:-10], decrypt=True)
        tokens.clear()
        self.assertFalse(tokens.path.exists())

    def test_transient_failure_retains_tokens_but_rejection_requires_auth(self):
        client = Mock(origin=ORIGIN)
        session = authenticated(client)
        client.me.side_effect = BackendError("BACKEND_UNAVAILABLE")
        with self.assertRaises(BackendError):
            session.principal()
        self.assertIsNotNone(session._tokens)
        client.me.side_effect = BackendError("SESSION_REJECTED")
        with self.assertRaises(BackendError):
            session.principal()
        self.assertIsNone(session._tokens)

    def test_transport_never_replays_timeout_or_5xx(self):
        calls = []

        def handle(request):
            calls.append(request.method)
            raise httpx.ReadTimeout("private body must not escape")

        client = BackendClient(ORIGIN, transport=httpx.MockTransport(handle))
        self.addCleanup(client.close)
        with self.assertRaisesRegex(BackendError, "^BACKEND_UNAVAILABLE$"):
            client.json("PUT", "/v1/launcher/seasons/x", body={"private": "data"})
        self.assertEqual(calls, ["PUT"])
