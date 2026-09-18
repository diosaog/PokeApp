from __future__ import annotations

from typing import Any

from app.auth.errors import AuthBackendError, InvalidCredentialsError
from app.auth.models import SupabaseAuthSession, SupabaseAuthUser


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _message(exc: BaseException) -> str:
    return str(exc).lower()


def _looks_like_invalid_credentials(exc: BaseException) -> bool:
    text = _message(exc)
    return "invalid login credentials" in text or "invalid credentials" in text


class SupabaseAuthClient:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, anon_key: str) -> "SupabaseAuthClient":
        try:
            from supabase import create_client
        except Exception as exc:
            raise AuthBackendError("Supabase Python client is not available.") from exc
        return cls(create_client(url, anon_key))

    def sign_in_with_password(self, *, email: str, password: str) -> SupabaseAuthSession:
        try:
            response = self._client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            if _looks_like_invalid_credentials(exc):
                raise InvalidCredentialsError() from exc
            raise AuthBackendError("Supabase Auth sign-in failed.") from exc

        session = _field(response, "session")
        user = _field(response, "user") or _field(session, "user")
        if not session or not user:
            raise AuthBackendError("Supabase Auth sign-in returned no session.")

        user_id = _field(user, "id")
        access_token = _field(session, "access_token")
        if not user_id or not access_token:
            raise AuthBackendError("Supabase Auth session is missing required fields.")

        return SupabaseAuthSession(
            user_id=str(user_id),
            access_token=str(access_token),
            refresh_token=str(_field(session, "refresh_token", "") or ""),
            expires_at=_field(session, "expires_at"),
            expires_in=_field(session, "expires_in"),
        )


class SupabaseAdminAuthClient:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str) -> "SupabaseAdminAuthClient":
        try:
            from supabase import create_client
        except Exception as exc:
            raise AuthBackendError("Supabase Python client is not available.") from exc
        return cls(create_client(url, service_role_key))

    def create_user(self, *, email: str, password: str) -> SupabaseAuthUser:
        try:
            response = self._client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                }
            )
        except Exception as exc:
            raise AuthBackendError("Supabase Auth admin user creation failed.") from exc

        user = _field(response, "user") or _field(response, "data")
        user_id = _field(user, "id")
        if not user_id:
            raise AuthBackendError("Supabase Auth admin create_user returned no user id.")
        return SupabaseAuthUser(user_id=str(user_id))
