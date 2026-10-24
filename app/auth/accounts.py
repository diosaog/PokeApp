"""Account provisioning saga over existing trainer/Auth identities; no season effects."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
import base64
import io
from uuid import UUID

from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import AuthBackendError, InvalidCredentialsError


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
    try:
        UUID(slug)
    except ValueError:
        pass
    else:
        raise AccountError(
            "INVALID_ACCOUNT_NAME", 422
        )  # UUID login is reserved for stable identity.
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

    def valid_session(self, auth_id, token):
        # Called only AFTER Supabase has verified this exact access token.
        try:
            payload = token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            iat = claims.get("iat", 0)
            if type(iat) is not int:
                iat = 0
        except (ValueError, IndexError, UnicodeError):
            iat = 0
        return (
            self.repository.rpc(
                "account_session_allowed", {"p_auth": auth_id, "p_iat": iat}
            )
            is True
        )

    def profile(self, trainer_id, viewer_id):
        row = self.repository.trainer(trainer_id)
        if not row or (not row["globally_enabled"] and trainer_id != viewer_id):
            raise AccountError("ACCOUNT_NOT_FOUND", 404)
        return self.public_profile(row, viewer_id)

    def public_profile(self, row, viewer_id, urls=None):
        key = row.get("photo_key")
        url = (
            (urls or {}).get(key)
            if urls is not None
            else self.repository.photo_urls([key]).get(key)
            if key
            else None
        )
        return {
            "trainer_id": row["id"],
            "display_name": row["display_name"],
            "photo_url": url,
            "revision": row["profile_revision"] if row["id"] == viewer_id else None,
        }

    def profiles(self, viewer_id, offset):
        rows = self.repository.trainers(offset)
        urls = self.repository.photo_urls(
            [r["photo_key"] for r in rows if r.get("photo_key")]
        )
        return {
            "items": [self.public_profile(r, viewer_id, urls) for r in rows],
            "offset": offset,
            "has_more": len(rows) == 50,
        }

    def rename(self, actor, operation, revision, name):
        display, slug = account_name(name)
        digest = self.fingerprint(
            ["rename", actor, str(operation), revision, display, slug]
        )
        return self.repository.profile_update(
            actor, str(operation), digest, revision, display, slug, None
        )

    def photo(self, actor, operation, revision, data):
        from PIL import Image, ImageOps, UnidentifiedImageError

        if not 0 < len(data) <= 5 * 1024 * 1024:
            raise AccountError("INVALID_PHOTO", 422)
        try:
            with Image.open(io.BytesIO(data)) as picture:
                if (
                    picture.format not in {"JPEG", "PNG", "WEBP"}
                    or getattr(picture, "n_frames", 1) != 1
                    or picture.width * picture.height > 16000000
                ):
                    raise AccountError("INVALID_PHOTO", 422)
                picture.load()
                normalized = ImageOps.exif_transpose(picture).convert("RGB")
                normalized.thumbnail((600, 800))
                output = io.BytesIO()
                normalized.save(output, format="JPEG", quality=88)
                clean = output.getvalue()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ):
            raise AccountError("INVALID_PHOTO", 422) from None
        key = f"portraits/{actor}/{hashlib.sha256(clean).hexdigest()}.jpg"
        # Immutable content-addressed object; failed CAS can only leave an orphan.
        self.repository.upload_photo(key, clean)
        digest = self.fingerprint(["photo", actor, str(operation), revision, key])
        return self.repository.profile_update(
            actor, str(operation), digest, revision, None, None, key
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
    ):
        if (
            not re.fullmatch(r"[0-9]{4}", new_pin)
            or new_pin != confirmation
            or (target is None and not re.fullmatch(r"[0-9]{4}", current_pin))
        ):
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        if target is None and current_pin == new_pin:
            raise AccountError("INVALID_PIN_CONFIRMATION", 422)
        digest = self.fingerprint(
            ["pin-change", str(operation), current_pin, new_pin, target]
        )
        prior = self.repository.pin_operation(str(operation))
        if prior:
            if prior["request_hash"] != digest or (
                actor is not None and prior["actor_id"] != actor
            ):
                raise AccountError("ACCOUNT_CONFLICT")
            if prior["stage"] == "complete":
                return {"status": "changed", "sign_in_required": True}
            target_id = prior["target_id"]
        else:
            if resume or actor is None:
                raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            target_id = target or actor
        row = self.repository.trainer(target_id)
        if not row or not row["globally_enabled"] or not row["auth_user_id"]:
            raise AccountError("ACCOUNT_FORBIDDEN", 403)
        credential = build_internal_auth_credential(target_id, new_pin, self.pepper)
        if not prior:
            if target is None:
                old = build_internal_auth_credential(actor, current_pin, self.pepper)
                session = self.auth.verify(old.email, old.password)
                if session.user_id != row["auth_user_id"]:
                    raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
            self.repository.rpc(
                "account_pin_begin",
                dict(
                    p_actor=actor,
                    p_target=target_id,
                    p_operation=str(operation),
                    p_hash=digest,
                ),
            )
        claimed = self.repository.rpc(
            "account_pin_claim", dict(p_operation=str(operation), p_hash=digest)
        )
        if claimed:
            try:
                self.auth.password(row["auth_user_id"], credential.password)
            except AuthBackendError:
                pass  # Exactly one credential update attempt; reconcile through sign-in.
        try:
            fresh = self.auth.verify(credential.email, credential.password)
        except InvalidCredentialsError:
            # Never steal a lease or send an old password update a second time.
            raise AccountError("PIN_RECONCILIATION_REQUIRED", 409) from None
        if fresh.user_id != row["auth_user_id"]:
            raise AccountError("ACCOUNT_RECONCILIATION_REQUIRED")
        self.auth.revoke(fresh.access_token)
        return self.repository.rpc(
            "account_pin_finish", dict(p_operation=str(operation), p_hash=digest)
        )

    def admin_accounts(self, actor, offset):
        return self.repository.rpc(
            "account_admin_list", dict(p_actor=actor, p_offset=offset)
        )

    def admin_status(self, actor, target, operation, revision, enabled):
        digest = self.fingerprint(
            ["account_status", actor, target, str(operation), revision, enabled]
        )
        return self.repository.rpc(
            "account_admin_status",
            dict(
                p_actor=actor,
                p_target=target,
                p_operation=str(operation),
                p_hash=digest,
                p_revision=revision,
                p_enabled=enabled,
            ),
        )
