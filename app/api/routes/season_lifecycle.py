from uuid import UUID
from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.routes.season_admin import Admin, Container, Key
from app.api.season_lifecycle_models import (
    FinishSeasonBody, ArchiveSeasonBody, DiscardSeasonBody, SeasonLifecycleReceipt,
)
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix='/v1/admin/seasons', tags=['season lifecycle'])
STATES = {'finish': 'finished', 'archive': 'archived', 'discard': 'discarded'}


def execute(op, sid, principal, container, payload, key):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid),
        body=payload.model_dump(mode='json'), idempotency_key=key)
    try:
        if container.season_lifecycle_repository is None:
            raise PersistenceError('Missing backend')
        result = SeasonLifecycleReceipt.model_validate(container.season_lifecycle_repository.execute(op, request))
        if (result.season_id != sid or result.operation != op or result.state != STATES[op]
                or str(result.actor_trainer_id) != str(principal.trainer_id)
                or (op == 'archive' and (result.archive_id is None or result.hall_id is None))
                or (op != 'archive' and (result.archive_id is not None or result.hall_id is not None))):
            raise ValueError('Scope mismatch')
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, 'Season lifecycle operation rejected.') from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, 'SEASON_LIFECYCLE_UNAVAILABLE', 'Season lifecycle is unavailable.') from exc


@router.post('/{season_id}/finish', response_model=SeasonLifecycleReceipt)
def finish(season_id: UUID, payload: FinishSeasonBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('finish', season_id, principal, container, payload, idempotency_key)


@router.post('/{season_id}/archive', response_model=SeasonLifecycleReceipt)
def archive(season_id: UUID, payload: ArchiveSeasonBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('archive', season_id, principal, container, payload, idempotency_key)


@router.post('/{season_id}/discard', response_model=SeasonLifecycleReceipt)
def discard(season_id: UUID, payload: DiscardSeasonBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('discard', season_id, principal, container, payload, idempotency_key)
