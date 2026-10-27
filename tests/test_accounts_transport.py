import json
from uuid import uuid4
import unittest

import httpx
from supabase_auth._sync.gotrue_admin_api import SyncGoTrueAdminAPI
from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.supabase.accounts import SupabaseAccountAuth
from app.auth.errors import AuthBackendError


class AccountTransportTests(unittest.TestCase):
    def test_real_admin_sdk_preserves_reserved_uuid_and_server_metadata(self):
        uid = str(uuid4())
        calls = []
        user = dict(
            id=uid,
            email="trainer-test@auth.pokeapp.invalid",
            app_metadata={"pokeapp_registration": "marker"},
            user_metadata={},
            aud="authenticated",
            role="authenticated",
            created_at="2026-01-01T00:00:00Z",
        )

        def respond(request):
            calls.append(request)
            if request.url.path.endswith("/logout"):
                return httpx.Response(204)
            return httpx.Response(200, json=user)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            adapter = SupabaseAccountAuth(
                SyncGoTrueAdminAPI(
                    url="https://example.invalid/auth/v1", http_client=client
                )
            )
            adapter.create(uid, user["email"], "derived-test-password", "marker")
            self.assertEqual(json.loads(calls[0].content)["id"], uid)
            self.assertEqual(
                json.loads(calls[0].content)["app_metadata"],
                {"pokeapp_registration": "marker"},
            )
            self.assertNotIn("role", json.loads(calls[0].content))
            self.assertEqual(adapter.lookup(uid)["id"], uid)
            adapter.password(uid, "new-derived-test-password")
            self.assertEqual(
                json.loads(calls[-1].content), {"password": "new-derived-test-password"}
            )
            adapter.revoke("temporary-token")
            self.assertEqual(calls[-1].url.params["scope"], "global")

    def test_admin_not_found_is_distinct_from_unauthorized_or_outage(self):
        for status in (404, 401, 503):
            with httpx.Client(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(status, json={"msg": "fixture"})
                )
            ) as client:
                adapter = SupabaseAccountAuth(
                    SyncGoTrueAdminAPI(
                        url="https://example.invalid/auth/v1", http_client=client
                    )
                )
                if status == 404:
                    self.assertIsNone(adapter.lookup(str(uuid4())))
                else:
                    with self.assertRaises(AuthBackendError):
                        adapter.lookup(str(uuid4()))

    def test_capability_off_default_and_register_requires_explicit_container(self):
        client = TestClient(create_app(container=ApiContainer()))
        # The contract grew registration/renewal/bootstrap flags: all stay off
        # without an explicitly configured account service.
        self.assertEqual(
            client.get("/v1/auth/account-capabilities").json(),
            {
                "enabled": False,
                "registration_enabled": False,
                "renewal_enabled": False,
                "bootstrap_required": False,
            },
        )
        response = client.post(
            "/v1/auth/register",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "trainer_name": "test",
                "pin": "0073",
                "confirmation": "0073",
                "access_code": "anything",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("0073", response.text)
