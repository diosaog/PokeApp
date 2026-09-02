from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_supabase_v2_rls.py"
ENV_EXAMPLE = ROOT / ".env.supabase-v2-rls.example"


def _load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_supabase_v2_rls", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SupabaseV2RlsValidatorTests(unittest.TestCase):
    def test_validator_exists_and_does_not_embed_secrets(self) -> None:
        source = VALIDATOR.read_text(encoding="utf-8")

        self.assertIn("POKEAPP_V2_SUPABASE_URL", source)
        self.assertIn("POKEAPP_V2_SUPABASE_ANON_KEY", source)
        self.assertIn("POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY", source)
        self.assertIn("auth.uid", source)
        self.assertIn("raw-saves", source)
        self.assertIn("secrets=redacted", source)
        self.assertNotIn("https://", source)

    def test_rpc_calls_use_the_real_rpc_path(self) -> None:
        module = _load_validator_module()
        config = module.Config(
            url="https://example.supabase.co",
            anon_key="anon",
            service_role_key="service",
            email_domain="example.com",
            cleanup=True,
            run_id="run",
        )
        api = module.SupabaseHttp(config)
        api.request = Mock(return_value=module.HttpResult(200, {"ok": True}, "{}", {}))

        result = api.rpc("current_auth_uid", auth="service")

        self.assertEqual(result, {"ok": True})
        api.request.assert_called_once_with(
            "POST",
            "https://example.supabase.co/rest/v1/rpc/current_auth_uid",
            auth="service",
            body={},
        )

    def test_env_example_contains_only_placeholders(self) -> None:
        source = ENV_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("POKEAPP_V2_SUPABASE_URL=", source)
        self.assertIn("your-project-ref", source)
        self.assertIn("your-service-role-key", source)


if __name__ == "__main__":
    unittest.main()
