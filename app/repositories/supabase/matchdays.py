from typing import Protocol

from app.application.matchdays import plan_close
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, SeasonAdminRejected

ERRORS = {**REJECTIONS, **dict.fromkeys(("season_not_active", "matchday_not_current", "matchday_not_scheduled",
    "matchday_not_open", "results_incomplete", "invalid_results", "config_mismatch", "ranking_inputs_unavailable",
    "dependent_data_exists", "already_closed", "correction_window_closed", "stale_inputs", "reward_item_unavailable"), 409),
    "matchday_not_found":404}


class MatchdayRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseMatchdayRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client
        return cls(create_client(url, key))

    def rpc(self, name, request):
        try:
            data = self.client.rpc(name, {"p_request":request}).execute().data
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
        envelope = dict(operation=operation, request=request)
        if operation in ("close", "correct"):
            context = self.rpc("api_admin_matchday_context", envelope)
            if "receipt" in context:
                return context["receipt"]
            try:
                changes = request["body"]["results"] if operation == "correct" else None
                envelope.update(plan=plan_close(context["context"], changes), input_hash=context["input_hash"])
            except (ValueError, KeyError, TypeError, StopIteration) as exc:
                raise PersistenceError("Invalid authoritative close inputs") from exc
        return self.rpc("api_admin_matchday", envelope)
