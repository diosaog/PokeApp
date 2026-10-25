import unittest
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.item_use_transport import ItemUseTransport
from app.application.item_use_verification import VerificationRejected
from app.application.item_use_worker import SignedArtifactReader, verify_one
from app.domain.item_use_status import physical_state
from app.launcher.backend import BackendClient, BackendError
from app.launcher.item_use import AuthenticatedItemResultTransport
from app.launcher.write_files import WriteSafetyError
from app.repositories.errors import ItemUseRejectedError, PersistenceError
from app.repositories.supabase.item_use_transport import PrivateItemUseBlobs
from app.save_parser.models import ErrorCode, SaveError
from app.save_parser.writer import NativeWriteError


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.scope = (str(uuid4()), str(uuid4()), TRAINER_ID, str(uuid4()))
        self.repo, self.blobs = Mock(), Mock()
        self.transport = ItemUseTransport(
            self.repo, self.blobs, allowed_trainers=[TRAINER_ID]
        )
        self.data = bytes(415232)

    def test_off_default_and_exact_allowlist(self):
        self.assertFalse(APIConfig.from_env({}).item_verification_transport_enabled)
        with self.assertRaises(ValueError):
            APIConfig(item_verification_transport_enabled=True)
        with self.assertRaises(ItemUseRejectedError):
            self.transport.status(
                self.scope[0], self.scope[1], str(uuid4()), self.scope[3]
            )
        self.repo.execute.assert_not_called()

    def test_receipt_excludes_private_capabilities(self):
        self.repo.execute.return_value = {
            "authorization_id": self.scope[0],
            "status": "VERIFIED",
            "result_sha256": sha256(self.data).hexdigest(),
            "source_url": "SECRET",
            "result_url": "SECRET",
            "claim_id": "PRIVATE",
        }
        receipt = self.transport.submit(*self.scope, self.data)
        self.assertEqual(set(receipt), {"authorization_id", "status", "result_sha256"})
        self.blobs.put.assert_not_called()

    def test_size_and_concurrency_bound(self):
        with self.assertRaises(ItemUseRejectedError):
            self.transport.submit(*self.scope, b"short")
        self.transport.slots.acquire()
        self.transport.slots.acquire()
        with self.assertRaises(ItemUseRejectedError) as caught:
            self.transport.submit(*self.scope, self.data)
        self.assertEqual(caught.exception.status, 429)
        self.repo.execute.assert_not_called()

    def test_upload_unknown_reconciles_only_exact_bytes_never_upserts(self):
        bucket = Mock()
        blobs = PrivateItemUseBlobs(
            SimpleNamespace(storage=SimpleNamespace(from_=lambda _: bucket))
        )
        bucket.upload.side_effect = httpx.ReadTimeout("secret hidden")
        bucket.download.return_value = self.data
        blobs.put("item-use/test", self.data, sha256(self.data).hexdigest())
        self.assertEqual(bucket.upload.call_args.args[2]["upsert"], "false")
        bucket.download.return_value = b"different"
        with self.assertRaises(PersistenceError):
            blobs.put("item-use/test", self.data, sha256(self.data).hexdigest())
        bucket.remove.assert_not_called()

    def test_api_auth_off_scope_size_content_type_and_projection(self):
        container = ApiContainer(
            token_verifier=FakeTokenVerifier(),
            principal_repository=FakePrincipalRepository(),
        )
        a, s, _, c = self.scope
        path = f"/v1/launcher/seasons/{s}/item-uses/{a}/result?claim_id={c}"
        headers = {
            "Authorization": "Bearer fictional",
            "Content-Type": "application/octet-stream",
        }
        with TestClient(create_app(container=container)) as api:
            self.assertEqual(api.put(path, content=self.data).status_code, 401)
            self.assertEqual(
                api.put(path, content=self.data, headers=headers).status_code, 503
            )
            api.app.state.api_container = replace(
                container, item_use_transport=self.transport
            )
            self.assertEqual(
                api.put(
                    path,
                    content=self.data,
                    headers={"Authorization": "Bearer fictional"},
                ).status_code,
                415,
            )
            self.assertEqual(
                api.put(path, content=bytes(483329), headers=headers).status_code, 413
            )
            self.repo.execute.return_value = {
                "authorization_id": a,
                "status": "VERIFIED",
                "result_sha256": "f" * 64,
                "source_url": "SECRET",
            }
            result = api.put(path, content=self.data, headers=headers)
            self.assertEqual(result.status_code, 200)
            self.assertNotIn("SECRET", result.text)
            self.transport.allowed_trainers = frozenset()
            self.assertEqual(api.get(path, headers=headers).status_code, 403)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.data = bytes(415232)
        self.hash = sha256(self.data).hexdigest()
        self.key = "item-use/result.sav"
        self.url = (
            "https://store.example/storage/v1/object/sign/raw-saves/"
            + self.key
            + "?token=fictional"
        )
        self.requests = []
        self.response = httpx.Response(200, content=self.data)

        def respond(request):
            self.requests.append(request)
            return self.response

        client = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(client.close)
        self.reader = SignedArtifactReader("https://store.example", client=client)

    def test_exact_artifact_hash_and_size(self):
        self.assertEqual(
            self.reader.read(self.url, self.key, self.hash, len(self.data)), self.data
        )
        with self.assertRaises(VerificationRejected):
            self.reader.read(self.url, self.key, "f" * 64)
        self.response = httpx.Response(200, content=bytes(483329))
        with self.assertRaises(VerificationRejected):
            self.reader.read(self.url, self.key, self.hash)

    def test_SSRF_redirects_and_foreign_path_never_followed(self):
        for url in (
            self.url.replace("store.example", "other.example"),
            self.url.replace("https:", "http:"),
            self.url.replace("item-use/", "trusted/wrong/"),
            self.url + "#fragment",
        ):
            with self.assertRaises(VerificationRejected):
                self.reader.read(url, self.key, self.hash)
        self.assertFalse(self.requests)
        self.response = httpx.Response(
            302, headers={"Location": "https://other.example/secret"}
        )
        with self.assertRaises(PersistenceError):
            self.reader.read(self.url, self.key, self.hash)
        self.assertEqual(len(self.requests), 1)

    def test_storage_network_errors_are_sanitized(self):
        def fail(_):
            raise httpx.ReadTimeout("TOKEN")

        with httpx.Client(transport=httpx.MockTransport(fail)) as client:
            reader = SignedArtifactReader("https://store.example", client=client)
            with self.assertRaises(PersistenceError) as caught:
                reader.read(self.url, self.key, self.hash)
            self.assertNotIn("TOKEN", str(caught.exception))


class CurrentStateTests(unittest.TestCase):
    def test_states_do_not_rewrite_historical_receipt(self):
        historical = {"physical_effect_status": "pending"}
        auth = {"status": "APPLIED_VERIFIED", "receipt": historical}
        self.assertEqual(physical_state("revive", auth), "APPLIED_VERIFIED")
        self.assertEqual(historical, {"physical_effect_status": "pending"})
        self.assertEqual(physical_state("revive", used=True), "LEGACY_PENDING")
        self.assertEqual(physical_state("shield", used=True), "NOT_REQUIRED")
        self.assertEqual(physical_state("revive"), "AVAILABLE")

    def test_expiry_unknown_and_recovery_fail_closed(self):
        self.assertEqual(
            physical_state(
                "revive",
                {"status": "PREPARED", "expires_at": "2020-01-01T00:00:00Z"},
                now=datetime.now(UTC),
            ),
            "EXPIRED",
        )
        self.assertEqual(physical_state("revive", {"status": "PREPARED"}), "UNKNOWN")
        for state in ("BLOCKED_UNCERTAIN", "RECOVERY_REQUIRED", "FAILED_RECOVERABLE"):
            self.assertEqual(physical_state("revive", {"status": state}), state)


class LauncherTransportTests(unittest.TestCase):
    def test_worker_infrastructure_failure_retries_without_rejecting_artifact(self):
        a = {"id": str(uuid4()), "season_id": str(uuid4()), "trainer_id": TRAINER_ID}
        job = {
            "authorization_id": a["id"],
            "lease_id": str(uuid4()),
            "claim_id": str(uuid4()),
            "result_url": "private",
            "storage_key": "private",
            "result_sha256": "a" * 64,
            "byte_size": 415232,
        }
        for error in (NativeWriteError(), SaveError(ErrorCode.PARSER_FAILURE)):
            calls = []

            def rpc(request, calls=calls):
                calls.append(request["operation"])
                return job if request["operation"] == "lease" else {"authorization": a}

            with patch(
                "app.application.item_use_worker.TrustedItemUseVerification"
            ) as service:
                service.return_value.verify.side_effect = error
                self.assertEqual(verify_one(rpc, Mock(), Mock(), Mock()), "RETRY_LATER")
            self.assertEqual(calls, ["lease", "context"])

    def test_exact_scope_and_existing_JWT_raw_transport_no_automatic_retry(self):
        calls = []

        def respond(request):
            calls.append(request)
            self.assertEqual(request.headers["authorization"], "Bearer fictional")
            self.assertEqual(request.content, b"isolated")
            raise httpx.ReadTimeout("lost response")

        client = BackendClient(
            "https://api.example", transport=httpx.MockTransport(respond)
        )
        self.addCleanup(client.close)
        session = Mock()
        session.principal.return_value = SimpleNamespace(trainer_id=TRAINER_ID)
        session.upload.side_effect = lambda path, data: client.upload(
            path, data, "fictional"
        )
        transport = AuthenticatedItemResultTransport(session)
        scope = (str(uuid4()), str(uuid4()), TRAINER_ID, str(uuid4()))
        with self.assertRaises(BackendError):
            transport.submit(*scope, b"isolated")
        self.assertEqual(len(calls), 1)
        self.assertIn("/v1/launcher/seasons/", calls[0].url.path)
        with self.assertRaises(WriteSafetyError):
            transport.status(scope[0], scope[1], str(uuid4()), scope[3])
        session.request.assert_not_called()
