from __future__ import annotations

from app.auth.accounts import AccountError
from app.auth.errors import AuthBackendError


class SupabaseAccountRepository:
    def __init__(self, client):
        self.client = client

    def rpc(self, name, params):
        try:
            return self.client.rpc(name, params).execute().data
        except Exception as exc:
            for code, status in (
                ("account_conflict", 409),
                ("account_stale", 409),
                ("account_forbidden", 403),
                ("account_renewal_required", 403),
                ("account_reconciliation_required", 409),
            ):
                if code in str(exc):
                    raise AccountError(code.upper(), status) from None
            raise AuthBackendError("Account operation unavailable.") from None

    def reserve(self, operation, digest, name, slug):
        return self.rpc(
            "account_registration_reserve",
            dict(p_operation=operation, p_hash=digest, p_name=name, p_slug=slug),
        )

    def credential_intent(self, kind, key):
        table, column = {
            "pin": ("account_pin_changes", "operation_id"),
            "grant": ("account_renewal_grants", "token_hash"),
        }[kind]
        try:
            rows = self.client.table(table).select("*").eq(column, key).execute().data
            if len(rows) > 1:
                raise ValueError("ambiguous intent")
            return rows[0] if rows else None
        except Exception:
            raise AuthBackendError("Credential reconciliation unavailable.") from None

    def complete(self, operation, digest, auth_id):
        return self.rpc(
            "account_registration_complete",
            dict(p_operation=operation, p_hash=digest, p_auth=auth_id),
        )

    def rate_check(self, key, limit, seconds):
        return (
            self.rpc(
                "account_rate_check", dict(p_key=key, p_limit=limit, p_seconds=seconds)
            )
            is True
        )

    def trainer(self, trainer_id):
        try:
            rows = (
                self.client.table("trainers")
                .select(
                    "id,display_name,slug,auth_user_id,globally_enabled,is_admin,photo_key,profile_revision"
                )
                .eq("id", trainer_id)
                .execute()
                .data
            )
            if len(rows) > 1:
                raise ValueError("ambiguous identity")
            return rows[0] if rows else None
        except Exception:
            raise AuthBackendError("Profile lookup unavailable.") from None

    def trainers(self, offset):
        try:
            return (
                self.client.table("trainers")
                .select("id,display_name,photo_key,profile_revision")
                .eq("globally_enabled", True)
                .order("slug")
                .order("id")
                .range(offset, offset + 49)
                .execute()
                .data
            )
        except Exception:
            raise AuthBackendError("Profile list unavailable.") from None

    def profile_update(self, actor, operation, digest, revision, name, slug, photo):
        return self.rpc(
            "account_profile_update",
            dict(
                p_actor=actor,
                p_operation=operation,
                p_hash=digest,
                p_revision=revision,
                p_name=name,
                p_slug=slug,
                p_photo=photo,
            ),
        )

    def pin_operation(self, operation):
        try:
            rows = (
                self.client.table("account_pin_changes")
                .select("operation_id,actor_id,target_id,request_hash,stage")
                .eq("operation_id", operation)
                .execute()
                .data
            )
            return rows[0] if len(rows) == 1 else None
        except Exception:
            raise AuthBackendError("PIN reconciliation unavailable.") from None

    def photo_urls(self, keys):
        if not keys:
            return {}
        try:
            rows = self.client.storage.from_("trainer-photos").create_signed_urls(
                keys, 300
            )
            return {r["path"]: r.get("signedURL") or r.get("signedUrl") for r in rows}
        except Exception:
            raise AuthBackendError("Portrait lookup unavailable.") from None

    def upload_photo(self, key, data):
        bucket = self.client.storage.from_("trainer-photos")
        try:
            bucket.upload(key, data, {"content-type": "image/jpeg", "upsert": "false"})
        except Exception:
            # Includes an unknown upload outcome; confirm exact bytes, never overwrite.
            try:
                if bucket.download(key) == data:
                    return
            except Exception:
                pass
            raise AuthBackendError(
                "Portrait upload outcome requires reconciliation."
            ) from None


class SupabaseAccountAuth:
    """Privileged methods do not use or mutate a user's signed-in SDK session."""

    def __init__(self, admin, password_auth=None):
        self.admin = admin
        self.password_auth = password_auth

    def lookup(self, auth_id):
        try:
            user = self.admin.get_user_by_id(auth_id).user
        except Exception as exc:
            if (
                getattr(exc, "status", None) == 404
                or getattr(exc, "code", None) == "user_not_found"
            ):
                return None
            raise AuthBackendError("Account lookup unavailable.") from None
        return dict(
            id=str(user.id),
            email=user.email,
            marker=user.app_metadata.get("pokeapp_registration"),
            role=user.role,
        )

    def create(self, auth_id, email, password, marker):
        try:
            self.admin.create_user(
                dict(
                    id=auth_id,
                    email=email,
                    password=password,
                    email_confirm=True,
                    app_metadata={"pokeapp_registration": marker},
                )
            )
        except Exception:
            raise AuthBackendError(
                "Account creation outcome requires reconciliation."
            ) from None

    def verify(self, email, password):
        return self.password_auth().sign_in_with_password(
            email=email, password=password
        )

    def password(self, auth_id, password):
        try:
            user = self.admin.update_user_by_id(auth_id, {"password": password}).user
            if str(user.id) != auth_id:
                raise ValueError("identity mismatch")
        except Exception:
            raise AuthBackendError(
                "PIN update outcome requires reconciliation."
            ) from None

    def revoke(self, token):
        try:
            self.admin.sign_out(token, scope="global")
        except Exception:
            raise AuthBackendError(
                "Session revocation requires reconciliation."
            ) from None
