from __future__ import annotations

from typing import Protocol

from app.auth.models import SupabaseAuthSession, SupabaseAuthUser, TrainerAuthIdentity


class TrainerAuthRepository(Protocol):
    def find_for_login(self, identifier: str) -> TrainerAuthIdentity | None:
        ...

    def set_auth_user_id(self, trainer_id: str, auth_user_id: str) -> TrainerAuthIdentity:
        ...


class SupabaseAuthPort(Protocol):
    def sign_in_with_password(self, *, email: str, password: str) -> SupabaseAuthSession:
        ...


class SupabaseSessionRefreshPort(Protocol):
    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthSession:
        ...


class SupabaseAccessTokenVerifierPort(Protocol):
    def get_user(self, *, access_token: str) -> SupabaseAuthUser:
        ...


class SupabaseAdminAuthPort(Protocol):
    def create_user(self, *, email: str, password: str) -> SupabaseAuthUser:
        ...
