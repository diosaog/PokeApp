from __future__ import annotations

from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import (
    AuthIdentityMismatchError,
    AuthNotProvisionedError,
    InvalidCredentialsError,
    PartialProvisioningError,
    ProvisioningPermissionError,
)
from app.auth.models import (
    AuthProvisioningResult,
    AuthProvisioningStatus,
    PinAuthResult,
    TrainerAuthIdentity,
)
from app.auth.identifiers import canonical_trainer_uuid
from app.auth.ports import SupabaseAdminAuthPort, SupabaseAuthPort, TrainerAuthRepository


def _clean_pin_for_current_semantics(pin: str) -> str:
    if not isinstance(pin, str):
        raise InvalidCredentialsError()
    cleaned = pin.strip()
    if len(cleaned) != 4 or not cleaned.isdigit():
        raise InvalidCredentialsError()
    return cleaned


def _same_uuid(left: str, right: str) -> bool:
    return canonical_trainer_uuid(left) == canonical_trainer_uuid(right)


class PinAuthBridge:
    def __init__(
        self,
        *,
        trainers: TrainerAuthRepository,
        auth: SupabaseAuthPort,
        pepper: str,
    ) -> None:
        self._trainers = trainers
        self._auth = auth
        self._pepper = pepper

    def authenticate(self, *, trainer_identifier: str, pin: str) -> PinAuthResult:
        cleaned_pin = _clean_pin_for_current_semantics(pin)
        trainer = self._trainers.find_for_login(trainer_identifier)
        if trainer is None or not trainer.globally_enabled:
            raise InvalidCredentialsError()
        if not trainer.auth_user_id:
            raise AuthNotProvisionedError(trainer.id)

        credential = build_internal_auth_credential(trainer.id, cleaned_pin, self._pepper)
        session = self._auth.sign_in_with_password(email=credential.email, password=credential.password)

        if not _same_uuid(session.user_id, trainer.auth_user_id):
            raise AuthIdentityMismatchError(trainer.id)

        return PinAuthResult(
            trainer_id=trainer.id,
            auth_user_id=trainer.auth_user_id,
            session=session,
        )


class TrainerAuthProvisioner:
    def __init__(
        self,
        *,
        trainers: TrainerAuthRepository,
        admin_auth: SupabaseAdminAuthPort,
        pepper: str,
    ) -> None:
        self._trainers = trainers
        self._admin_auth = admin_auth
        self._pepper = pepper

    def provision_trainer_auth(
        self,
        trainer: TrainerAuthIdentity,
        current_pin: str,
        *,
        privileged: bool = False,
    ) -> AuthProvisioningResult:
        if not privileged:
            raise ProvisioningPermissionError()

        cleaned_pin = _clean_pin_for_current_semantics(current_pin)
        if trainer.auth_user_id:
            return AuthProvisioningResult(
                status=AuthProvisioningStatus.ALREADY_PROVISIONED,
                trainer_id=trainer.id,
                auth_user_id=trainer.auth_user_id,
            )

        credential = build_internal_auth_credential(trainer.id, cleaned_pin, self._pepper)
        created_user = self._admin_auth.create_user(email=credential.email, password=credential.password)
        try:
            updated_trainer = self._trainers.set_auth_user_id(trainer.id, created_user.user_id)
        except Exception as exc:
            raise PartialProvisioningError(trainer_id=trainer.id, auth_user_id=created_user.user_id) from exc

        if not updated_trainer.auth_user_id or not _same_uuid(updated_trainer.auth_user_id, created_user.user_id):
            raise PartialProvisioningError(trainer_id=trainer.id, auth_user_id=created_user.user_id)

        return AuthProvisioningResult(
            status=AuthProvisioningStatus.PROVISIONED,
            trainer_id=trainer.id,
            auth_user_id=created_user.user_id,
        )
