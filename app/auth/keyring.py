"""SEC-PIN-01 credential policy foundation, not enabled by the API container.

Versions must come from trusted, persisted account/intent metadata, never a
request's choice. This module neither updates Auth nor certifies a migration.
The SQL saga, independent identity verification and session cutover are still
required before wiring it into login, registration or PIN recovery.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.auth.credentials import (
    _encode_digest_letters_only,
    build_internal_auth_credential,
    PASSWORD_COMPLEXITY_PREFIX,
    synthetic_auth_email,
)
from app.auth.errors import AuthBackendError, InvalidCredentialsError
from app.auth.identifiers import canonical_trainer_uuid
from app.auth.models import InternalAuthCredential


class KeyringConfigurationError(AuthBackendError):
    def __init__(self):
        # Do not include values or validation input in errors or repr.
        super().__init__("Invalid versioned credential configuration.")


class CredentialRenewalRequired(InvalidCredentialsError):
    """Deliberately retains the generic public authentication error."""


class IntentReconciliationRequired(AuthBackendError):
    def __init__(self):
        super().__init__("Credential intent requires trusted reconciliation.")


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise KeyringConfigurationError()
    if value.utcoffset() is None:
        raise KeyringConfigurationError()
    return value.astimezone(timezone.utc)


def _version(value: int) -> int:
    if type(value) is not int or value not in (1, 2):
        raise KeyringConfigurationError()
    return value


@dataclass(frozen=True)
class CredentialState:
    """Trusted row projection; no default version or inferred legacy identity."""

    version: int
    reset_required: bool

    def __post_init__(self):
        _version(self.version)
        if type(self.reset_required) is not bool:
            raise KeyringConfigurationError()


@dataclass(frozen=True)
class IntentVersions:
    """The persisted password and request-HMAC epochs are independent."""

    credential_version: int
    fingerprint_version: int
    expires_at: datetime

    def __post_init__(self):
        _version(self.credential_version)
        _version(self.fingerprint_version)
        object.__setattr__(self, "expires_at", _utc(self.expires_at))


@dataclass(frozen=True)
class CredentialKeyring:
    """Bounded v1 compatibility, v2 domain separation and no key fallback.

    All supplied keys stay private. ``repr`` never includes secrets. A single
    explicitly configured UTC deadline bounds both legacy passwords and legacy
    intent HMACs. Removing v1 is supported; v2 derivation remains unchanged.
    ``throttle_key`` must survive credential/intent key rotations.
    """

    legacy_deadline: datetime
    v2_pepper: str = field(repr=False)
    intent_key: str = field(repr=False)
    throttle_key: str = field(repr=False)
    v1_pepper: str | None = field(default=None, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "legacy_deadline", _utc(self.legacy_deadline))
        current = (self.v2_pepper, self.intent_key, self.throttle_key)
        if any(not isinstance(key, str) or len(key.encode()) < 32 for key in current):
            raise KeyringConfigurationError()
        if self.v1_pepper is not None and (
            not isinstance(self.v1_pepper, str) or not self.v1_pepper
        ):
            raise KeyringConfigurationError()
        all_keys = (*current, *((self.v1_pepper,) if self.v1_pepper else ()))
        if len(set(all_keys)) != len(all_keys):
            raise KeyringConfigurationError()

    def _legacy(self, now: datetime) -> str:
        if _utc(now) >= self.legacy_deadline or self.v1_pepper is None:
            raise CredentialRenewalRequired()
        return self.v1_pepper

    def credential(
        self,
        trainer_id: str,
        pin: str,
        state: CredentialState,
        *,
        now: datetime,
    ) -> InternalAuthCredential:
        if not isinstance(state, CredentialState) or state.reset_required:
            raise CredentialRenewalRequired()
        if not isinstance(pin, str) or not re.fullmatch(r"[0-9]{4}", pin):
            raise InvalidCredentialsError()
        _utc(now)
        trainer_id = canonical_trainer_uuid(trainer_id)
        if state.version == 1:
            return build_internal_auth_credential(trainer_id, pin, self._legacy(now))
        # A v2 account selects only this branch, even if a legacy key is present.
        message = f"pokeapp-v2-auth:credential-v2:{trainer_id}:{pin}".encode()
        digest = hmac.new(self.v2_pepper.encode(), message, hashlib.sha256).digest()
        return InternalAuthCredential(
            trainer_id=trainer_id,
            email=synthetic_auth_email(trainer_id),
            password=PASSWORD_COMPLEXITY_PREFIX + _encode_digest_letters_only(digest),
        )

    def intent_fingerprint(
        self, payload: Any, versions: IntentVersions, *, now: datetime
    ) -> str:
        if not isinstance(versions, IntentVersions) or _utc(now) >= versions.expires_at:
            raise IntentReconciliationRequired()
        # An uncompleted v1 credential cannot be provisioned after its cutoff,
        # even when its intent was already protected by the newer HMAC key.
        if 1 in (versions.credential_version, versions.fingerprint_version):
            try:
                legacy = self._legacy(now)
            except CredentialRenewalRequired:
                raise IntentReconciliationRequired() from None
        if versions.fingerprint_version == 1:
            # Byte-identical to P1/P2's legacy serialization for retained intents.
            value = json.dumps(payload, sort_keys=True).encode()
            key = legacy
        else:
            value = json.dumps(
                [
                    "pokeapp-credential-intent-v2",
                    versions.credential_version,
                    versions.fingerprint_version,
                    versions.expires_at.isoformat(),
                    payload,
                ],
                sort_keys=True,
            ).encode()
            key = self.intent_key
        return hmac.new(key.encode(), value, hashlib.sha256).hexdigest()

    def throttle_fingerprint(self, scope: str, identity: str) -> str:
        # No credential version, PIN or pepper in the counter identity.
        value = json.dumps(["pokeapp-throttle-v2", scope, identity]).encode()
        return hmac.new(self.throttle_key.encode(), value, hashlib.sha256).hexdigest()
