import unittest
from unittest.mock import patch

from app.api.serve import main
from app.auth.keyring import KeyringConfigurationError


class VersionedStartupTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "POKEAPP_V2_SUPABASE_URL": "https://fixture.supabase.co",
            "POKEAPP_V2_SUPABASE_ANON_KEY": "synthetic-publishable",
            "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY": "synthetic-private",
            "POKEAPP_API_CORS_ORIGINS": "https://fixture.invalid",
            "POKEAPP_AUTH_PIN_PEPPER_V2": "synthetic-password-key-00000000001",
            "POKEAPP_ACCOUNT_INTENT_KEY_V2": "synthetic-intent-key-000000000002",
            "POKEAPP_ACCOUNT_THROTTLE_KEY": "synthetic-throttle-key-0000000003",
            "POKEAPP_AUTH_PIN_V1_DEADLINE": "2026-10-24T00:00:00Z",
        }

    def test_v2_only_starts_without_retired_pepper(self):
        with (
            patch.dict("os.environ", self.env, clear=True),
            patch("uvicorn.run") as run,
        ):
            main()
        self.assertEqual(run.call_count, 1)
        self.assertFalse(run.call_args.kwargs["proxy_headers"])

    def test_legacy_pepper_alone_cannot_start_new_runtime(self):
        env = {
            k: v
            for k, v in self.env.items()
            if not any(s in k for s in ("_V2", "THROTTLE", "DEADLINE"))
        }
        env.update(
            {k: v for k, v in self.env.items() if k.startswith("POKEAPP_V2_SUPABASE")}
        )
        env["POKEAPP_AUTH_PIN_PEPPER"] = "synthetic-legacy"
        with patch.dict("os.environ", env, clear=True), patch("uvicorn.run") as run:
            with self.assertRaises(SystemExit):
                main()
        run.assert_not_called()

    def test_partial_keyring_fails_closed(self):
        del self.env["POKEAPP_ACCOUNT_INTENT_KEY_V2"]
        with (
            patch.dict("os.environ", self.env, clear=True),
            patch("uvicorn.run") as run,
        ):
            with self.assertRaises(KeyringConfigurationError):
                main()
        run.assert_not_called()

    def test_missing_supabase_service_key_still_denied(self):
        del self.env["POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY"]
        with (
            patch.dict("os.environ", self.env, clear=True),
            patch("uvicorn.run") as run,
        ):
            with self.assertRaises(SystemExit):
                main()
        run.assert_not_called()
