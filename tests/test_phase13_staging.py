"""Safety of the opt-in staging transport, without starting any database/server."""

from types import SimpleNamespace
import unittest

import jwt

from app.auth.errors import InvalidCredentialsError
from tools.phase13_staging import PEPPER, StagingClient, SyntheticAuth, uid


class StagingSafetyTests(unittest.TestCase):
    def test_hosted_or_unrelated_database_is_rejected_before_access(self):
        for host, database in (
            ("db.example.test", "pokeapp_v2_validation_phase13_test"),
            ("127.0.0.1", "postgres"),
            ("127.0.0.1", "pokeapp_v2_validation_phase11_test"),
        ):
            with (
                self.subTest(host=host, database=database),
                self.assertRaises(ValueError),
            ):
                StagingClient(SimpleNamespace(host=host, database=database))

    def test_local_auth_still_requires_signature_expiry_audience_and_known_user(self):
        auth = SyntheticAuth()
        token = auth.session(uid("Alia/auth")).access_token
        self.assertEqual(auth.get_user(access_token=token).user_id, uid("Alia/auth"))
        invalid = (
            "forged",
            jwt.encode(
                {"sub": uid("Alia/auth"), "aud": "phase13-local"},
                PEPPER,
                algorithm="HS256",
            ),
            jwt.encode(
                {"sub": uid("Alia/auth"), "exp": 1, "aud": "phase13-local"},
                PEPPER,
                algorithm="HS256",
            ),
            jwt.encode(
                {"sub": uid("Alia/auth"), "aud": "production"},
                PEPPER,
                algorithm="HS256",
            ),
            jwt.encode(
                {"sub": uid("unknown"), "aud": "phase13-local"},
                PEPPER,
                algorithm="HS256",
            ),
            jwt.encode(
                {"sub": uid("Alia/auth"), "aud": "phase13-local"},
                "different-synthetic-key-with-enough-length",
                algorithm="HS256",
            ),
        )
        for token in invalid:
            with self.assertRaises(InvalidCredentialsError):
                auth.get_user(access_token=token)
