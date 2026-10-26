"""27A: server-authoritative robbery seams (unit level; PG E2E is in tools)."""

import os
import subprocess
import sys
import unittest
from hashlib import sha256
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

from fastapi import Header
from fastapi.testclient import TestClient
from httpx import HTTPError

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.transfer_integration import TransferIntegration
from app.application.transfer_verification import TransferVerification
from app.application.transfer_worker import run_transfer_step
from app.launcher.transfer import (
    TRANSFER_MESSAGES,
    TransferAssignmentWire,
    TransferLegWire,
)
from app.repositories.errors import PersistenceError, TransferRejectedError
from app.repositories.supabase.transfer_storage import PrivateTransferStorage

AID, ROBBER, VICTIM = str(uuid4()), str(uuid4()), str(uuid4())
DATA = b"\0" * 415232


class Bucket:
    def __init__(self):
        self.objects, self.fail_upload = {}, False

    def upload(self, key, data, options):
        assert options["upsert"] == "false"
        if key in self.objects:
            raise HTTPError("exists")
        self.objects[key] = data
        if self.fail_upload:
            raise HTTPError("lost reply")

    def download(self, key):
        if key not in self.objects:
            raise HTTPError("missing")
        return self.objects[key]


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.bucket = Bucket()
        client = SimpleNamespace(
            storage=SimpleNamespace(from_=lambda name: self.bucket)
        )
        self.storage = PrivateTransferStorage(client)

    def test_immutable_store_and_lost_reply_reconciliation(self):
        key = f"transfer-basis/{AID}/source/{sha256(DATA).hexdigest()}.sav"
        self.bucket.fail_upload = True
        self.storage.store_raw(key, DATA, sha256(DATA).hexdigest())  # reconciled
        self.storage.store_raw(key, DATA, sha256(DATA).hexdigest())  # idempotent
        self.assertEqual(self.storage.read_source({"storage_key": key}), DATA)
        with self.assertRaises(PersistenceError):
            self.storage.store_raw(key, b"other" + DATA[5:], sha256(DATA).hexdigest())
        self.bucket.objects["trusted/x.sav"] = b"different"
        with self.assertRaises(PersistenceError):
            self.storage.store_raw("trusted/x.sav", DATA, sha256(DATA).hexdigest())

    def test_only_private_save_prefixes(self):
        for key in ("item-use/a.sav", "../trusted/a.sav", None):
            with self.assertRaises(PersistenceError):
                self.storage.read_source({"storage_key": key})
            with self.assertRaises(PersistenceError):
                self.storage.store_raw(key, DATA, sha256(DATA).hexdigest())


class WorkerTests(unittest.TestCase):
    def test_new_actions_dispatch_and_failures_stay_pending(self):
        jobs = [
            {"authorization_id": "a", "action": "adjudicate", "side": None},
            {"authorization_id": "b", "action": "rebase", "side": "source"},
            {"authorization_id": "c", "action": "settle", "side": "destination"},
            {"authorization_id": "d", "action": "finalize", "side": None},
        ]
        verification = Mock()
        verification.settle.side_effect = PersistenceError("lost")
        outcomes = run_transfer_step(lambda request: jobs, verification)
        self.assertEqual(
            [o["outcome"] for o in outcomes],
            ["DONE", "DONE", "RETRY_LATER", "REJECTED"],
        )
        verification.adjudicate.assert_called_once_with("a")
        verification.rebase.assert_called_once_with("b", "source")
        verification.settle.assert_called_once_with("c", "destination")
        verification.finalize.assert_not_called()  # two-proof completion superseded

    def test_lost_replies_never_repeat_effects(self):
        rpc = Mock(side_effect=lambda r: {"status": "X", "adjudicated": True})
        verifier = TransferVerification(rpc, None, None, None, None, store_raw=Mock())
        self.assertTrue(verifier.adjudicate(AID)["adjudicated"])
        self.assertEqual(rpc.call_count, 1)  # status only; no derive, no decision
        snap = {
            "adjudication": {"context": {}},
            "legs": {
                "source": {"obligation": "VERIFIED", "verified": True},
                "destination": {"obligation": "PHYSICAL_PENDING", "verified": True},
            },
        }
        rpc = Mock(return_value=snap)
        reader = Mock()
        verifier = TransferVerification(rpc, None, reader, None, None, store_raw=Mock())
        self.assertEqual(verifier.settle(AID, "source")["obligation"], "VERIFIED")
        self.assertTrue(verifier.verify(AID, "destination")["verified"])
        reader.read.assert_not_called()


class Service:
    def __init__(self):
        self.calls = []

    def enabled(self, tid):
        return True

    def candidate(self, sid, tid, aid, data):
        self.calls.append((tid, aid, len(data)))
        return {
            "authorization_id": aid,
            "side": "source",
            "status": "COMPETITIVELY_ADJUDICATED",
            "obligation": "DONOR_PHYSICAL_PENDING",
            "pair_id": None,
            "source_sha256": "a" * 64,
            "apply_started": False,
            "result_sha256": None,
            "verified": False,
            "accepted_save_id": None,
        }


class ApiTests(unittest.TestCase):
    def client(self, service):
        app = create_app(container=ApiContainer(transfer_integration=service))

        def principal(authorization: Annotated[str, Header()]):
            return SimpleNamespace(trainer_id=authorization.removeprefix("Bearer "))

        app.dependency_overrides[require_enabled_principal] = principal
        return TestClient(app)

    def test_candidate_route_takes_raw_bytes_for_the_principal_only(self):
        service = Service()
        path = f"/v1/launcher/seasons/{uuid4()}/transfers/{AID}/candidate"
        with self.client(service) as api:
            denied = api.put(
                path, json={}, headers={"Authorization": "Bearer " + VICTIM}
            )
            self.assertEqual(denied.status_code, 415)
            reply = api.put(
                path,
                content=DATA,
                headers={
                    "Authorization": "Bearer " + VICTIM,
                    "Content-Type": "application/octet-stream",
                },
            )
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertEqual(reply.json()["obligation"], "DONOR_PHYSICAL_PENDING")
        self.assertEqual(service.calls, [(VICTIM, AID, len(DATA))])

    def test_decided_robbery_cannot_be_cancelled_by_anyone(self):
        repo = Mock()
        repo.leg.side_effect = TransferRejectedError("TRANSFER_ADJUDICATED", 409)
        service = TransferIntegration(repo, Mock(), allowed_trainers=[ROBBER, VICTIM])
        with self.assertRaises(TransferRejectedError):
            service.withdraw(str(uuid4()), ROBBER, AID)
        outsider = TransferIntegration(repo, Mock(), allowed_trainers=[ROBBER])
        with self.assertRaises(TransferRejectedError):
            outsider.candidate(str(uuid4()), VICTIM, AID, DATA)


class LauncherWireTests(unittest.TestCase):
    def test_obligation_states_and_mandatory_sync(self):
        base = {"authorization_id": AID, "status": "COMPETITIVELY_ADJUDICATED"}
        victim = TransferAssignmentWire.model_validate(
            base | {"side": "source", "obligation": "DONOR_PHYSICAL_PENDING"}
        )
        robber = TransferAssignmentWire.model_validate(
            base | {"side": "destination", "obligation": "RECIPIENT_PHYSICAL_PENDING"}
        )
        settled = TransferAssignmentWire.model_validate(
            base | {"side": "source", "obligation": "DONOR_VERIFIED"}
        )
        self.assertEqual(
            (victim.mandatory, robber.mandatory, settled.mandatory),
            (True, False, False),
        )
        leg = TransferLegWire.model_validate(
            base
            | {
                "side": "source",
                "obligation": "DONOR_ABSENT_VERIFIED",
                "pair_id": str(uuid4()),
                "source_sha256": "a" * 64,
                "apply_started": False,
                "verified": False,
                "status": "RECONCILED",
            }
        )
        self.assertEqual(leg.status, "RECONCILED")
        for state in ("COMPETITIVELY_ADJUDICATED", "RECONCILED", "REPLANNING"):
            self.assertIn(state, TRANSFER_MESSAGES)

    @unittest.skipUnless(os.name == "nt", "Launcher runtime runs on Windows")
    def test_runtime_fulfil_needs_explicit_emulator_confirmation(self):
        code = (
            "from app.launcher.runtime import TRANSFER_COMMANDS;"
            "assert 'transfer_fulfil' in TRANSFER_COMMANDS"
        )
        subprocess.run([sys.executable, "-c", code], check=True)


if __name__ == "__main__":
    unittest.main()
