"""Trusted byte ingestion and durable Launcher outcome/readback boundaries."""

import tempfile
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
from phase9_fixtures import FakeParser, observed
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier
from test_phase16_launcher import ORIGIN, SID

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.save_ingestion import TrustedSaveIngestion, parsed_payload
from app.launcher.backend import BackendError
from app.launcher.journal import LocalConflict, LocalJournal, LocalReceipt
from app.launcher.trusted_sync import TrustedStore, deliver_trusted
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.models import ErrorCode, SaveError, SaveFingerprint
from app.save_parser.registration import observation_digest

VERSION = "pokeapp-reader/3;pkhex/24.11.11"
DATA = b"synthetic unit bytes; native parsing is exercised separately"
HASH = sha256(DATA).hexdigest()


class Repository:
    def __init__(self):
        self.saved = None
        self.context = {
            "current_save_id": None,
            "save_identity": None,
            "head": None,
            "entities": [],
        }
        self.writes = []
        self.raw = []

    def store_raw(self, *args):
        self.raw.append(args)

    def execute(self, operation, request):
        if operation == "context":
            return self.context
        if operation == "receipt":
            if self.saved is None:
                raise SeasonAdminRejected("missing", 404)
            return self.saved
        self.writes.append(request)
        self.saved = {
            k: request[k]
            for k in (
                "save_id",
                "trainer_id",
                "season_id",
                "sha256",
                "observation_digest",
                "parser_version",
            )
        }
        self.saved.update(status="registered", is_current=True)
        return self.saved


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.parser = FakeParser()
        self.parser.version = VERSION
        self.service = TrustedSaveIngestion(self.repo, self.parser)
        self.digest = observation_digest(self.parser.value, VERSION)

    def send(self, **kw):
        values = {
            "season_id": SID,
            "trainer_id": TRAINER_ID,
            "raw_hash": HASH,
            "expected_save_id": None,
            "local_digest": self.digest,
            "data": DATA,
        }
        return self.service.receive(**(values | kw))

    def test_server_parses_original_bytes_and_scopes_single_model(self):
        result = self.send()
        req = self.repo.writes[0]
        self.assertEqual(self.repo.raw[0][1], DATA)
        self.assertEqual(self.parser.calls, 1)
        self.assertEqual(req["payload"]["source_hash"], HASH)
        self.assertEqual(req["identity_plan"]["save_file_id"], result.save_id)
        self.assertEqual(req["identity_plan"]["trainer_id"], TRAINER_ID)
        self.assertEqual(req["storage_key"], f"trusted/{TRAINER_ID}/{SID}/{HASH}.sav")

    def test_replay_has_no_parse_storage_or_new_commit(self):
        first = self.send()
        self.assertEqual(self.send(), first)
        self.assertEqual(
            (self.parser.calls, len(self.repo.raw), len(self.repo.writes)), (1, 1, 1)
        )

    def test_client_digest_mismatch_never_registers(self):
        with self.assertRaises(SeasonAdminRejected):
            self.send(local_digest="a" * 64)
        self.assertEqual(self.repo.raw, [])
        self.assertEqual(self.repo.writes, [])

    def test_bad_hash_context_and_parser_fail_before_effect(self):
        for kwargs in (
            {"raw_hash": "b" * 64},
            {"expected_save_id": SID},
            {"data": b""},
        ):
            with self.assertRaises(SeasonAdminRejected):
                self.send(**kwargs)
        for code in (ErrorCode.CORRUPT_SAVE, ErrorCode.UNSUPPORTED_GAME):
            self.parser.parse = Mock(side_effect=SaveError(code))
            with self.assertRaises(SeasonAdminRejected):
                self.send()
        self.assertEqual(self.repo.raw, [])

    def test_mismatched_trainer_and_unproven_current_identity_fail(self):
        self.repo.context["save_identity"] = {"game": "X", "trainer": {}}
        with self.assertRaises(SeasonAdminRejected):
            self.send()
        self.repo.context.update(current_save_id=SID, save_identity=None)
        with self.assertRaises(SeasonAdminRejected):
            self.send(expected_save_id=SID)
        self.assertEqual(self.repo.writes, [])

    def test_projection_stats_order_and_unknown_progress(self):
        payload = parsed_payload(observed(), SID, TRAINER_ID, HASH)
        from app.api.read_models import PokemonRead, PrivatePokemonRead

        mon = payload["party"][0]["pokemon"]
        private = PrivatePokemonRead.model_validate(mon).model_dump()
        public = PokemonRead.model_validate(mon).model_dump()
        self.assertNotIn("identity_evidence", private)
        self.assertFalse(
            set(public) & {"ivs", "evs", "ability", "nature", "identity_evidence"}
        )
        self.assertIsNone(payload["observed_progress"]["progress"])

    def test_authenticated_raw_api_and_denials(self):
        principals = FakePrincipalRepository()
        principals.trainer = replace(principals.trainer, is_admin=False)
        with TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=principals,
                    save_ingestion=self.service,
                )
            )
        ) as client:
            path = f"/v1/seasons/{SID}/saves/raw?sha256={HASH}&observation_digest={self.digest}&expected_save_id=none"
            headers = {
                "Authorization": "Bearer validated",
                "Content-Type": "application/octet-stream",
            }
            self.assertEqual(client.put(path, content=DATA).status_code, 401)
            self.assertEqual(
                client.put(
                    path,
                    content=DATA,
                    headers=headers | {"Content-Type": "application/json"},
                ).status_code,
                415,
            )
            self.assertEqual(
                client.put(path, content=DATA, headers=headers).status_code, 200
            )
            self.assertEqual(
                client.get(
                    f"/v1/seasons/{SID}/saves/receipt?sha256={HASH}", headers=headers
                ).json()["sha256"],
                HASH,
            )
            self.assertEqual(
                client.put(
                    path.replace("none", "-" * 36), content=DATA, headers=headers
                ).status_code,
                422,
            )


class TrustedOutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = TrustedStore(LocalJournal(Path(self.temp.name) / "sync.db"))
        self.local = LocalReceipt(
            "fixture",
            1,
            SaveFingerprint(sha256=HASH, size=len(DATA)),
            VERSION,
            observed(),
        )
        self.store.enqueue_raw(ORIGIN, TRAINER_ID, SID, self.local, DATA)
        self.row = self.store.pending(ORIGIN, TRAINER_ID)
        self.registration = {
            "status": "registered",
            "save_id": SID,
            "trainer_id": TRAINER_ID,
            "season_id": SID,
            "sha256": HASH,
            "parser_version": VERSION,
            "observation_digest": self.row["digest"],
            "is_current": True,
        }
        self.session = Mock()

    def test_lost_response_reconciles_before_retry_and_requires_pc(self):
        self.session.request.side_effect = [None, {"current_save_id": None}]
        self.session.upload.side_effect = BackendError("BACKEND_UNAVAILABLE")
        with self.assertRaises(BackendError):
            deliver_trusted(self.session, self.store, self.row, selected_hash=HASH)
        row = self.store.pending(ORIGIN, TRAINER_ID)
        self.assertEqual(row["prepared"], 1)
        self.session.request.side_effect = [
            self.registration,
            {"status": "not_ready", "save": {"id": SID}},
        ]
        with self.assertRaises(BackendError):
            deliver_trusted(self.session, self.store, row, selected_hash=HASH)
        self.assertIsNone(self.store.receipt(ORIGIN, TRAINER_ID, SID, HASH))
        self.session.request.side_effect = [
            self.registration,
            {"status": "ready", "save": {"id": SID}},
        ]
        deliver_trusted(
            self.session,
            self.store,
            self.store.pending(ORIGIN, TRAINER_ID),
            selected_hash=HASH,
        )
        self.assertEqual(self.session.upload.call_count, 1)
        self.assertIsNotNone(self.store.receipt(ORIGIN, TRAINER_ID, SID, HASH))
        self.assertIsNone(self.store.pending(ORIGIN, TRAINER_ID))

    def test_obsolete_queued_save_never_uploads(self):
        self.session.request.return_value = None
        self.assertIsNone(
            deliver_trusted(self.session, self.store, self.row, selected_hash="f" * 64)
        )
        self.session.upload.assert_not_called()

    def test_wrong_scope_and_superseded_cannot_show_success(self):
        for patch in ({"trainer_id": SID}, {"is_current": False}):
            self.session.request.return_value = self.registration | patch
            with self.assertRaises(BackendError):
                deliver_trusted(self.session, self.store, self.row, selected_hash=HASH)
            self.assertIsNone(self.store.receipt(ORIGIN, TRAINER_ID, SID, HASH))
        self.session.upload.assert_not_called()

    def test_stable_bytes_digest_and_origin_scoped(self):
        with self.assertRaises(LocalConflict):
            self.store.enqueue_raw(
                ORIGIN, TRAINER_ID, SID, self.local, DATA + b"changed"
            )
        self.assertIsNone(self.store.pending("https://other.example", TRAINER_ID))
        self.assertIsNone(self.store.pending(ORIGIN, SID))

    def test_trusted_consent_is_new_explicit_and_account_scoped(self):
        self.assertFalse(self.store.enabled(ORIGIN, TRAINER_ID))
        self.store.enable(ORIGIN, TRAINER_ID)
        restarted = TrustedStore(self.store.journal)
        self.assertTrue(restarted.enabled(ORIGIN, TRAINER_ID))
        self.assertFalse(restarted.enabled(ORIGIN, SID))
        self.assertFalse(restarted.enabled("https://other.example", TRAINER_ID))

    def test_runtime_publishes_only_verified_readback_and_clears_superseded(self):
        from app.launcher.backend import BackendPrincipal
        from app.launcher.runtime import LauncherRuntime

        runtime = LauncherRuntime(
            Path(self.temp.name) / "runtime", Mock(),
            client=Mock(origin=ORIGIN), token_store=Mock(), start=False,
        )
        runtime.store = self.store
        runtime.receipt = self.local
        runtime.session = self.session
        principal = BackendPrincipal(
            trainer_id=TRAINER_ID, display_name="Fixture",
            globally_enabled=True, is_admin=False,
        )
        self.session._principal = principal
        self.session.principal.return_value = principal
        runtime.client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        runtime._patch(local_status="READY", cloud_sync=True)
        # Byte enqueue was already proved; isolate the cloud worker's UI state.
        runtime._enqueue_local = Mock()
        seasons = {"items": [{"id": SID, "status": "active"}]}
        self.session.request.side_effect = [
            # Old backend: item-use and transfer endpoints absent (missing=True).
            seasons, {"balance": "0"}, None, None, self.registration, {"status": "not_ready"},
        ]
        with self.assertRaisesRegex(BackendError, "SAVE_READBACK_PENDING"):
            runtime._cloud_step()
        self.assertIsNone(runtime.state()["cloud_receipt"])
        self.session.request.side_effect = [
            # Old backend: item-use and transfer endpoints absent (missing=True).
            seasons, {"balance": "0"}, None, None, self.registration,
            {"status": "ready", "save": {"id": SID}}, self.registration,
        ]
        runtime._cloud_step()
        self.assertEqual(runtime.state()["cloud_receipt"]["save_id"], SID)
        runtime.next_cloud_refresh = 0
        self.session.request.side_effect = [
            # Old backend: item-use and transfer endpoints absent (missing=True).
            seasons, {"balance": "0"}, None, None, self.registration | {"is_current": False},
        ]
        with self.assertRaisesRegex(BackendError, "SAVE_SUPERSEDED"):
            runtime._cloud_step()
        self.assertIsNone(runtime.state()["cloud_receipt"])
        self.session.upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
