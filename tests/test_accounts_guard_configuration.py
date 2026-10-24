"""The session/RLS guard service must outlive removal of the PIN secret."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.config import APIConfig
from app.api.dependencies import create_default_container
from app.api.main import create_app
from test_api_phase8b import (
    FakePrincipalRepository,
    FakeSessionRefresher,
    FakeTokenVerifier,
)


class GuardConfigurationTests(unittest.TestCase):
    def test_missing_pepper_never_removes_guard_service(self):
        for flag in (False, True):
            with (
                self.subTest(flag=flag),
                patch(
                    "httpx.Client.send", side_effect=AssertionError("Network forbidden")
                ),
            ):
                container = create_default_container(
                    APIConfig(
                        supabase_url="https://example.invalid",
                        supabase_anon_key="sb_publishable_synthetic_test_only",
                        supabase_service_role_key="sb_secret_synthetic_test_only",
                        auth_pin_pepper="",
                        account_management_enabled=flag,
                    )
                )
            self.assertIsNotNone(container.account_service)
            self.assertFalse(container.account_service.enabled)
            self.assertIsNone(container.auth_bridge)
            # Verifier/principal fixtures provide a valid signed-in account;
            # only the persisted session decision is denied, no external calls.
            with patch.object(
                container.account_service.repository, "rpc", return_value=False
            ) as guard:
                client = self.enterContext(
                    TestClient(
                        create_app(
                            config=APIConfig(),
                            container=replace(
                                container,
                                token_verifier=FakeTokenVerifier(),
                                principal_repository=FakePrincipalRepository(),
                                session_refresher=FakeSessionRefresher(),
                            ),
                        )
                    )
                )
                response = client.get(
                    "/v1/me", headers={"Authorization": "Bearer valid-token"}
                )
                self.assertEqual(response.status_code, 401)
                guard.assert_called_once()
                self.assertEqual(guard.call_args.args[0], "account_session_allowed")
                self.assertEqual(
                    client.post(
                        "/v1/auth/refresh",
                        json={"refresh_token": "synthetic-refresh"},
                    ).status_code,
                    401,
                )
                guard.return_value = True
                self.assertEqual(
                    client.get(
                        "/v1/me", headers={"Authorization": "Bearer valid-token"}
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    client.post(
                        "/v1/auth/refresh",
                        json={"refresh_token": "synthetic-refresh"},
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    client.get("/v1/auth/account-capabilities").json(),
                    {"enabled": False},
                )


if __name__ == "__main__":
    unittest.main()
