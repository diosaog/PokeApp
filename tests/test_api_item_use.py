from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.domain.item_use import ItemUsePrepareRequest
from app.repositories.errors import ItemUseRejectedError
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


SEASON_ID = str(uuid4())
PURCHASE_ID = str(uuid4())
AUTHORIZATION_ID = str(uuid4())
POKEMON_ID = str(uuid4())
SAVE_ID = str(uuid4())
SAVE_HASH = "a" * 64


def receipt(**changes):
    row = {
        "id": AUTHORIZATION_ID,
        "operation_id": "item-op-1",
        "purchase_id": PURCHASE_ID,
        "season_id": SEASON_ID,
        "trainer_id": TRAINER_ID,
        "target_pokemon_entity_id": POKEMON_ID,
        "save_file_id": SAVE_ID,
        "save_sha256": SAVE_HASH,
        "effect_code": "revive",
        "status": "PREPARED",
        "observed_sha256": None,
        "error_code": None,
        "receipt": None,
        "created_at": "2026-10-25T10:00:00Z",
        "updated_at": "2026-10-25T10:00:00Z",
        "applied_at": None,
    }
    row.update(changes)
    return row


@dataclass
class FakeItemUseRepository:
    prepared: dict | None = None
    completed: dict | None = None
    listed: list[dict] | None = None
    error: Exception | None = None

    def prepare(self, request):
        if self.error:
            raise self.error
        self.prepared = request
        return receipt(
            operation_id=request.operation_id,
            purchase_id=request.purchase_id,
            season_id=request.season_id,
            trainer_id=request.trainer_id,
            target_pokemon_entity_id=request.pokemon_entity_id,
            save_file_id=request.save_file_id,
            save_sha256=request.save_sha256,
        )

    def complete(self, authorization_id, season_id, trainer_id, request):
        if self.error:
            raise self.error
        self.completed = {
            "authorization_id": authorization_id,
            "season_id": season_id,
            "trainer_id": trainer_id,
            "request": request,
        }
        return receipt(
            id=authorization_id,
            operation_id=request["operation_id"],
            season_id=season_id,
            trainer_id=trainer_id,
            status=request["status"],
            observed_sha256=request.get("observed_sha256"),
        )

    def list(self, season_id, trainer_id):
        if self.error:
            raise self.error
        return self.listed or [receipt(season_id=season_id, trainer_id=trainer_id)]


class ItemUseApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeItemUseRepository()
        self.verifier = FakeTokenVerifier()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=self.verifier,
                    principal_repository=self.principals,
                    item_use_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer dummy"}

    def test_prepare_passes_server_principal_and_idempotency(self):
        response = self.client.post(
            f"/v1/seasons/{SEASON_ID}/shop/purchases/{PURCHASE_ID}/item-use",
            headers={**self.headers, "Idempotency-Key": "prepare-key"},
            json={
                "pokemon_entity_id": POKEMON_ID,
                "save_file_id": SAVE_ID,
                "save_sha256": SAVE_HASH,
                "operation_id": "item-op-1",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.repo.prepared.season_id, SEASON_ID)
        self.assertEqual(self.repo.prepared.trainer_id, TRAINER_ID)
        self.assertEqual(self.repo.prepared.idempotency_key, "prepare-key")
        self.assertEqual(response.json()["status"], "PREPARED")

    def test_complete_passes_scope_before_completion(self):
        response = self.client.put(
            f"/v1/launcher/seasons/{SEASON_ID}/item-uses/{AUTHORIZATION_ID}",
            headers=self.headers,
            json={
                "operation_id": "item-op-1",
                "status": "APPLIED_VERIFIED",
                "observed_sha256": SAVE_HASH,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.repo.completed["authorization_id"], AUTHORIZATION_ID)
        self.assertEqual(self.repo.completed["season_id"], SEASON_ID)
        self.assertEqual(self.repo.completed["trainer_id"], TRAINER_ID)
        self.assertEqual(self.repo.completed["request"]["status"], "APPLIED_VERIFIED")

    def test_list_is_principal_scoped(self):
        response = self.client.get(
            f"/v1/launcher/seasons/{SEASON_ID}/item-uses", headers=self.headers
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"][0]["trainer_id"], TRAINER_ID)

    def test_missing_backend_fails_closed(self):
        client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=self.verifier,
                    principal_repository=self.principals,
                )
            )
        )
        self.addCleanup(client.close)
        response = client.get(
            f"/v1/launcher/seasons/{SEASON_ID}/item-uses", headers=self.headers
        )
        self.assertEqual(response.status_code, 503)

    def test_rejection_is_sanitized(self):
        self.repo.error = ItemUseRejectedError("ITEM_USE_FORBIDDEN", 403)
        response = self.client.put(
            f"/v1/launcher/seasons/{SEASON_ID}/item-uses/{AUTHORIZATION_ID}",
            headers=self.headers,
            json={"operation_id": "item-op-1", "status": "RECOVERY_REQUIRED"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "ITEM_USE_FORBIDDEN")

    def test_authentication_is_required_before_repository(self):
        self.verifier.fail = InvalidSessionError()
        response = self.client.get(
            f"/v1/launcher/seasons/{SEASON_ID}/item-uses", headers=self.headers
        )
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.repo.completed)

    def test_sql_keeps_purchase_pending_until_verified_completion(self):
        sql = Path("supabase/v2/migrations/054_item_use_authorizations.sql").read_text(
            encoding="utf-8"
        )
        prepare = sql.split("create function public.api_prepare_item_use", 1)[1].split(
            "create function public.api_complete_item_use", 1
        )[0]
        complete = sql.split("create function public.api_complete_item_use", 1)[1]
        self.assertNotIn("update public.purchases", prepare.lower())
        self.assertIn("p_status<>'applied_verified'", complete.lower())
        self.assertIn("api_redeem_purchase", complete)
        self.assertIn("item_use_forbidden", complete)
        self.assertIn("force row level security", sql.lower())
        self.assertLess(
            complete.index("from public.seasons where id=v_auth.season_id"),
            complete.index(
                "from public.season_players where season_id=v_auth.season_id"
            ),
        )
        self.assertLess(
            complete.index(
                "from public.season_players where season_id=v_auth.season_id"
            ),
            complete.index(
                "from public.item_use_authorizations "
                "where id=p_authorization_id for update"
            ),
        )

    def test_domain_rejects_noncanonical_save_hash(self):
        with self.assertRaises(ValueError):
            ItemUsePrepareRequest(
                SEASON_ID,
                TRAINER_ID,
                PURCHASE_ID,
                POKEMON_ID,
                SAVE_ID,
                "A" * 64,
                "prepare-key",
                "item-op-1",
            )


if __name__ == "__main__":
    unittest.main()
