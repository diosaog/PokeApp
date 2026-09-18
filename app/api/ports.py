from __future__ import annotations

from typing import Protocol

from app.auth.models import SupabaseAuthSession, SupabaseAuthUser, TrainerAuthIdentity


class SessionRefreshPort(Protocol):
    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthSession:
        ...


class AccessTokenVerifierPort(Protocol):
    def get_user(self, *, access_token: str) -> SupabaseAuthUser:
        ...


class TrainerPrincipalRepository(Protocol):
    def find_by_auth_user_id(self, auth_user_id: str) -> TrainerAuthIdentity | None:
        ...
