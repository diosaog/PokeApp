from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_enabled_principal
from app.api.routes.season_admin import Container, Key
from app.api.trial_models import (CreateTrialBody, UpdateTrialBody, ResolveTrialBody,
    CorrectTrialBody, CancelTrialBody, TrialReceipt, TrialView, TrialList)
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix='/v1/seasons/{season_id}/trials', tags=['trials'])
Participant = Annotated[AuthenticatedPrincipal, Depends(require_enabled_principal)]


def execute(op, sid, principal, container, body=None, cid=None, key=None):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid))
    if cid is not None:
        request['resource_id'] = str(cid)
    if body is not None:
        request.update(body=body.model_dump(mode='json'), idempotency_key=key)
    try:
        if container.trial_repository is None:
            raise PersistenceError('Missing backend')
        raw = container.trial_repository.execute(op, request)
        model = TrialList if op == 'list' else TrialView if op == 'detail' else TrialReceipt
        result = model.model_validate(raw)
        if result.season_id != sid:
            raise ValueError('Scope mismatch')
        if op == 'list':
            if any(c.season_id != sid for c in result.cases):
                raise ValueError('List scope mismatch')
        elif op == 'detail':
            if result.id != cid:
                raise ValueError('Case scope mismatch')
        else:
            if (result.operation != op or str(result.actor_trainer_id) != str(principal.trainer_id)
                    or (cid is not None and result.case_id != cid)):
                raise ValueError('Receipt scope mismatch')
            expected = 'open' if op in ('create', 'proposal') else 'cancelled' if op == 'cancel' else (
                'resolved' if body.verdict == 'guilty' else 'dismissed')
            if result.status != expected or (op in ('resolve', 'correct') and (
                    result.verdict != body.verdict or result.decision_revision_id is None)):
                raise ValueError('Receipt state mismatch')
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, 'Trial operation rejected.') from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, 'TRIAL_UNAVAILABLE', 'Trials are unavailable.') from exc


@router.get('', response_model=TrialList)
def list_trials(season_id: UUID, principal: Participant, container: Container):
    return execute('list', season_id, principal, container)


@router.get('/{case_id}', response_model=TrialView)
def get_trial(season_id: UUID, case_id: UUID, principal: Participant, container: Container):
    return execute('detail', season_id, principal, container, cid=case_id)


@router.post('', response_model=TrialReceipt)
def create_trial(season_id: UUID, payload: CreateTrialBody, idempotency_key: Key, principal: Participant, container: Container):
    return execute('create', season_id, principal, container, payload, key=idempotency_key)


@router.put('/{case_id}/proposal', response_model=TrialReceipt)
def update_trial(season_id: UUID, case_id: UUID, payload: UpdateTrialBody, idempotency_key: Key, principal: Participant, container: Container):
    return execute('proposal', season_id, principal, container, payload, case_id, idempotency_key)


@router.post('/{case_id}/resolve', response_model=TrialReceipt)
def resolve_trial(season_id: UUID, case_id: UUID, payload: ResolveTrialBody, idempotency_key: Key, principal: Participant, container: Container):
    return execute('resolve', season_id, principal, container, payload, case_id, idempotency_key)


@router.post('/{case_id}/cancel', response_model=TrialReceipt)
def cancel_trial(season_id: UUID, case_id: UUID, payload: CancelTrialBody, idempotency_key: Key, principal: Participant, container: Container):
    return execute('cancel', season_id, principal, container, payload, case_id, idempotency_key)


@router.post('/{case_id}/correct', response_model=TrialReceipt)
def correct_trial(season_id: UUID, case_id: UUID, payload: CorrectTrialBody, idempotency_key: Key, principal: Participant, container: Container):
    return execute('correct', season_id, principal, container, payload, case_id, idempotency_key)
