"""Account provisioning saga over existing trainer/Auth identities; no season effects."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from uuid import UUID

from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import AuthBackendError


class AccountError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status
        super().__init__(code)


def account_name(value: str) -> tuple[str, str]:
    name = " ".join(unicodedata.normalize("NFKC", value).split())
    # Reuse the existing ASCII slug contract; preserve Spanish accents in display.
    plain = "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    )
    slug = plain.lower().replace(" ", "-")
    if not 1 <= len(name) <= 48 or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", slug):
        raise AccountError("INVALID_ACCOUNT_NAME", 422)
    return name, slug


class AccountService:
    def __init__(self, repository, auth, *, pepper: str, enabled: bool = False):
        self.repository, self.auth = repository, auth
        self.pepper, self.enabled = pepper, enabled

    def fingerprint(self, value) -> str:
        return hmac.new(
            self.pepper.encode(),
            json.dumps(value, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()

    def throttle(self, scope: str, identity: str, limit: int = 8, seconds: int = 300):
        if not self.repository.rate_check(
            self.fingerprint([scope, identity]), limit, seconds
        ):
            raise AccountError("RATE_LIMITED", 429)

    def register(
        self, operation: UUID, name: str, pin: str, confirmation: str, access_code: str
    ):
        if not self.enabled or not self.pepper:
            raise AccountError("ACCOUNTS_UNAVAILABLE", 503)
        # Fixed approved invitation, server only. It grants no existing-account access.
        if not hmac.compare_digest(access_code.encode(), b"PokeApp679"):
            raise AccountError("REGISTRATION_REJECTED", 400)
        if not re.fullmatch(r"[0-9]{4}", pin) or pin != confirmation:
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        display, slug = account_name(name)
        digest = self.fingerprint(
            ["registration-v1", str(operation), display, slug, pin]
        )
        reservation = self.repository.reserve(str(operation), digest, display, slug)
        trainer_id, auth_id = reservation["trainer_id"], reservation["auth_user_id"]
        credential = build_internal_auth_credential(trainer_id, pin, self.pepper)
        marker = self.fingerprint(
            ["registration-auth", str(operation), trainer_id, auth_id]
        )
        user = self.auth.lookup(auth_id)
        if user is None:
            if reservation["status"] == "complete":
                raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            try:
                self.auth.create(auth_id, credential.email, credential.password, marker)
            except AuthBackendError:
                # A transport failure is not proof of rollback. Read before retry.
                user = self.auth.lookup(auth_id)
                if user is None:
                    raise AccountError("ACCOUNT_RETRY_REQUIRED", 503) from None
            else:
                user = self.auth.lookup(auth_id)
        if (
            not user
            or user["id"] != auth_id
            or user["email"] != credential.email
            or user.get("marker") != marker
            or user.get("role") != "authenticated"
        ):
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        result = self.repository.complete(str(operation), digest, auth_id)
        if result != trainer_id:
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        return {"trainer_id": trainer_id, "status": "registered"}
