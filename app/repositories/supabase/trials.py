"""One service-only RPC per command; never retry a judicial mutation."""
from typing import Protocol

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

ERRORS = {
    **dict.fromkeys(('trainer_disabled', 'participant_inactive', 'creator_required'), 403),
    **dict.fromkeys(('season_not_found', 'trial_not_found', 'accused_not_found'), 404),
    **dict.fromkeys(('season_not_active', 'season_unavailable', 'trial_source_unsupported',
        'trial_not_open', 'trial_not_resolved', 'stale_revision', 'idempotency_conflict',
        'no_future_points_capture', 'store_ban_rounds_unavailable', 'current_matchday_required',
        'current_matchday_invalid', 'historical_artifact_immutable'), 409),
    'invalid_request': 422,
}


class TrialRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseTrialRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client
        return cls(create_client(url, key))

    def execute(self, operation, request):
        rpc = 'api_trials_read' if operation in ('list', 'detail') else 'api_trial_mutate'
        try:
            result = self.client.rpc(rpc, {'p_request': dict(request, operation=operation)}).execute().data
        except Exception as exc:
            message = str(getattr(exc, 'message', ''))
            status = ERRORS.get(message)
            if status and str(getattr(exc, 'code', '')) == f'PT{status}':
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError('Trial backend unavailable') from exc
        if not isinstance(result, dict):
            raise PersistenceError('Invalid trial response')
        return result
