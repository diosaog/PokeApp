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
            if "account_conflict" in str(exc):
                raise AccountError("ACCOUNT_CONFLICT") from None
            raise AuthBackendError("Account operation unavailable.") from None

    def reserve(self, operation, digest, name, slug):
        return self.rpc(
            "account_registration_reserve",
            dict(p_operation=operation, p_hash=digest, p_name=name, p_slug=slug),
        )

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


class SupabaseAccountAuth:
    """Privileged methods do not use or mutate a user's signed-in SDK session."""

    def __init__(self, admin):
        self.admin = admin

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
