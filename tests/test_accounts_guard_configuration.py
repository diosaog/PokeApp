"""The session/RLS guard service must outlive removal of the PIN secret."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.config import APIConfig
from app.api.dependencies import create_default_container
from app.api.main import create_app
from app.auth.keyring import KeyringConfigurationError
from app.auth.versioned_accounts import VersionedAccountService
from test_api_phase8b import (
    FakePrincipalRepository,
    FakeSessionRefresher,
    FakeTokenVerifier,
)


class GuardConfigurationTests(unittest.TestCase):
    def test_default_runtime_uses_versioned_service_and_independent_registration_flag(
        self,
    ):
        config = APIConfig.from_env(
            {
                "POKEAPP_V2_SUPABASE_URL": "https://example.invalid",
                "POKEAPP_V2_SUPABASE_ANON_KEY": "sb_publishable_synthetic",
                "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY": "sb_secret_synthetic",
                "POKEAPP_AUTH_PIN_PEPPER_V2": "synthetic-password-key-00000000001",
                "POKEAPP_ACCOUNT_INTENT_KEY_V2": "synthetic-intent-key-0000000000002",
                "POKEAPP_ACCOUNT_THROTTLE_KEY": "synthetic-throttle-key-0000000003",
                "POKEAPP_AUTH_PIN_V1_DEADLINE": "2026-10-24T00:00:00+00:00",
                "POKEAPP_ACCOUNT_MANAGEMENT_ENABLED": "true",
                "POKEAPP_REGISTRATION_ACCESS_CODE": "synthetic-private-invitation",
            }
        )
        with patch(
            "httpx.Client.send", side_effect=AssertionError("Network forbidden")
        ):
            container = create_default_container(config)
            self.assertIsInstance(container.account_service, VersionedAccountService)
            self.assertIsNotNone(container.auth_bridge)
            self.assertTrue(container.account_service.registration_enabled)
            self.assertIsNone(container.account_service.keyring.v1_pepper)
            disabled_registration = create_default_container(
                replace(config, registration_access_code="")
            )
            self.assertFalse(disabled_registration.account_service.registration_enabled)
            self.assertTrue(disabled_registration.account_service.enabled)
        self.assertNotIn("synthetic-private-invitation", repr(config))

    def test_partial_versioned_configuration_never_falls_back(self):
        with self.assertRaises(KeyringConfigurationError):
            APIConfig.from_env(
                {
                    "POKEAPP_AUTH_PIN_PEPPER_V2": "synthetic-key",
                    "POKEAPP_AUTH_PIN_PEPPER": "synthetic-old",
                }
            )

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
                    {
                        "enabled": False,
                        "registration_enabled": False,
                        "renewal_enabled": False,
                        "bootstrap_required": False,
                    },
                )


if __name__ == "__main__":
    unittest.main()
