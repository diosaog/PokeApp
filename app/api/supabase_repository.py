from __future__ import annotations

from typing import Any
from uuid import UUID

from app.auth.errors import AuthBackendError
from app.auth.models import TrainerAuthIdentity

TRAINER_COLUMNS = "id,display_name,slug,globally_enabled,auth_user_id,is_admin"


def _data(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    return list(data or [])


class SupabaseTrainerAuthRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str) -> "SupabaseTrainerAuthRepository":
        from supabase import create_client

        return cls(create_client(url, service_role_key))

    def find_for_login(self, identifier: str) -> TrainerAuthIdentity | None:
        clean = str(identifier or "").strip()
        if not clean:
            return None
        try:
            trainer_id = str(UUID(clean))
        except ValueError:
            row = self._find_one("slug", clean.lower())
        else:
            row = self._find_one("id", trainer_id)
        return _trainer_from_row(row) if row else None

    def find_by_auth_user_id(self, auth_user_id: str) -> TrainerAuthIdentity | None:
        row = self._find_one("auth_user_id", str(auth_user_id))
        return _trainer_from_row(row) if row else None

    def set_auth_user_id(self, trainer_id: str, auth_user_id: str) -> TrainerAuthIdentity:
        trainer_id, auth_user_id = str(UUID(trainer_id)), str(UUID(auth_user_id))
        try:
            response = (
                self._client.table("trainers")
                .update({"auth_user_id": auth_user_id})
                .eq("id", trainer_id)
                .execute()
            )
        except Exception as exc:
            raise AuthBackendError("Trainer auth mapping update failed.") from exc
        rows = _data(response)
        if len(rows) != 1 or str(rows[0].get("id")) != trainer_id or str(rows[0].get("auth_user_id")) != auth_user_id:
            raise AuthBackendError("Trainer auth mapping was not confirmed.")
        return _trainer_from_row(rows[0])

    def _find_one(self, column: str, value: str) -> dict[str, Any] | None:
        try:
            response = (
                self._client.table("trainers")
                .select(TRAINER_COLUMNS)
                .eq(column, value)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise AuthBackendError("Trainer auth lookup failed.") from exc
        rows = _data(response)
        return rows[0] if rows else None


def _trainer_from_row(row: dict[str, Any]) -> TrainerAuthIdentity:
    return TrainerAuthIdentity(
        id=str(row["id"]),
        display_name=str(row.get("display_name") or row.get("slug") or row["id"]),
        slug=str(row.get("slug") or row["id"]),
        globally_enabled=bool(row.get("globally_enabled", True)),
        auth_user_id=str(row["auth_user_id"]) if row.get("auth_user_id") else None,
        is_admin=bool(row.get("is_admin", False)),
    )
