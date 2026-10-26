"""24B seams without a database; the PG/native journey lives in validate_phase24b_local."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

from fastapi import Header
from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.item_use_verification import VerificationRejected
from app.application.transfer_integration import TransferIntegration
from app.application.transfer_worker import run_transfer_step
from app.launcher.transfer import AuthenticatedTransferRemote
from app.launcher.write_files import WriteSafetyError
from app.repositories.errors import PersistenceError, TransferRejectedError

SID, AID, ROBBER, VICTIM, OUTSIDER, ENTITY, PURCHASE = (str(uuid4()) for _ in range(7))
HASH = "a" * 64


def leg(**fields):
    return {
        "authorization_id": AID,
        "side": "destination",
        "status": "PREPARING",
        "source_sha256": HASH,
        "apply_started": False,
        "result_sha256": None,
        "verified": False,
        "accepted_save_id": None,
        "result_key": "item-use/secret.sav",
        "proof": {"never": "public"},
    } | fields


class Repository:
    def __init__(self):
        self.calls = []
        self.owner = VICTIM

    def target_owner(self, sid, eid):
        return self.owner

    def reserve(self, request):
        self.calls.append(("reserve", request))
        return {"authorization_id": AID, "status": "PREPARING"}

    def list(self, sid, tid):
        return [
            leg(
                purchase_id=PURCHASE,
                pokemon_entity_id=ENTITY,
                claimed=False,
                expires_at="2026-10-25T11:00:00Z",
                created_at="2026-10-25T10:00:00Z",
                intent={"mutation": {"kind": "transfer_insert"}},
            )
        ]

    def leg(self, request):
        self.calls.append(("leg", request))
        if request["operation"] == "cancel":
            raise TransferRejectedError("TRANSFER_ASSISTED_RECOVERY_REQUIRED", 409)
        return leg()


class TransferApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.service = TransferIntegration(
            self.repo, Mock(), allowed_trainers=[ROBBER, VICTIM]
        )

    def client(self, service):
        app = create_app(container=ApiContainer(transfer_integration=service))

        def principal(authorization: Annotated[str, Header()]):
            return SimpleNamespace(trainer_id=authorization.removeprefix("Bearer "))

        app.dependency_overrides[require_enabled_principal] = principal
        return TestClient(app)

    def call(self, method, path, tid=ROBBER, service="default", **kwargs):
        with self.client(self.service if service == "default" else service) as api:
            headers = {"Authorization": "Bearer " + tid} | kwargs.pop("headers", {})
            return api.request(method, path, headers=headers, **kwargs)

    def request(self, tid=ROBBER, key=None, service="default"):
        return self.call(
            "POST",
            f"/v1/seasons/{SID}/shop/purchases/{PURCHASE}/transfer",
            tid,
            service,
            json={"pokemon_entity_id": ENTITY},
            headers={"Idempotency-Key": key or str(uuid4())},
        )

    def test_disabled_service_never_reserves(self):
        self.assertEqual(self.request(service=None).status_code, 503)
        reply = self.call("GET", f"/v1/seasons/{SID}/transfers", service=None)
        self.assertEqual(reply.json(), {"items": [], "transfer_enabled": False})

    def test_both_participants_must_be_in_cohort_before_reservation(self):
        self.assertEqual(self.request(OUTSIDER).status_code, 403)
        self.repo.owner = OUTSIDER
        reply = self.request()
        self.assertEqual(reply.json()["detail"]["code"], "TRANSFER_PEER_UNAVAILABLE")
        self.repo.owner = ROBBER
        self.assertEqual(self.request().status_code, 409)
        self.assertFalse(self.repo.calls)

    def test_operation_id_is_the_uuid_idempotency_key(self):
        self.assertEqual(self.request(key="retry-1").status_code, 422)
        key = str(uuid4())
        self.assertEqual(self.request(key=key).status_code, 200)
        self.assertEqual(self.repo.calls[0][1]["operation_id"], key)
        self.assertEqual(self.repo.calls[0][1]["trainer_id"], ROBBER)

    def test_reads_never_expose_private_fields_and_web_hides_plans(self):
        web = self.call("GET", f"/v1/seasons/{SID}/transfers").json()
        self.assertTrue(web["transfer_enabled"])
        self.assertNotIn("intent", web["items"][0])
        launcher = self.call("GET", f"/v1/launcher/seasons/{SID}/transfers").json()
        self.assertEqual(
            launcher["items"][0]["intent"], {"mutation": {"kind": "transfer_insert"}}
        )
        got = self.call("GET", f"/v1/launcher/seasons/{SID}/transfers/{AID}").json()
        self.assertNotIn("result_key", got)
        self.assertNotIn("proof", got)
        outsider = self.call("GET", f"/v1/seasons/{SID}/transfers", OUTSIDER).json()
        self.assertEqual(outsider, {"items": [], "transfer_enabled": False})

    def test_leg_body_shape_and_safe_rejection_codes(self):
        path = f"/v1/launcher/seasons/{SID}/transfers/{AID}"
        bad = (
            {"operation": "cancel", "claim_id": str(uuid4())},
            {"operation": "ready", "claim_id": str(uuid4())},
            {"operation": "begin"},
            {"operation": "finish", "claim_id": str(uuid4())},
            {"operation": "begin", "claim_id": str(uuid4()), "proof": {}},
        )
        for body in bad:
            self.assertEqual(self.call("PUT", path, json=body).status_code, 422, body)
        reply = self.call("PUT", path, json={"operation": "cancel"})
        self.assertEqual(reply.status_code, 409)
        self.assertEqual(
            reply.json()["detail"]["code"], "TRANSFER_ASSISTED_RECOVERY_REQUIRED"
        )
        upload = self.call(
            "PUT",
            f"{path}/result?claim_id={uuid4()}",
            content=b"x",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(upload.status_code, 415)

    def test_foreign_receipt_and_victim_web_withdrawal_rejected(self):
        self.repo.leg = lambda request: leg(authorization_id=str(uuid4()))
        got = self.call("GET", f"/v1/launcher/seasons/{SID}/transfers/{AID}")
        self.assertEqual(got.status_code, 404)
        self.repo.leg = lambda request: leg(side="source")
        cancel = self.call("POST", f"/v1/seasons/{SID}/transfers/{AID}/cancel", VICTIM)
        self.assertEqual(
            cancel.json()["detail"]["code"], "TRANSFER_VICTIM_CANNOT_CANCEL"
        )
        # Same rule through the Launcher leg route: the victim cannot veto.
        launcher = self.call(
            "PUT",
            f"/v1/launcher/seasons/{SID}/transfers/{AID}",
            VICTIM,
            json={"operation": "cancel"},
        )
        self.assertEqual(launcher.status_code, 409)
        self.assertEqual(
            launcher.json()["detail"]["code"], "TRANSFER_VICTIM_CANNOT_CANCEL"
        )


class LauncherRemoteTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.remote = AuthenticatedTransferRemote(self.session, SID, ROBBER)
        self.scope = {"authorization_id": AID, "season_id": SID, "trainer_id": ROBBER}

    def test_scope_and_operation_allowlist(self):
        for request in (
            self.scope | {"trainer_id": VICTIM, "operation": "get"},
            self.scope | {"season_id": str(uuid4()), "operation": "get"},
            self.scope | {"operation": "reserve_result"},
        ):
            with self.assertRaises(WriteSafetyError):
                self.remote.leg(request)
        self.session.request.assert_not_called()

    def test_cancel_sends_no_claim_and_receipts_are_revalidated(self):
        self.session.request.return_value = leg()
        self.remote.leg(self.scope | {"operation": "cancel", "claim_id": str(uuid4())})
        self.assertEqual(
            self.session.request.call_args.kwargs["body"], {"operation": "cancel"}
        )
        self.session.request.return_value = leg(authorization_id=str(uuid4()))
        with self.assertRaises(WriteSafetyError):
            self.remote.leg(self.scope | {"operation": "get"})
        self.session.request.return_value = leg(status="APPLIED")
        with self.assertRaises(WriteSafetyError):
            self.remote.leg(self.scope | {"operation": "get"})


class RuntimeTests(unittest.TestCase):
    def runtime(self):
        from app.launcher.backend import BackendPrincipal
        from app.launcher.runtime import LauncherRuntime

        self.temp = tempfile.TemporaryDirectory(prefix="pokeapp-24b-")
        self.addCleanup(self.temp.cleanup)
        runtime = LauncherRuntime(
            Path(self.temp.name),
            Mock(),
            client=Mock(origin="https://x.invalid"),
            token_store=Mock(),
            start=False,
        )
        runtime.session = Mock(
            _principal=BackendPrincipal(
                trainer_id=ROBBER,
                display_name="R",
                is_admin=False,
                globally_enabled=True,
            )
        )
        runtime.value["cloud"] = {"data": {"season": {"id": SID}}}
        return runtime

    def test_arguments_require_explicit_emulator_confirmation(self):
        runtime = self.runtime()
        for name, args in (
            ("transfer_apply", {"authorization_id": AID}),
            (
                "transfer_apply",
                {"authorization_id": AID, "closed_emulator_confirmed": False},
            ),
            (
                "transfer_refresh",
                {"authorization_id": AID, "closed_emulator_confirmed": True},
            ),
            ("transfer_prepare", {"authorization_id": "x"}),
        ):
            with self.assertRaises(ValueError):
                runtime.command(name, args)

    def test_production_build_fails_closed_without_pausing_sync(self):
        runtime = self.runtime()
        self.assertFalse(runtime.state()["write"]["transfer_application_enabled"])
        runtime.command(
            "transfer_prepare",
            {"authorization_id": AID, "closed_emulator_confirmed": True},
        )
        runtime._write_step()
        state = runtime.state()
        self.assertIn("no está habilitada", state["write_error"])
        self.assertFalse(runtime.save_activity.recovery_required)
        runtime.session.request.assert_not_called()

    def test_cloud_discovery_caches_status_but_never_plans(self):
        runtime = self.runtime()
        principal = runtime.session._principal
        runtime.session.principal.return_value = principal
        runtime.client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        listing = {
            "transfer_enabled": True,
            "items": [
                Repository().list(SID, ROBBER)[0]
                | {"result_sha256": None, "verified": False}
            ],
        }

        def request(method, path, **kwargs):
            if path == "/v1/read/seasons":
                return {"items": [{"id": SID, "status": "active"}]}
            if path.endswith("/shop"):
                return {"balance": "0"}
            if path.endswith("/transfers"):
                self.assertTrue(kwargs["missing"])
                return listing
            return None

        runtime.session.request.side_effect = request
        runtime._enqueue_local = Mock()
        runtime._cloud_step()
        cached = runtime.state()["cloud"]["data"]["transfers"]
        self.assertEqual(
            cached,
            [
                {
                    "authorization_id": AID,
                    "side": "destination",
                    "status": "PREPARING",
                    "planned": True,
                    "claimed": False,
                    "apply_started": False,
                    "verified": False,
                    "location": None,
                }
            ],
        )
        self.assertNotIn("transfer_insert", str(runtime.state()))


class WorkerTests(unittest.TestCase):
    def test_dispatch_and_failure_classification(self):
        jobs = [
            {"authorization_id": "a", "action": "plan", "side": None},
            {"authorization_id": "b", "action": "verify", "side": "source"},
            {"authorization_id": "c", "action": "finalize", "side": None},
        ]
        verification = Mock()
        verification.verify.side_effect = VerificationRejected("ARTIFACT_HASH_MISMATCH")
        verification.finalize.side_effect = PersistenceError("lost")
        outcomes = run_transfer_step(lambda request: jobs, verification)
        self.assertEqual(
            [o["outcome"] for o in outcomes], ["DONE", "REJECTED", "RETRY_LATER"]
        )
        verification.prepare.assert_called_once_with("a")
        verification.verify.assert_called_once_with("b", "source")
        with self.assertRaises(PersistenceError):
            run_transfer_step(lambda request: None, verification)


if __name__ == "__main__":
    unittest.main()
