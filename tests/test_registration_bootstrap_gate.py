import hashlib
import unittest
from unittest.mock import Mock
from uuid import uuid4

from app.auth.accounts import AccountError, AccountService
from app.auth.versioned_accounts import VersionedAccountService
from app.api.config import APIConfig
from tests.test_accounts_registration import Repository, Auth


class BootstrapGateTests(unittest.TestCase):
    def test_versioned_registration_rejects_before_any_repository_or_auth_effect(self):
        repo, auth = Mock(), Mock()
        service = VersionedAccountService(
            repo,
            auth,
            keyring=Mock(),
            enabled=True,
            access_code="fictional-invitation",
            bootstrap_hash=hashlib.sha256(b"owner-only").hexdigest(),
        )
        for token in ("", "wrong"):
            with self.assertRaises(AccountError):
                service.register(
                    uuid4(), "Anto", "1234", "1234", "fictional-invitation", token
                )
        self.assertEqual(repo.mock_calls, [])
        self.assertEqual(auth.mock_calls, [])

    def test_controlled_access_never_elevates_registration(self):
        repo = Repository()
        service = AccountService(
            repo,
            Auth(),
            pepper="fake",
            enabled=True,
            access_code="fictional-invitation",
            bootstrap_hash=hashlib.sha256(b"owner-only").hexdigest(),
        )
        row = service.register(
            uuid4(), "Anto", "1234", "1234", "fictional-invitation", "owner-only"
        )
        self.assertFalse(repo.trainers[row["trainer_id"]]["admin"])

    def test_bootstrap_does_not_replace_the_invitation(self):
        service = AccountService(
            Mock(),
            Mock(),
            pepper="fake",
            enabled=True,
            access_code="fictional-invitation",
            bootstrap_hash=hashlib.sha256(b"owner-only").hexdigest(),
        )
        with self.assertRaises(AccountError):
            service.check_registration_access("wrong", "owner-only")

    def test_invalid_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            AccountService(Mock(), Mock(), pepper="fake", bootstrap_hash="invalid")
        cfg = APIConfig.from_env({"POKEAPP_REGISTRATION_BOOTSTRAP_HASH": "a" * 64})
        self.assertEqual(cfg.registration_bootstrap_hash, "a" * 64)
        self.assertNotIn("a" * 64, repr(cfg))
