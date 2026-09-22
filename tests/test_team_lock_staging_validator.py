import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.validate_supabase_v2_rls import HttpResult, ValidationError
from tools.validate_supabase_v2_team_lock import STAGING_URL, direct_write_denied, staging_config


class TeamLockStagingValidatorTests(unittest.TestCase):
    def test_explicit_write_opt_in_is_required_before_loading_credentials(self):
        with patch("tools.validate_supabase_v2_team_lock._load_env_file") as load:
            with self.assertRaises(ValidationError):
                staging_config(Path("unused"), False)
            load.assert_not_called()

    def test_only_approved_v2_staging_host_is_allowed(self):
        for url in ("https://other.supabase.co", "http://localhost:54321", STAGING_URL + "/rest/v1"):
            with self.subTest(url=url), patch.dict(os.environ, {"POKEAPP_V2_SUPABASE_URL": url}, clear=True):
                with patch("tools.validate_supabase_v2_team_lock._load_env_file"), self.assertRaises(ValidationError):
                    staging_config(Path("unused"), True)

    def test_approved_config_uses_unique_fixture_prefix_and_cleanup(self):
        values = {"POKEAPP_V2_SUPABASE_URL": STAGING_URL,
                  "POKEAPP_V2_SUPABASE_ANON_KEY": "dummy-public",
                  "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY": "dummy-private"}
        with patch.dict(os.environ, values, clear=True), patch("tools.validate_supabase_v2_team_lock._load_env_file"):
            first = staging_config(Path("unused"), True)
            second = staging_config(Path("unused"), True)
        self.assertTrue(first.cleanup)
        self.assertTrue(first.run_id.startswith("phase8c_validation_"))
        self.assertNotEqual(first.run_id, second.run_id)

    def test_rls_filtered_update_is_a_denial_not_a_write(self):
        empty = HttpResult(200, [], "[]", {})
        self.assertTrue(direct_write_denied("PATCH", empty))
        self.assertFalse(direct_write_denied("POST", empty))
        self.assertFalse(direct_write_denied("PATCH", HttpResult(200, [{"id": "changed"}], "", {})))
        self.assertFalse(direct_write_denied("PATCH", HttpResult(204, None, "", {})))

    def test_constraint_backend_and_missing_rpc_errors_are_not_security_success(self):
        for status in (400, 404, 409, 500, 503):
            self.assertFalse(direct_write_denied("PATCH", HttpResult(status, {}, "", {})))
        self.assertTrue(direct_write_denied("POST", HttpResult(403, {}, "", {})))


if __name__ == "__main__":
    unittest.main()
