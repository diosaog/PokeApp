from dataclasses import replace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier


class AdminService:
    enabled = True

    def __init__(self):
        self.calls = []

    def valid_session(self, *args):
        return True

    def throttle(self, *args):
        pass

    def admin_accounts(self, actor, offset):
        self.calls.append((actor, offset))
        return dict(
            items=[
                dict(
                    trainer_id=TRAINER_ID,
                    display_name="Owner",
                    globally_enabled=True,
                    is_admin=True,
                    revision=0,
                    provisioned=True,
                )
            ],
            offset=offset,
            has_more=False,
        )

    def admin_status(self, actor, target, operation, revision, enabled):
        self.calls.append((actor, target, revision, enabled))
        return dict(trainer_id=target, revision=revision + 1, globally_enabled=enabled)

    def change_pin(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return dict(status="changed", sign_in_required=True)


class AdminAccountsTests(unittest.TestCase):
    def client(self, admin=True, enabled=True):
        repo = FakePrincipalRepository()
        repo.trainer = replace(repo.trainer, is_admin=admin, globally_enabled=enabled)
        self.service = AdminService()
        return TestClient(
            create_app(
                container=ApiContainer(
                    account_service=self.service,
                    principal_repository=repo,
                    token_verifier=FakeTokenVerifier(),
                )
            )
        )

    def test_admin_list_hides_auth_identity(self):
        response = self.client().get(
            "/v1/admin/accounts", headers={"Authorization": "Bearer dummy"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("auth_user_id", response.text)

    def test_non_admin_and_disabled_admin_denied_all_routes(self):
        target = str(uuid4())
        for admin, enabled in ((False, True), (True, False)):
            client = self.client(admin, enabled)
            headers = {"Authorization": "Bearer dummy", "Idempotency-Key": str(uuid4())}
            responses = [
                client.get("/v1/admin/accounts", headers=headers),
                client.put(
                    f"/v1/admin/accounts/{target}/status",
                    headers=headers,
                    json={"enabled": False, "expected_revision": 0},
                ),
                client.post(
                    f"/v1/admin/accounts/{target}/reset-pin",
                    headers=headers,
                    json={"new_pin": "0071", "confirmation": "0071"},
                ),
            ]
            self.assertTrue(all(r.status_code == 403 for r in responses))
            self.assertEqual(self.service.calls, [])

    def test_status_identity_comes_from_verified_principal(self):
        client = self.client()
        target = str(uuid4())
        response = client.put(
            f"/v1/admin/accounts/{target}/status",
            headers={"Authorization": "Bearer dummy", "Idempotency-Key": str(uuid4())},
            json={"enabled": False, "expected_revision": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.calls, [(TRAINER_ID, target, 2, False)])

    def test_role_injection_and_delete_have_no_contract(self):
        client = self.client()
        target = str(uuid4())
        headers = {"Authorization": "Bearer dummy", "Idempotency-Key": str(uuid4())}
        self.assertEqual(
            client.put(
                f"/v1/admin/accounts/{target}/status",
                headers=headers,
                json={"enabled": True, "expected_revision": 0, "is_admin": True},
            ).status_code,
            422,
        )
        self.assertEqual(
            client.delete(f"/v1/admin/accounts/{target}", headers=headers).status_code,
            404,
        )
        self.assertEqual(self.service.calls, [])

    def test_admin_reset_is_targeted_and_self_requires_current_pin(self):
        client = self.client()
        headers = {"Authorization": "Bearer dummy", "Idempotency-Key": str(uuid4())}
        body = {
            "new_pin": "0071",
            "confirmation": "0071",
            "renewal_token": "synthetic-renewal-" + "x" * 48,
        }
        self.assertEqual(
            client.post(
                f"/v1/admin/accounts/{TRAINER_ID}/reset-pin", headers=headers, json=body
            ).status_code,
            403,
        )
        target = str(uuid4())
        r = client.post(
            f"/v1/admin/accounts/{target}/reset-pin", headers=headers, json=body
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("0071", r.text)
        self.assertEqual(
            self.service.calls[-1][1],
            {"target": target, "renewal_token": body["renewal_token"]},
        )
