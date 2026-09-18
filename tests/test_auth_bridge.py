from __future__ import annotations

import unittest

from app.auth import (
    AuthProvisioningStatus,
    PinAuthBridge,
    SupabaseAuthSession,
    SupabaseAuthUser,
    TrainerAuthIdentity,
    TrainerAuthProvisioner,
    auth_pin_pepper_from_env,
    build_internal_auth_credential,
    derive_supabase_password,
    synthetic_auth_email,
)
from app.auth.errors import (
    AuthIdentityMismatchError,
    AuthNotProvisionedError,
    InvalidCredentialsError,
    MissingAuthPepperError,
    PartialProvisioningError,
    ProvisioningPermissionError,
)


TRAINER_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TRAINER_ID = "22222222-2222-2222-2222-222222222222"
AUTH_USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OTHER_AUTH_USER_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PEPPER = "unit-test-pepper"
PIN = "0042"


class FakeTrainerAuthRepository:
    def __init__(self, trainers: tuple[TrainerAuthIdentity, ...] = (), *, fail_mapping: bool = False) -> None:
        self.trainers = {trainer.slug: trainer for trainer in trainers}
        self.trainers_by_id = {trainer.id: trainer for trainer in trainers}
        self.fail_mapping = fail_mapping
        self.set_calls: list[tuple[str, str]] = []

    def find_for_login(self, identifier: str) -> TrainerAuthIdentity | None:
        return self.trainers.get(identifier)

    def set_auth_user_id(self, trainer_id: str, auth_user_id: str) -> TrainerAuthIdentity:
        self.set_calls.append((trainer_id, auth_user_id))
        if self.fail_mapping:
            raise RuntimeError("mapping failed")
        current = self.trainers_by_id[trainer_id]
        updated = TrainerAuthIdentity(
            id=current.id,
            display_name=current.display_name,
            slug=current.slug,
            globally_enabled=current.globally_enabled,
            auth_user_id=auth_user_id,
            is_admin=current.is_admin,
        )
        self.trainers[current.slug] = updated
        self.trainers_by_id[updated.id] = updated
        return updated


class FakeSupabaseAuth:
    def __init__(self, *, expected_email: str, expected_password: str, user_id: str = AUTH_USER_ID) -> None:
        self.expected_email = expected_email
        self.expected_password = expected_password
        self.user_id = user_id
        self.calls: list[tuple[str, str]] = []

    def sign_in_with_password(self, *, email: str, password: str) -> SupabaseAuthSession:
        self.calls.append((email, password))
        if email != self.expected_email or password != self.expected_password:
            raise InvalidCredentialsError()
        return SupabaseAuthSession(
            user_id=self.user_id,
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=123,
            expires_in=3600,
        )


class FakeSupabaseAdminAuth:
    def __init__(self, *, user_id: str = AUTH_USER_ID) -> None:
        self.user_id = user_id
        self.calls: list[tuple[str, str]] = []

    def create_user(self, *, email: str, password: str) -> SupabaseAuthUser:
        self.calls.append((email, password))
        return SupabaseAuthUser(user_id=self.user_id)


def _trainer(
    *,
    trainer_id: str = TRAINER_ID,
    slug: str = "anto",
    display_name: str = "Antonio",
    globally_enabled: bool = True,
    auth_user_id: str | None = AUTH_USER_ID,
    is_admin: bool = False,
) -> TrainerAuthIdentity:
    return TrainerAuthIdentity(
        id=trainer_id,
        display_name=display_name,
        slug=slug,
        globally_enabled=globally_enabled,
        auth_user_id=auth_user_id,
        is_admin=is_admin,
    )


def _bridge(trainer: TrainerAuthIdentity) -> tuple[PinAuthBridge, FakeSupabaseAuth]:
    expected_password = derive_supabase_password(trainer.id, PIN, PEPPER)
    fake_auth = FakeSupabaseAuth(
        expected_email=synthetic_auth_email(trainer.id),
        expected_password=expected_password,
        user_id=trainer.auth_user_id or AUTH_USER_ID,
    )
    repo = FakeTrainerAuthRepository((trainer,))
    return PinAuthBridge(trainers=repo, auth=fake_auth, pepper=PEPPER), fake_auth


class AuthBridgeTests(unittest.TestCase):
    def test_a01_credential_derivation_is_deterministic(self) -> None:
        first = derive_supabase_password(TRAINER_ID, PIN, PEPPER)
        second = derive_supabase_password(TRAINER_ID, PIN, PEPPER)

        self.assertEqual(first, second)

    def test_a02_different_trainer_changes_credential(self) -> None:
        self.assertNotEqual(
            derive_supabase_password(TRAINER_ID, PIN, PEPPER),
            derive_supabase_password(OTHER_TRAINER_ID, PIN, PEPPER),
        )

    def test_a03_different_pin_changes_credential(self) -> None:
        self.assertNotEqual(
            derive_supabase_password(TRAINER_ID, "0042", PEPPER),
            derive_supabase_password(TRAINER_ID, "0043", PEPPER),
        )

    def test_a04_leading_zero_pin_is_preserved(self) -> None:
        self.assertNotEqual(
            derive_supabase_password(TRAINER_ID, "0042", PEPPER),
            derive_supabase_password(TRAINER_ID, "42", PEPPER),
        )

    def test_a05_synthetic_email_uses_only_trainer_uuid(self) -> None:
        self.assertEqual(
            synthetic_auth_email(TRAINER_ID),
            "trainer-11111111-1111-1111-1111-111111111111@auth.pokeapp.invalid",
        )

    def test_a06_raw_pin_absent_from_derived_credential(self) -> None:
        password = derive_supabase_password(TRAINER_ID, PIN, PEPPER)

        self.assertNotIn(PIN, password)

    def test_a07_missing_pepper_fails_safely(self) -> None:
        with self.assertRaises(MissingAuthPepperError):
            derive_supabase_password(TRAINER_ID, PIN, "")
        with self.assertRaises(MissingAuthPepperError):
            auth_pin_pepper_from_env({})

    def test_a08_unknown_or_disabled_trainer_cannot_authenticate(self) -> None:
        enabled = _trainer()
        password = derive_supabase_password(enabled.id, PIN, PEPPER)
        auth = FakeSupabaseAuth(
            expected_email=synthetic_auth_email(enabled.id),
            expected_password=password,
        )
        empty_bridge = PinAuthBridge(trainers=FakeTrainerAuthRepository(), auth=auth, pepper=PEPPER)
        disabled_bridge = PinAuthBridge(
            trainers=FakeTrainerAuthRepository((_trainer(globally_enabled=False),)),
            auth=auth,
            pepper=PEPPER,
        )

        with self.assertRaises(InvalidCredentialsError):
            empty_bridge.authenticate(trainer_identifier="missing", pin=PIN)
        with self.assertRaises(InvalidCredentialsError):
            disabled_bridge.authenticate(trainer_identifier="anto", pin=PIN)
        self.assertEqual(auth.calls, [])

    def test_a09_unprovisioned_trainer_cannot_authenticate(self) -> None:
        bridge, _auth = _bridge(_trainer(auth_user_id=None))

        with self.assertRaises(AuthNotProvisionedError):
            bridge.authenticate(trainer_identifier="anto", pin=PIN)

    def test_a10_matching_supabase_session_succeeds(self) -> None:
        trainer = _trainer()
        bridge, auth = _bridge(trainer)

        result = bridge.authenticate(trainer_identifier=trainer.slug, pin=PIN)

        self.assertEqual(result.trainer_id, trainer.id)
        self.assertEqual(result.auth_user_id, trainer.auth_user_id)
        self.assertEqual(result.session.user_id, trainer.auth_user_id)
        self.assertEqual(len(auth.calls), 1)

    def test_a11_mismatched_supabase_user_id_is_hard_failure(self) -> None:
        trainer = _trainer()
        expected_password = derive_supabase_password(trainer.id, PIN, PEPPER)
        auth = FakeSupabaseAuth(
            expected_email=synthetic_auth_email(trainer.id),
            expected_password=expected_password,
            user_id=OTHER_AUTH_USER_ID,
        )
        bridge = PinAuthBridge(trainers=FakeTrainerAuthRepository((trainer,)), auth=auth, pepper=PEPPER)

        with self.assertRaises(AuthIdentityMismatchError):
            bridge.authenticate(trainer_identifier=trainer.slug, pin=PIN)

    def test_a12_bad_pin_maps_to_generic_authentication_failure(self) -> None:
        trainer = _trainer()
        bridge, _auth = _bridge(trainer)

        with self.assertRaises(InvalidCredentialsError) as raised:
            bridge.authenticate(trainer_identifier=trainer.slug, pin="0043")

        self.assertEqual(raised.exception.public_code, "INVALID_CREDENTIALS")
        self.assertNotIn(synthetic_auth_email(trainer.id), str(raised.exception))

    def test_a13_public_auth_result_contains_no_privileged_secrets(self) -> None:
        trainer = _trainer()
        bridge, _auth = _bridge(trainer)

        public = bridge.authenticate(trainer_identifier=trainer.slug, pin=PIN).to_public_dict()

        self.assertNotIn("pepper", repr(public).lower())
        self.assertNotIn("service_role", repr(public).lower())
        self.assertNotIn("password", repr(public).lower())
        self.assertNotIn(PIN, repr(public))

    def test_a14_provisioning_creates_mapping_exactly_once(self) -> None:
        trainer = _trainer(auth_user_id=None)
        repo = FakeTrainerAuthRepository((trainer,))
        admin_auth = FakeSupabaseAdminAuth(user_id=AUTH_USER_ID)
        provisioner = TrainerAuthProvisioner(trainers=repo, admin_auth=admin_auth, pepper=PEPPER)

        result = provisioner.provision_trainer_auth(trainer, PIN, privileged=True)

        self.assertEqual(result.status, AuthProvisioningStatus.PROVISIONED)
        self.assertEqual(result.auth_user_id, AUTH_USER_ID)
        self.assertEqual(len(admin_auth.calls), 1)
        self.assertEqual(repo.set_calls, [(trainer.id, AUTH_USER_ID)])

    def test_a15_already_provisioned_trainer_does_not_create_duplicate_user(self) -> None:
        trainer = _trainer(auth_user_id=AUTH_USER_ID)
        repo = FakeTrainerAuthRepository((trainer,))
        admin_auth = FakeSupabaseAdminAuth()
        provisioner = TrainerAuthProvisioner(trainers=repo, admin_auth=admin_auth, pepper=PEPPER)

        result = provisioner.provision_trainer_auth(trainer, PIN, privileged=True)

        self.assertEqual(result.status, AuthProvisioningStatus.ALREADY_PROVISIONED)
        self.assertEqual(admin_auth.calls, [])
        self.assertEqual(repo.set_calls, [])

    def test_a16_mapping_failure_after_auth_creation_is_partial_provision_error(self) -> None:
        trainer = _trainer(auth_user_id=None)
        repo = FakeTrainerAuthRepository((trainer,), fail_mapping=True)
        admin_auth = FakeSupabaseAdminAuth(user_id=AUTH_USER_ID)
        provisioner = TrainerAuthProvisioner(trainers=repo, admin_auth=admin_auth, pepper=PEPPER)

        with self.assertRaises(PartialProvisioningError) as raised:
            provisioner.provision_trainer_auth(trainer, PIN, privileged=True)

        self.assertEqual(raised.exception.auth_user_id, AUTH_USER_ID)
        self.assertEqual(len(admin_auth.calls), 1)

    def test_a17_admin_status_is_not_inferred_from_display_name_anto(self) -> None:
        trainer = _trainer(display_name="Anto", is_admin=False)
        bridge, _auth = _bridge(trainer)

        result = bridge.authenticate(trainer_identifier=trainer.slug, pin=PIN)

        self.assertFalse(trainer.is_admin)
        self.assertFalse(hasattr(result, "is_admin"))

    def test_a18_credential_and_session_repr_do_not_expose_sensitive_values(self) -> None:
        credential = build_internal_auth_credential(TRAINER_ID, PIN, PEPPER)
        session = SupabaseAuthSession(
            user_id=AUTH_USER_ID,
            access_token="access-token-secret",
            refresh_token="refresh-token-secret",
        )

        self.assertNotIn(credential.password, repr(credential))
        self.assertNotIn(PIN, repr(credential))
        self.assertNotIn("access-token-secret", repr(session))
        self.assertNotIn("refresh-token-secret", repr(session))

    def test_provisioning_requires_explicit_privileged_path(self) -> None:
        trainer = _trainer(auth_user_id=None)
        repo = FakeTrainerAuthRepository((trainer,))
        admin_auth = FakeSupabaseAdminAuth()
        provisioner = TrainerAuthProvisioner(trainers=repo, admin_auth=admin_auth, pepper=PEPPER)

        with self.assertRaises(ProvisioningPermissionError):
            provisioner.provision_trainer_auth(trainer, PIN)
        self.assertEqual(admin_auth.calls, [])


if __name__ == "__main__":
    unittest.main()
