from uuid import UUID
from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.routes.season_admin import Admin, Container, Key
from app.api.participant_status_models import ParticipantStatusBody, ParticipantStatusReceipt
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix='/v1/admin/seasons/{season_id}/participants', tags=['participant administration'])
STATUSES = {'retire': 'retired', 'abandon': 'abandoned', 'disqualify': 'disqualified'}


def execute(op, sid, pid, principal, container, payload, key):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid), resource_id=str(pid),
        body=payload.model_dump(mode='json'), idempotency_key=key)
    try:
        if container.participant_status_repository is None:
            raise PersistenceError('Missing backend')
        result = ParticipantStatusReceipt.model_validate(container.participant_status_repository.execute(op, request))
        if (result.season_id != sid or result.participant_id != pid or result.new_status != STATUSES[op]
                or str(result.actor_trainer_id) != str(principal.trainer_id)):
            raise ValueError('Scope mismatch')
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, 'Participant status operation rejected.') from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, 'PARTICIPANT_STATUS_UNAVAILABLE', 'Participant administration is unavailable.') from exc


@router.post('/{participant_id}/retire', response_model=ParticipantStatusReceipt)
def retire(season_id: UUID, participant_id: UUID, payload: ParticipantStatusBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('retire', season_id, participant_id, principal, container, payload, idempotency_key)


@router.post('/{participant_id}/abandon', response_model=ParticipantStatusReceipt)
def abandon(season_id: UUID, participant_id: UUID, payload: ParticipantStatusBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('abandon', season_id, participant_id, principal, container, payload, idempotency_key)


@router.post('/{participant_id}/disqualify', response_model=ParticipantStatusReceipt)
def disqualify(season_id: UUID, participant_id: UUID, payload: ParticipantStatusBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('disqualify', season_id, participant_id, principal, container, payload, idempotency_key)
