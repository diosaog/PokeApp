"""Synthetic-only SEC-PIN-01 foundation checks; no live Auth or key material."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import unittest

from app.auth.credentials import build_internal_auth_credential
from app.auth.config import credential_keyring_from_env
from app.auth.errors import InvalidCredentialsError
from app.auth.keyring import (
    CredentialKeyring,
    CredentialRenewalRequired,
    CredentialState,
    IntentReconciliationRequired,
    IntentVersions,
    KeyringConfigurationError,
)


TRAINER = "00000000-0000-4000-8000-000000000001"
NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
CUTOFF = NOW + timedelta(hours=1)


class CredentialKeyringTests(unittest.TestCase):
    def setUp(self):
        self.ring = CredentialKeyring(
            legacy_deadline=CUTOFF,
            v1_pepper="synthetic-legacy-test-pepper",
            v2_pepper="synthetic-password-v2-test-key-0001",
            intent_key="synthetic-journal-v2-test-key-0002",
            throttle_key="synthetic-counter-v2-test-key-0003",
        )

    def credential(self, version=2, **kw):
        return self.ring.credential(
            TRAINER, "0012", CredentialState(version, False), now=kw.get("now", NOW)
        )

    def test_v1_is_exactly_compatible_before_cutoff(self):
        self.assertEqual(
            self.credential(1),
            build_internal_auth_credential(TRAINER, "0012", self.ring.v1_pepper),
        )

    def test_v2_preserves_identity_but_separates_password(self):
        first, second = self.credential(1), self.credential(2)
        self.assertEqual(first.trainer_id, second.trainer_id)
        self.assertEqual(first.email, second.email)
        self.assertNotEqual(first.password, second.password)
        changed = self.ring.credential(
            TRAINER, "0120", CredentialState(2, False), now=NOW
        )
        self.assertNotEqual(second.password, changed.password)

    def test_no_legacy_fallback_after_v2_selection(self):
        retired = replace(self.ring, v1_pepper=None)
        self.assertEqual(
            retired.credential(TRAINER, "0012", CredentialState(2, False), now=CUTOFF),
            self.credential(2),
        )
        with self.assertRaises(CredentialRenewalRequired):
            retired.credential(TRAINER, "0012", CredentialState(1, False), now=NOW)

    def test_cutoff_is_exclusive_and_v2_survives(self):
        self.credential(1, now=CUTOFF - timedelta(microseconds=1))
        for when in (CUTOFF, CUTOFF + timedelta(days=1)):
            with self.assertRaises(CredentialRenewalRequired):
                self.credential(1, now=when)
            self.assertEqual(self.credential(2, now=when), self.credential(2))

    def test_reset_required_and_missing_state_fail_closed(self):
        for state in (None, CredentialState(1, True), CredentialState(2, True)):
            with self.assertRaises(CredentialRenewalRequired):
                self.ring.credential(TRAINER, "0012", state, now=NOW)

    def test_no_inferred_version_or_truthy_reset_flag(self):
        for bad in (None, 0, 3, True, "1", 1.0):
            with self.assertRaises(KeyringConfigurationError):
                CredentialState(bad, False)
        with self.assertRaises(KeyringConfigurationError):
            CredentialState(2, "false")

    def test_pin_is_ascii_exact_four_digits(self):
        for bad in (12, None, "012", "00012", " 0012", "１２３４"):
            with self.assertRaises(InvalidCredentialsError):
                self.ring.credential(TRAINER, bad, CredentialState(2, False), now=NOW)

    def test_explicit_timezone_required_and_offsets_normalized(self):
        with self.assertRaises(KeyringConfigurationError):
            replace(self.ring, legacy_deadline=CUTOFF.replace(tzinfo=None))
        with self.assertRaises(KeyringConfigurationError):
            self.credential(1, now=NOW.replace(tzinfo=None))
        offset = CUTOFF.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(
            replace(self.ring, legacy_deadline=offset).legacy_deadline, CUTOFF
        )

    def test_key_purposes_must_be_separate_and_nonempty(self):
        for field in ("v2_pepper", "intent_key", "throttle_key"):
            for bad in (None, "", "short", self.ring.v1_pepper):
                with self.assertRaises(KeyringConfigurationError):
                    replace(self.ring, **{field: bad})
        with self.assertRaises(KeyringConfigurationError):
            replace(self.ring, intent_key=self.ring.v2_pepper)
        with self.assertRaises(KeyringConfigurationError):
            replace(self.ring, v1_pepper="")

    def test_secrets_are_redacted_from_representations_and_errors(self):
        rendered = repr(self.ring) + repr(self.credential())
        for key in (
            self.ring.v1_pepper,
            self.ring.v2_pepper,
            self.ring.intent_key,
            self.ring.throttle_key,
        ):
            self.assertNotIn(key, rendered)
        self.assertNotIn(self.credential().password, rendered)
        with self.assertRaises(KeyringConfigurationError) as error:
            replace(self.ring, v1_pepper=self.ring.v2_pepper)
        self.assertNotIn(self.ring.v2_pepper, str(error.exception))

    def test_legacy_intent_hmac_is_exactly_compatible(self):
        payload = ["pin-change", "operation", "0001", "0002", None]
        versions = IntentVersions(1, 1, CUTOFF)
        expected = hmac.new(
            self.ring.v1_pepper.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(
            self.ring.intent_fingerprint(payload, versions, now=NOW), expected
        )

    def test_legacy_intent_cannot_outlive_cutoff_even_with_v2_hmac(self):
        for epochs in ((1, 1), (1, 2), (2, 1)):
            versions = IntentVersions(*epochs, CUTOFF + timedelta(days=1))
            with self.assertRaises(IntentReconciliationRequired):
                self.ring.intent_fingerprint(["synthetic"], versions, now=CUTOFF)

    def test_v2_intent_survives_removal_of_old_pepper(self):
        versions = IntentVersions(2, 2, CUTOFF + timedelta(days=1))
        expected = self.ring.intent_fingerprint(["synthetic"], versions, now=NOW)
        retired = replace(self.ring, v1_pepper=None)
        self.assertEqual(
            retired.intent_fingerprint(["synthetic"], versions, now=CUTOFF), expected
        )
        with self.assertRaises(IntentReconciliationRequired):
            retired.intent_fingerprint([], IntentVersions(2, 1, CUTOFF), now=NOW)

    def test_intents_always_expire_including_v2(self):
        for epochs in ((1, 1), (2, 2)):
            with self.assertRaises(IntentReconciliationRequired):
                self.ring.intent_fingerprint([], IntentVersions(*epochs, NOW), now=NOW)

    def test_new_intent_hash_binds_versions_and_expiry(self):
        versions = IntentVersions(2, 2, CUTOFF)
        original = self.ring.intent_fingerprint([], versions, now=NOW)
        for changed in (
            replace(versions, credential_version=1),
            replace(versions, expires_at=CUTOFF + timedelta(minutes=1)),
        ):
            self.assertNotEqual(
                original, self.ring.intent_fingerprint([], changed, now=NOW)
            )

    def test_new_password_does_not_change_intent_or_throttle_keys(self):
        versions = IntentVersions(2, 2, CUTOFF)
        before = self.ring
        self.ring = replace(before, v2_pepper="synthetic-next-password-key-00004")
        self.assertNotEqual(
            self.credential().password,
            before.credential(
                TRAINER, "0012", CredentialState(2, False), now=NOW
            ).password,
        )
        self.assertEqual(
            before.intent_fingerprint([], versions, now=NOW),
            self.ring.intent_fingerprint([], versions, now=NOW),
        )
        self.assertEqual(
            before.throttle_fingerprint("login", TRAINER),
            self.ring.throttle_fingerprint("login", TRAINER),
        )

    def test_intent_rotation_does_not_reset_counter_identity(self):
        new = replace(
            self.ring, intent_key="synthetic-next-journal-key-000005", v1_pepper=None
        )
        self.assertEqual(
            new.throttle_fingerprint("login", TRAINER),
            self.ring.throttle_fingerprint("login", TRAINER),
        )
        self.assertNotEqual(
            new.throttle_fingerprint("login", TRAINER),
            new.throttle_fingerprint("reset", TRAINER),
        )

    def test_explicit_configuration_has_no_live_or_legacy_fallback(self):
        source = {
            "POKEAPP_AUTH_PIN_V1_DEADLINE": CUTOFF.isoformat(),
            "POKEAPP_AUTH_PIN_PEPPER_V2": self.ring.v2_pepper,
            "POKEAPP_ACCOUNT_INTENT_KEY_V2": self.ring.intent_key,
            "POKEAPP_ACCOUNT_THROTTLE_KEY": self.ring.throttle_key,
        }
        retired = credential_keyring_from_env(source)
        self.assertIsNone(retired.v1_pepper)
        self.assertEqual(
            retired.credential(TRAINER, "0012", CredentialState(2, False), now=NOW),
            self.credential(),
        )
        for required in source:
            with self.assertRaises(KeyringConfigurationError):
                credential_keyring_from_env(
                    {k: v for k, v in source.items() if k != required}
                )
        with self.assertRaises(KeyringConfigurationError):
            credential_keyring_from_env(
                {"POKEAPP_AUTH_PIN_PEPPER": self.ring.v1_pepper}
            )
        with self.assertRaises(KeyringConfigurationError) as error:
            credential_keyring_from_env(
                {**source, "POKEAPP_AUTH_PIN_V1_DEADLINE": self.ring.v2_pepper}
            )
        self.assertNotIn(self.ring.v2_pepper, str(error.exception))


if __name__ == "__main__":
    unittest.main()
