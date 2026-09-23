from typing import Protocol

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, SeasonAdminRejected

ERRORS = {**REJECTIONS, **dict.fromkeys((
    'season_not_active', 'participant_already_inactive', 'participant_has_current_team_lock',
    'matchday_not_scheduled', 'round_open', 'dependent_data_exists',
    'ongoing_competition_dependency', 'config_mismatch', 'invalid_results'), 409),
    'participant_not_found': 404}


class ParticipantStatusRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...


class SupabaseParticipantStatusRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client
        return cls(create_client(url, key))

    def execute(self, operation, request):
        try:
            data = self.client.rpc('api_admin_participant_status', {
                'p_request': dict(request, operation=operation)}).execute().data
        except Exception as exc:
            message = str(getattr(exc, 'message', ''))
            status = ERRORS.get(message)
            if status and str(getattr(exc, 'code', '')) == f'PT{status}':
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError('Participant status backend unavailable') from exc
        if not isinstance(data, dict):
            raise PersistenceError('Invalid participant status response')
        return data
