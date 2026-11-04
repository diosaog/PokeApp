from typing import Protocol

from app.application.matchdays import plan_close
from app.application.daily_ranking import RankingDecisionRequired
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, SeasonAdminRejected

ERRORS = {
    **REJECTIONS,
    **dict.fromkeys(
        (
            "season_not_active",
            "matchday_not_current",
            "matchday_not_scheduled",
            "matchday_not_open",
            "results_incomplete",
            "invalid_results",
            "config_mismatch",
            "ranking_inputs_unavailable",
            "dependent_data_exists",
            "already_closed",
            "correction_window_closed",
            "stale_inputs",
            "reward_item_unavailable",
            "ranking_tie_unresolved",
            # 079: ordinary League start and own death history.
            "opponent_missing",
            "death_history_admin_required",
            "death_history_already_confirmed",
            "death_history_changed",
        ),
        409,
    ),
    "matchday_not_found": 404,
    **dict.fromkeys(
        ("participant_required", "participant_inactive", "participant_ineligible"), 403
    ),
}


# 079: participant League start; both RPCs take {actor_trainer_id, season_id}.
LEAGUE_RPCS = {
    "league_readiness": "api_league_readiness",
    "prepare_first": "api_league_prepare_first_matchday",
}


class MatchdayRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseMatchdayRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def rpc(self, name, request):
        try:
            data = self.client.rpc(name, {"p_request": request}).execute().data
        except Exception as exc:
            message = str(getattr(exc, "message", ""))
            status = ERRORS.get(message)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError("Matchday backend unavailable") from exc
        if not isinstance(data, dict):
            raise PersistenceError("Invalid matchday response")
        return data

    def execute(self, operation, request):
        if operation in LEAGUE_RPCS:
            return self.rpc(LEAGUE_RPCS[operation], request)
        if operation in ("own_death_state", "own_death_confirm"):
            return self.rpc(
                "api_participant_death_history",
                dict(operation=operation.removeprefix("own_death_"), request=request),
            )
        if operation in ("participant_state", "participant_results"):
            return self.rpc(
                "api_participant_matchday",
                dict(operation=operation.removeprefix("participant_"), request=request),
            )
        envelope = dict(operation=operation, request=request)
        if operation in ("close", "correct"):
            context = self.rpc("api_admin_matchday_context", envelope)
            if "receipt" in context:
                return context["receipt"]
            try:
                changes = request["body"]["results"] if operation == "correct" else None
                envelope.update(
                    plan=plan_close(
                        context["context"],
                        changes,
                        request["body"].get("tie_resolution"),
                    ),
                    input_hash=context["input_hash"],
                )
            except RankingDecisionRequired:
                raise
            except (ValueError, KeyError, TypeError, StopIteration) as exc:
                raise PersistenceError("Invalid authoritative close inputs") from exc
        return self.rpc("api_admin_matchday", envelope)
