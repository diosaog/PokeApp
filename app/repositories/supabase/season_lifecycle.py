from typing import Protocol

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, SeasonAdminRejected

ERRORS = {**REJECTIONS, **dict.fromkeys((
    'season_not_active', 'season_not_finished', 'competition_incomplete',
    'historical_source_invalid', 'discard_not_allowed', 'historical_artifact_exists',
    'historical_artifact_immutable', 'config_mismatch', 'invalid_roster',
    'invalid_results', 'results_incomplete'), 409)}


class SeasonLifecycleRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseSeasonLifecycleRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client
        return cls(create_client(url, key))

    def execute(self, operation, request):
        try:
            data = self.client.rpc('api_admin_season_lifecycle', {
                'p_request': dict(request, operation=operation)}).execute().data
        except Exception as exc:
            message = str(getattr(exc, 'message', ''))
            status = ERRORS.get(message)
            if status and str(getattr(exc, 'code', '')) == f'PT{status}':
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError('Season lifecycle backend unavailable') from exc
        if not isinstance(data, dict):
            raise PersistenceError('Invalid season lifecycle response')
        return data
