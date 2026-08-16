from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_supabase_v2_rls.py"
ENV_EXAMPLE = ROOT / ".env.supabase-v2-rls.example"


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

    def test_env_example_contains_only_placeholders(self) -> None:
        source = ENV_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("POKEAPP_V2_SUPABASE_URL=", source)
        self.assertIn("your-project-ref", source)
        self.assertIn("your-service-role-key", source)


if __name__ == "__main__":
    unittest.main()
