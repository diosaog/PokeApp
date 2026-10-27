"""Phase 28 incident center API: admin only, reasoned, idempotent, scoped."""

import unittest
from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.routes.incidents import digest
from app.repositories.errors import PersistenceError
from app.repositories.supabase.incidents import SupabaseIncidentRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected

SEASON = "22222222-2222-4222-8222-222222222222"
PURCHASE = "33333333-3333-4333-8333-333333333333"
PLAYER = "44444444-4444-4444-8444-444444444444"
AUTH = {"Authorization": "Bearer opaque-token"}


class FakeIncidents:
    def __init__(self):
        self.calls = []
        self.fail = None
        self.receipts = {}

    def read(self, actor, season):
        self.calls.append(("read", actor, season))
        return {
            "season_id": season,
            "season_status": "active",
            "wallets": [],
            "purchases": [],
            "robberies": [],
            "history": [],
        }

    def resolve_purchase(
        self, actor, season, purchase, kind, operation, digest, reason
    ):
        self.calls.append(
            ("resolve", actor, season, purchase, kind, operation, digest, reason)
        )
        if self.fail:
            raise self.fail
        # The database keeps one receipt per operation id.
        return self.receipts.setdefault(
            operation,
            {
                "operation_id": operation,
                "kind": kind,
                "season_id": season,
                "trainer_id": PLAYER,
                "purchase_id": purchase,
                "status": "cancelled" if kind == "purchase_cancel" else "refunded",
                "amount": 30,
                "ledger_id": str(uuid4()),
                "balance_after": 100,
                "replayed": operation in self.receipts,
            },
        )

    def adjust_coins(self, actor, season, trainer, amount, operation, digest, reason):
        self.calls.append(
            ("adjust", actor, season, trainer, amount, operation, digest, reason)
        )
        if self.fail:
            raise self.fail
        return {
            "operation_id": operation,
            "kind": "coin_adjustment",
            "season_id": season,
            "trainer_id": trainer,
            "purchase_id": None,
            "status": "applied",
            "amount": amount,
            "ledger_id": str(uuid4()),
            "balance_after": 100 + amount,
            "replayed": False,
        }


def client(incidents=None, admin=True):
    principals = FakePrincipalRepository()
    principals.trainer = replace(principals.trainer, is_admin=admin)
    return TestClient(
        create_app(
            container=ApiContainer(
                token_verifier=FakeTokenVerifier(),
                principal_repository=principals,
                incident_repository=incidents,
            )
        )
    )


class IncidentApiTests(unittest.TestCase):
    def post(self, api, path, body, key=None):
        return api.post(
            f"/v1/admin/seasons/{SEASON}/incidents{path}",
            json=body,
            headers={**AUTH, "Idempotency-Key": key or str(uuid4())},
        )

    def test_only_administrators_reach_the_center(self):
        incidents = FakeIncidents()
        api = client(incidents, admin=False)
        self.assertEqual(
            api.get(f"/v1/admin/seasons/{SEASON}/incidents", headers=AUTH).status_code,
            403,
        )
        response = self.post(
            api, f"/purchases/{PURCHASE}", {"action": "cancel", "reason": "Duplicada"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(incidents.calls, [])

    def test_disabled_until_migration_062_is_applied(self):
        response = client(None).get(
            f"/v1/admin/seasons/{SEASON}/incidents", headers=AUTH
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "INCIDENTS_UNAVAILABLE")

    def test_cancel_sends_actor_reason_and_a_bound_hash(self):
        incidents = FakeIncidents()
        key = str(uuid4())
        response = self.post(
            client(incidents),
            f"/purchases/{PURCHASE}",
            {"action": "cancel", "reason": "  Compra duplicada  "},
            key,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "cancelled")
        call = incidents.calls[0]
        self.assertEqual(
            call[:6], ("resolve", TRAINER_ID, SEASON, PURCHASE, "purchase_cancel", key)
        )
        self.assertEqual(call[7], "Compra duplicada")
        # The same command always hashes the same; another action does not.
        self.assertEqual(
            call[6],
            digest(
                "purchase_cancel",
                SEASON,
                PURCHASE,
                {"action": "cancel", "reason": "Compra duplicada"},
            ),
        )
        self.assertNotEqual(
            call[6],
            digest(
                "purchase_refund",
                SEASON,
                PURCHASE,
                {"action": "refund", "reason": "Compra duplicada"},
            ),
        )

    def test_retry_with_the_same_key_returns_the_same_receipt(self):
        incidents = FakeIncidents()
        api, key = client(incidents), str(uuid4())
        body = {"action": "refund", "reason": "Objeto no aplicado"}
        first = self.post(api, f"/purchases/{PURCHASE}", body, key).json()
        second = self.post(api, f"/purchases/{PURCHASE}", body, key).json()
        self.assertEqual(first["ledger_id"], second["ledger_id"])

    def test_requests_are_validated_before_the_database(self):
        incidents = FakeIncidents()
        api = client(incidents)
        for path, body in (
            (f"/purchases/{PURCHASE}", {"action": "delete", "reason": "Duplicada"}),
            (f"/purchases/{PURCHASE}", {"action": "cancel", "reason": " ok "}),
            (f"/purchases/{PURCHASE}", {"action": "cancel"}),
            (
                f"/purchases/{PURCHASE}",
                {"action": "cancel", "reason": "Duplicada", "amount": 5},
            ),
            ("/coins", {"trainer_id": PLAYER, "amount": 0, "reason": "Corrección"}),
            (
                "/coins",
                {"trainer_id": PLAYER, "amount": 100001, "reason": "Corrección"},
            ),
        ):
            self.assertEqual(self.post(api, path, body).status_code, 422, body)
        missing_key = api.post(
            f"/v1/admin/seasons/{SEASON}/incidents/coins",
            json={"trainer_id": PLAYER, "amount": 5, "reason": "Corrección"},
            headers=AUTH,
        )
        self.assertEqual(missing_key.status_code, 422)
        self.assertEqual(incidents.calls, [])

    def test_database_refusals_keep_their_meaning(self):
        incidents = FakeIncidents()
        api = client(incidents)
        for code, status in (
            ("PURCHASE_LINKED_TO_SAVE_OPERATION", 409),
            ("PURCHASE_ALREADY_REVERSED", 409),
            ("INSUFFICIENT_FUNDS", 409),
            ("ADMIN_REQUIRED", 403),
        ):
            incidents.fail = SeasonAdminRejected(code, status)
            response = self.post(
                api,
                f"/purchases/{PURCHASE}",
                {"action": "cancel", "reason": "Duplicada"},
            )
            self.assertEqual(
                (response.status_code, response.json()["detail"]["code"]),
                (status, code),
            )
        incidents.fail = PersistenceError("down")
        response = self.post(
            api, "/coins", {"trainer_id": PLAYER, "amount": 5, "reason": "Corrección"}
        )
        self.assertEqual(response.status_code, 503)

    def test_a_receipt_for_something_else_is_never_shown_as_success(self):
        class Wrong(FakeIncidents):
            def adjust_coins(self, *args):
                receipt = super().adjust_coins(*args)
                return {**receipt, "trainer_id": str(uuid4())}

        response = self.post(
            client(Wrong()),
            "/coins",
            {"trainer_id": PLAYER, "amount": 5, "reason": "Corrección"},
        )
        self.assertEqual(response.status_code, 503)


class RepositoryErrorTests(unittest.TestCase):
    def test_database_messages_map_to_stable_codes(self):
        class Boom(Exception):
            message = "purchase_linked_to_save_operation"

        class Rpc:
            def rpc(self, *_):
                raise Boom()

        with self.assertRaises(SeasonAdminRejected) as raised:
            SupabaseIncidentRepository(Rpc()).read("a", "s")
        self.assertEqual(
            (raised.exception.code, raised.exception.status),
            ("PURCHASE_LINKED_TO_SAVE_OPERATION", 409),
        )

        class Unknown(Exception):
            message = "connection reset"

        class Down:
            def rpc(self, *_):
                raise Unknown()

        with self.assertRaises(PersistenceError):
            SupabaseIncidentRepository(Down()).read("a", "s")


if __name__ == "__main__":
    unittest.main()
