from typing import Protocol
from app.domain.services.cup_engine import plan, CupRejected
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, SeasonAdminRejected

ERRORS = {**REJECTIONS, **dict.fromkeys(('cup_not_draft','cup_not_active','cup_terminal',
    'legacy_cup_unsupported','season_not_eligible','invalid_roster','stale_inputs',
    'invalid_plan','historical_artifact_immutable'),409), 'cup_not_found':404}


class CupRepository(Protocol):
    def execute(self, operation: str, request: dict) -> dict: ...
    def read(self, request: dict) -> dict: ...


class SupabaseCupRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client
        return cls(create_client(url, key))

    def rpc(self, name, params):
        try:
            data = self.client.rpc(name, params).execute().data
        except Exception as exc:
            message = str(getattr(exc, 'message', ''))
            status = ERRORS.get(message)
            if status and str(getattr(exc, 'code', '')) == f'PT{status}':
                raise SeasonAdminRejected(message.upper(), status) from exc
            raise PersistenceError('Cup backend unavailable') from exc
        if not isinstance(data, dict):
            raise PersistenceError('Invalid Cup response')
        return data

    def execute(self, operation, request):
        request = dict(request, operation=operation)
        context = self.rpc('api_cup_context', {'p_request':request})
        if 'receipt' in context:
            return context['receipt']
        try:
            proposed = plan(context['context'], request)
        except CupRejected as exc:
            raise SeasonAdminRejected(str(exc), 409) from exc
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise PersistenceError('Invalid authoritative Cup inputs') from exc
        return self.rpc('api_admin_cup', dict(p_request=request, p_fingerprint=context['fingerprint'], p_plan=proposed))

    def read(self, request):
        return self.rpc('api_cup_read', {'p_request': request})
