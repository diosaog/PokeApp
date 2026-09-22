from dataclasses import replace
import json
import unittest

from fastapi import Depends
from fastapi.testclient import TestClient
import httpx
from postgrest import SyncPostgrestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.api.supabase_repository import SupabaseTrainerAuthRepository
from app.auth.errors import AuthBackendError
from app.auth.service import PinAuthBridge
from test_api_phase8b import AUTH_USER_ID, TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier


ROW = dict(id=TRAINER_ID, auth_user_id=AUTH_USER_ID, display_name="Antonio", slug="anto", globally_enabled=True, is_admin=True)


class AuthHardeningTests(unittest.TestCase):
    def repository(self, rows=None, *, status=200):
        self.requests = []

        def respond(request):
            self.requests.append(request)
            return httpx.Response(status, json=rows if rows is not None else [ROW])

        client = SyncPostgrestClient("https://example.invalid/rest/v1")
        client.session = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(client.session.close)
        return SupabaseTrainerAuthRepository(client)

    def test_h01_update_uses_real_sdk_and_exact_primary_key(self):
        trainer = self.repository().set_auth_user_id(TRAINER_ID, AUTH_USER_ID)
        request = self.requests[0]
        self.assertEqual(request.method, "PATCH")
        self.assertEqual(dict(request.url.params), {"id": "eq." + TRAINER_ID})
        self.assertEqual(json.loads(request.content), {"auth_user_id": AUTH_USER_ID})
        self.assertIn("return=representation", request.headers["Prefer"])
        self.assertEqual(trainer.auth_user_id, AUTH_USER_ID)

    def test_h02_no_row_or_ambiguous_or_wrong_mapping_is_not_success(self):
        for rows in ([], [ROW, ROW], [dict(ROW, auth_user_id=TRAINER_ID)], [dict(ROW, id=AUTH_USER_ID)]):
            with self.subTest(rows=len(rows)), self.assertRaises(AuthBackendError):
                self.repository(rows).set_auth_user_id(TRAINER_ID, AUTH_USER_ID)

    def test_h03_slug_never_queries_uuid_column(self):
        self.assertEqual(self.repository().find_for_login(" Anto ").id, TRAINER_ID)
        self.assertEqual(self.requests[0].url.params["slug"], "eq.anto")
        self.assertNotIn("id", self.requests[0].url.params)

    def test_h04_uuid_queries_primary_key(self):
        self.assertEqual(self.repository().find_for_login(TRAINER_ID).id, TRAINER_ID)
        self.assertEqual(self.requests[0].url.params["id"], "eq." + TRAINER_ID)
        self.assertNotIn("slug", self.requests[0].url.params)

    def test_h05_missing_slug_and_blank_identifier(self):
        repo = self.repository([])
        self.assertIsNone(repo.find_for_login("unknown"))
        self.assertIsNone(repo.find_for_login(" "))
        self.assertEqual(len(self.requests), 1)

    def mutation_client(self, enabled=True):
        repo = FakePrincipalRepository()
        repo.trainer = replace(repo.trainer, globally_enabled=enabled)
        app = create_app(container=ApiContainer(token_verifier=FakeTokenVerifier(), principal_repository=repo))

        @app.put("/test-mutation")
        def mutation(principal=Depends(require_enabled_principal)):
            return {"trainer_id": principal.trainer_id}

        return TestClient(app)

    def test_h06_enabled_principal_can_mutate(self):
        response = self.mutation_client().put("/test-mutation", headers={"Authorization": "Bearer dummy"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"trainer_id": TRAINER_ID})

    def test_h07_disabled_admin_cannot_mutate(self):
        response = self.mutation_client(False).put("/test-mutation", headers={"Authorization": "Bearer dummy"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "TRAINER_DISABLED")

    def test_h08_disabled_principal_can_still_read_me(self):
        response = self.mutation_client(False).get("/v1/me", headers={"Authorization": "Bearer dummy"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["globally_enabled"])

    def test_h09_backend_errors_are_typed_chained_and_not_exposed(self):
        secret = "dummy-private-backend-detail"
        repo = self.repository({"code": "22P02", "message": secret, "hint": None, "details": None}, status=400)
        with self.assertRaises(AuthBackendError) as caught:
            repo.find_for_login("anto")
        self.assertIsNotNone(caught.exception.__cause__)
        self.assertNotIn(secret, str(caught.exception))
        app = create_app(container=ApiContainer(
            auth_bridge=PinAuthBridge(trainers=repo, auth=None, pepper="dummy-pepper"),
            token_verifier=FakeTokenVerifier(), principal_repository=repo,
        ))
        client = TestClient(app)
        responses = [
            client.post("/v1/auth/pin-login", json={"trainer_identifier": "anto", "pin": "0042"}),
            client.get("/v1/me", headers={"Authorization": "Bearer dummy"}),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 503)
            for value in (secret, "dummy-pepper", "service_role", "0042"):
                self.assertNotIn(value, response.text)

    def test_update_failure_is_chained_backend_error(self):
        repo = self.repository({"code": "23505", "message": "dummy SQL detail", "hint": None, "details": None}, status=409)
        with self.assertRaises(AuthBackendError) as caught:
            repo.set_auth_user_id(TRAINER_ID, AUTH_USER_ID)
        self.assertIsNotNone(caught.exception.__cause__)
