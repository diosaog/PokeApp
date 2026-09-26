from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import ValidationError
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_enabled_principal
from app.api.routes.season_admin import Admin, Container, Key
from app.api.cup_models import (CupCreateBody, CupSetupBody, CupRevisionBody, CupResultsBody,
    CupCorrectBody, CupDisqualifyBody, CupDiscardBody, CupReceipt, CupDetail, CupSummary)
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(tags=['cups'])
Reader = Annotated[AuthenticatedPrincipal, Depends(require_enabled_principal)]
BASE = '/v1/admin/seasons/{season_id}/cups'


def execute(op, sid, cid, payload, key, principal, container, **resource):
    request = dict(season_id=str(sid), actor_trainer_id=str(principal.trainer_id),
        body=payload.model_dump(mode='json'), idempotency_key=key, **resource)
    if cid:
        request['resource_id'] = str(cid)
    try:
        if container.cup_repository is None:
            raise PersistenceError('Missing backend')
        result = CupReceipt.model_validate(container.cup_repository.execute(op, request))
        expected_state = {'create':'draft','setup':'draft','start':'active','results':'active',
            'close':'active','correct':'active','discard':'discarded','finalize':'finished'}.get(op)
        if (result.season_id!=sid or result.operation!=op or (cid and result.cup_id!=cid)
                or str(result.actor_trainer_id)!=str(principal.trainer_id)
                or (expected_state and result.state!=expected_state)
                or (op=='finalize') != (result.certificate_id is not None and result.hall_id is not None)):
            raise ValueError('Scope mismatch')
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, 'Cup operation rejected.') from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, 'CUP_UNAVAILABLE', 'Cup service unavailable.') from exc


@router.post(BASE, response_model=CupReceipt)
def create(season_id: UUID, payload: CupCreateBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('create',season_id,None,payload,idempotency_key,principal,container)


@router.put(BASE+'/{cup_id}/setup', response_model=CupReceipt)
def setup(season_id: UUID, cup_id: UUID, payload: CupSetupBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('setup',season_id,cup_id,payload,idempotency_key,principal,container)


@router.post(BASE+'/{cup_id}/start', response_model=CupReceipt)
def start(season_id: UUID, cup_id: UUID, payload: CupRevisionBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('start',season_id,cup_id,payload,idempotency_key,principal,container)


@router.put(BASE+'/{cup_id}/rounds/{round_number}/results', response_model=CupReceipt)
def results(season_id: UUID, cup_id: UUID, round_number: int, payload: CupResultsBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('results',season_id,cup_id,payload,idempotency_key,principal,container,round_number=round_number)


@router.post(BASE+'/{cup_id}/rounds/{round_number}/close', response_model=CupReceipt)
def close(season_id: UUID, cup_id: UUID, round_number: int, payload: CupRevisionBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('close',season_id,cup_id,payload,idempotency_key,principal,container,round_number=round_number)


@router.post(BASE+'/{cup_id}/rounds/{round_number}/correct', response_model=CupReceipt)
def correct(season_id: UUID, cup_id: UUID, round_number: int, payload: CupCorrectBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('correct',season_id,cup_id,payload,idempotency_key,principal,container,round_number=round_number)


@router.post(BASE+'/{cup_id}/participants/{side_id}/disqualify', response_model=CupReceipt)
def disqualify(season_id: UUID, cup_id: UUID, side_id: UUID, payload: CupDisqualifyBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('disqualify',season_id,cup_id,payload,idempotency_key,principal,container,side_id=str(side_id))


@router.post(BASE+'/{cup_id}/discard', response_model=CupReceipt)
def discard(season_id: UUID, cup_id: UUID, payload: CupDiscardBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('discard',season_id,cup_id,payload,idempotency_key,principal,container)


@router.post(BASE+'/{cup_id}/finalize', response_model=CupReceipt)
def finalize(season_id: UUID, cup_id: UUID, payload: CupRevisionBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute('finalize',season_id,cup_id,payload,idempotency_key,principal,container)


def read(sid, cid, principal, container):
    try:
        if container.cup_repository is None:
            raise PersistenceError('Missing backend')
        request = dict(season_id=str(sid), actor_trainer_id=str(principal.trainer_id))
        if cid:
            request['resource_id'] = str(cid)
        raw = container.cup_repository.read(request)
        if cid:
            result = CupDetail.model_validate(raw['cup'])
            if result.id!=cid or result.season_id!=sid:
                raise ValueError('Scope mismatch')
            return result
        result = [CupSummary.model_validate(c) for c in raw['cups']]
        if any(c.season_id!=sid for c in result):
            raise ValueError('Scope mismatch')
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, 'Cup not available.') from exc
    except (PersistenceError, ValidationError, ValueError, KeyError, TypeError) as exc:
        raise api_error(503, 'CUP_UNAVAILABLE', 'Cup service unavailable.') from exc


@router.get('/v1/seasons/{season_id}/cups', response_model=list[CupSummary])
def list_cups(season_id: UUID, principal: Reader, container: Container):
    return read(season_id,None,principal,container)


@router.get('/v1/seasons/{season_id}/cups/{cup_id}', response_model=CupDetail)
def detail(season_id: UUID, cup_id: UUID, principal: Reader, container: Container):
    return read(season_id,cup_id,principal,container)
