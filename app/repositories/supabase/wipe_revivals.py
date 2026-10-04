"""One owned counter RPC. Mutations never retry automatically."""

from typing import Protocol

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

ERRORS = {
    "invalid_request": 422,
    "trainer_disabled": 403,
    "participant_not_found": 403,
    "participant_inactive": 403,
    "season_not_found": 404,
    "wipe_revivals_not_editable": 409,
    "wipe_revision_conflict": 409,
    "idempotency_conflict": 409,
    "wipe_state_unavailable": 503,
}


class WipeRevivalsRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseWipeRevivalsRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client

        return cls(create_client(url, key))

    def execute(self, operation, request):
        try:
            data = (
                self.client.rpc(
                    "api_participant_wipe_revivals",
                    {"p_request": {"operation": operation, "request": request}},
                )
                .execute()
                .data
            )
        except Exception as exc:
            message = str(getattr(exc, "message", ""))
            status = ERRORS.get(message)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError("Wipe counter backend unavailable") from exc
        if not isinstance(data, dict):
            raise PersistenceError("Invalid wipe counter response")
        return data
