"""Service-role transport only; each RPC is one database transaction."""
from typing import Any, Protocol

from app.repositories.errors import PersistenceError


RPCS = {
    "setup": "api_admin_get_setup", "create": "api_admin_create_season",
    "rename": "api_admin_rename_season", "add_participant": "api_admin_add_participant",
    "remove_participant": "api_admin_remove_participant", "create_config": "api_admin_create_config",
    "replace_config": "api_admin_replace_config", "initial_divisions": "api_admin_initial_divisions",
    "prepare": "api_admin_prepare_first_matchday", "activate": "api_admin_activate_season",
}
REJECTIONS = {
    **dict.fromkeys(("trainer_disabled", "admin_required"), 403),
    **dict.fromkeys(("season_not_found", "participant_not_found", "config_not_found"), 404),
    **dict.fromkeys(("season_not_draft", "active_season_exists", "setup_incomplete", "stale_revision",
        "idempotency_conflict", "trainer_unavailable", "participant_exists", "participant_referenced",
        "invalid_roster", "invalid_config", "invalid_rewards", "effective_round_exists", "config_window_closed",
        "config_already_used", "initial_setup_locked", "division_capacity_mismatch", "matchday_already_prepared",
        "config_not_effective"), 409),
    "invalid_request": 422,
}


class SeasonAdminRejected(PersistenceError):
    def __init__(self, code: str, status: int):
        super().__init__("Season setup operation rejected.")
        self.code, self.status = code, status


class SeasonAdminRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseSeasonAdminRepository:
    def __init__(self, client: Any):
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str):
        from supabase import create_client
        return cls(create_client(url, service_role_key))

    def execute(self, operation: str, request: dict) -> dict:
        try:
            data = self._client.rpc(RPCS[operation], {"p_request": request}).execute().data
        except Exception as exc:
            message = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(message)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError("Season administration backend unavailable.") from exc
        if not isinstance(data, dict):
            raise PersistenceError("Invalid season administration response.")
        return data
