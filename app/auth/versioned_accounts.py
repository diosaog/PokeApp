"""SEC-PIN-01 integration over the existing account/PIN journal and Auth IDs."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import re

from app.auth.accounts import AccountService, AccountError, account_name
from app.auth.errors import AuthBackendError, InvalidCredentialsError
from app.auth.keyring import (
    CredentialKeyring,
    CredentialState,
    IntentVersions,
    CredentialRenewalRequired,
)


class VersionedAccountService(AccountService):
    def __init__(
        self,
        repository,
        auth,
        *,
        keyring: CredentialKeyring,
        enabled=False,
        access_code="",
        bootstrap_hash="",
        clock=None,
    ):
        super().__init__(
            repository,
            auth,
            pepper="",
            enabled=enabled,
            access_code=access_code,
            bootstrap_hash=bootstrap_hash,
        )
        self.keyring = keyring
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def credential(self, trainer_id, pin):
        context = self.repository.rpc("sec_pin_context", {"p_trainer": trainer_id})
        if not context or not context["globally_enabled"]:
            raise CredentialRenewalRequired()
        # SQL is authoritative; local policy may only be stricter, never extend it.
        if context["version"] == 1 and self.clock() >= datetime.fromisoformat(
            context["legacy_deadline"]
        ):
            raise CredentialRenewalRequired()
        return self.keyring.credential(
            trainer_id,
            pin,
            CredentialState(context["version"], context["reset_required"]),
            now=self.clock(),
        )

    def fingerprint(self, value):
        # Non-credential profile/status receipts also stop depending on v1.
        data = json.dumps(["account-command-v2", value], sort_keys=True).encode()
        return hmac.new(
            self.keyring.intent_key.encode(), data, hashlib.sha256
        ).hexdigest()

    def throttle(self, scope, identity, limit=8, seconds=300):
        old = None
        if self.keyring.v1_pepper:
            old = hmac.new(
                self.keyring.v1_pepper.encode(),
                json.dumps([scope, identity], sort_keys=True).encode(),
                hashlib.sha256,
            ).hexdigest()
        if (
            self.repository.rpc(
                "sec_pin_rate",
                dict(
                    p_key=self.keyring.throttle_fingerprint(scope, identity),
                    p_old=old,
                    p_limit=limit,
                    p_seconds=seconds,
                ),
            )
            is not True
        ):
            raise AccountError("RATE_LIMITED", 429)

    def _versions(self, row):
        if (
            row.get("credential_version") != 2
            or row.get("fingerprint_version") != 2
            or not row.get("expires_at")
        ):
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        return IntentVersions(2, 2, datetime.fromisoformat(row["expires_at"]))

    def _digest(self, row, body):
        return self.keyring.intent_fingerprint(
            body, self._versions(row), now=self.clock()
        )

    def _new_intent(self, body, expires=None):
        expiry = self.clock() + timedelta(hours=24)
        if expires is not None:
            expiry = min(expiry, expires)
        row = dict(
            credential_version=2,
            fingerprint_version=2,
            expires_at=expiry.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
        )
        return dict(p_hash=self._digest(row, body), p_expires=row["expires_at"])

    def register(
        self, operation, name, pin, confirmation, access_code, bootstrap_token=""
    ):
        if not self.registration_enabled:
            raise AccountError("ACCOUNTS_UNAVAILABLE", 503)
        self.check_registration_access(access_code, bootstrap_token)
        if not re.fullmatch(r"[0-9]{4}", pin) or pin != confirmation:
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        display, slug = account_name(name)
        body = ["registration-v2", str(operation), display, slug, pin]
        row = self.repository.rpc(
            "sec_pin_registration_prepare",
            dict(
                p_operation=str(operation),
                p_name=display,
                p_slug=slug,
                **self._new_intent(body),
            ),
        )
        digest = self._digest(
            row, ["registration-v2", str(operation), display, slug, pin]
        )
        self.repository.rpc(
            "sec_pin_bind",
            dict(p_kind="registration", p_operation=str(operation), p_hash=digest),
        )
        tid, aid = row["trainer_id"], row["auth_user_id"]
        credential = self.keyring.credential(
            tid, pin, CredentialState(2, False), now=self.clock()
        )
        marker = self.fingerprint(["registration-auth-v2", str(operation), tid, aid])
        user = self.auth.lookup(aid)
        if user is None:
            if row["status"] == "complete":
                raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            try:
                self.auth.create(aid, credential.email, credential.password, marker)
            except AuthBackendError:
                user = self.auth.lookup(aid)
                if user is None:
                    raise AccountError("ACCOUNT_RETRY_REQUIRED", 503) from None
            else:
                user = self.auth.lookup(aid)
        if (
            not user
            or user["id"] != aid
            or user["email"] != credential.email
            or user.get("marker") != marker
            or user.get("role") != "authenticated"
        ):
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        result = self.repository.rpc(
            "sec_pin_registration_complete",
            dict(p_operation=str(operation), p_hash=digest, p_auth=aid),
        )
        if result != tid:
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        return dict(trainer_id=tid, status="registered")

    def renew_pin(
        self, operation, token, new_pin, confirmation, *, actor=None, target=None
    ):
        if not isinstance(token, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{43,128}", token
        ):
            raise AccountError("ACCOUNT_RENEWAL_REQUIRED", 403)
        grant_hash = hashlib.sha256(token.encode()).hexdigest()
        grant = self.repository.credential_intent("grant", grant_hash)
        if not grant or (target is not None and grant["trainer_id"] != target):
            raise AccountError("ACCOUNT_RENEWAL_REQUIRED", 403)
        if self.clock() >= datetime.fromisoformat(grant["expires_at"]):
            raise AccountError("ACCOUNT_RENEWAL_REQUIRED", 403)
        return self._pin(
            actor or grant["trainer_id"],
            operation,
            "",
            new_pin,
            confirmation,
            target=grant["trainer_id"],
            grant_hash=grant_hash,
            grant_auth=grant["auth_user_id"],
            grant_expires=datetime.fromisoformat(grant["expires_at"]),
        )

    def change_pin(
        self,
        actor,
        operation,
        current_pin,
        new_pin,
        confirmation,
        *,
        target=None,
        resume=False,
        renewal_token="",
    ):
        if target is not None:
            return self.renew_pin(
                operation,
                renewal_token,
                new_pin,
                confirmation,
                actor=actor,
                target=target,
            )
        return self._pin(
            actor, operation, current_pin, new_pin, confirmation, resume=resume
        )

    def _pin(
        self,
        actor,
        operation,
        current_pin,
        new_pin,
        confirmation,
        *,
        target=None,
        resume=False,
        grant_hash=None,
        grant_auth=None,
        grant_expires=None,
    ):
        if not re.fullmatch(r"[0-9]{4}", new_pin) or new_pin != confirmation:
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        if grant_hash is None and (
            not re.fullmatch(r"[0-9]{4}", current_pin) or current_pin == new_pin
        ):
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        op = str(operation)
        prior = self.repository.credential_intent("pin", op)
        body = ["pin-v2", op, current_pin, new_pin, target, grant_hash]
        if prior:
            digest = self._digest(prior, body)
            if (actor is not None and prior["actor_id"] != actor) or prior[
                "grant_hash"
            ] != grant_hash:
                raise AccountError("ACCOUNT_CONFLICT")
            target_id = prior["target_id"]
        else:
            if actor is None or resume:
                raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            target_id = target or actor
        row = self.repository.trainer(target_id)
        if (
            not row
            or not row["globally_enabled"]
            or not row["auth_user_id"]
            or (grant_auth and grant_auth != row["auth_user_id"])
        ):
            raise AccountError("ACCOUNT_FORBIDDEN", 403)
        if not prior:
            if grant_hash is None:
                context = self.repository.rpc(
                    "sec_pin_context", dict(p_trainer=target_id)
                )
                if not context or context["version"] != 2 or context["reset_required"]:
                    raise AccountError("ACCOUNT_RENEWAL_REQUIRED", 403)
                old = self.credential(target_id, current_pin)
                session = self.auth.verify(old.email, old.password)
                if session.user_id != row["auth_user_id"]:
                    raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            prior = self.repository.rpc(
                "sec_pin_prepare",
                dict(
                    p_actor=actor,
                    p_target=target_id,
                    p_operation=op,
                    p_grant=grant_hash,
                    **self._new_intent(body, grant_expires),
                ),
            )
            digest = self._digest(prior, body)
        if prior["auth_user_id"] != row["auth_user_id"]:
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        self.repository.rpc(
            "sec_pin_bind", dict(p_kind="pin", p_operation=op, p_hash=digest)
        )
        if prior["stage"] == "complete":
            return dict(status="changed", sign_in_required=True)
        credential = self.keyring.credential(
            target_id, new_pin, CredentialState(2, False), now=self.clock()
        )
        claimed = self.repository.rpc(
            "sec_pin_claim", dict(p_operation=op, p_hash=digest)
        )
        if claimed:
            try:
                self.auth.password(row["auth_user_id"], credential.password)
            except AuthBackendError:
                pass
        try:
            fresh = self.auth.verify(credential.email, credential.password)
        except InvalidCredentialsError:
            raise AccountError("PIN_RECONCILIATION_REQUIRED") from None
        if fresh.user_id != row["auth_user_id"]:
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        self.auth.revoke(fresh.access_token)
        return self.repository.rpc(
            "sec_pin_finish", dict(p_operation=op, p_hash=digest)
        )
