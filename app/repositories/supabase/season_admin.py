"""Service-role transport only; each RPC is one database transaction."""
from typing import Any, Protocol

from app.repositories.errors import PersistenceError
from app.application.initial_assignment import initial_assignment_review, plan_initial_assignment, InitialAssignmentRejected


RPCS = {
    "live_rules_read": "api_admin_live_rules_read", "live_rules_update": "api_admin_live_rules_update",
    "setup": "api_admin_get_setup", "create": "api_admin_create_season",
    "rename": "api_admin_rename_season", "add_participant": "api_admin_add_participant",
    "remove_participant": "api_admin_remove_participant", "create_config": "api_admin_create_config",
    "replace_config": "api_admin_replace_config", "initial_divisions": "api_admin_initial_divisions",
    "prepare": "api_admin_prepare_first_matchday", "activate": "api_admin_activate_season",
    "dead_box": "api_admin_set_dead_box",
}
DEATH_HISTORY_REJECTIONS = {
    **dict.fromkeys(("death_history_source_unavailable", "death_history_revision_conflict",
        "death_history_source_changed", "death_history_inconsistent", "death_history_closed",
        "death_history_baseline_required", "death_history_confirmation_required",
        "death_history_dead_box_changed", "death_history_observation_gap",
        "death_history_segment_frozen", "death_history_start_unproven",
        "death_history_unmapped_revival", "death_history_wipe_reconciliation_required",
        "death_history_wipe_state_unavailable"), 409),
    "death_history_evidence_required": 422,
}
REJECTIONS = {
    **dict.fromkeys(("trainer_disabled", "admin_required"), 403),
    **dict.fromkeys(("season_not_found", "participant_not_found", "config_not_found"), 404),
    **dict.fromkeys(("season_not_draft", "active_season_exists", "setup_incomplete", "stale_revision",
        "idempotency_conflict", "trainer_unavailable", "participant_exists", "participant_referenced",
        "invalid_roster", "invalid_config", "invalid_rewards", "single_league_common_coins_required", "training_save_busy", "effective_round_exists", "config_window_closed",
        "config_already_used", "initial_setup_locked", "division_capacity_mismatch", "matchday_already_prepared",
        "config_not_effective", "competition_structure_locked", "competition_structure_mismatch",
        "season_not_editable"), 409),
    **dict.fromkeys(("initial_assignment_required", "initial_assignment_not_ready",
        "initial_assignment_locked", "initial_assignment_review_stale", "stale_inputs",
        "initial_boundary_tie_unresolved", "invalid_tie_resolution"), 409),
    "invalid_request": 422,
    **DEATH_HISTORY_REJECTIONS,
    **dict.fromkeys(("legacy_scoring_migration_required", "league_common_coins_required"), 409),
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
        from app.repositories.supabase.http import create_client
        return cls(create_client(url, service_role_key))

    def execute(self, operation: str, request: dict) -> dict:
        if operation in ("death_history_state", "death_history_reconcile"):
            return self._rpc("api_admin_death_history", dict(
                operation="state" if operation == "death_history_state" else "reconcile",
                request=request,
            ))
        if operation in ("initial_state", "initial_finalize"):
            envelope = dict(operation="read" if operation == "initial_state" else "finalize", request=request)
            context = self._rpc("initial_assignment_context", envelope)
            if "receipt" in context:
                if operation != "initial_finalize":
                    raise PersistenceError("Unexpected read receipt")
                return context["receipt"]
            try:
                if operation == "initial_state":
                    return initial_assignment_review(context)
                plan = plan_initial_assignment(context, request["body"])
            except InitialAssignmentRejected:
                raise
            except (ValueError, TypeError, KeyError) as exc:
                raise PersistenceError("Invalid initial assignment context") from exc
            return self._rpc("api_admin_finalize_initial_assignment", dict(
                request=request, plan=plan, input_hash=context["input_hash"],
            ))
        return self._rpc(RPCS[operation], request)

    def _rpc(self, name: str, request: dict) -> dict:
        try:
            data = self._client.rpc(name, {"p_request": request}).execute().data
        except Exception as exc:
            message = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(message)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError("Season administration backend unavailable.") from exc
        if not isinstance(data, dict):
            raise PersistenceError("Invalid season administration response.")
        return data
