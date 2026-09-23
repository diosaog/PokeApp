from uuid import UUID
from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.routes.season_admin import Admin, Container, Key
from app.api.matchday_models import OpenDayBody, CancelDayBody, ResultsBody, CloseDayBody, CorrectDayBody, DayReceipt, DayState
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix="/v1/admin/seasons/{season_id}/matchdays", tags=["matchday administration"])


def execute(op, sid, day, principal, container, payload=None, key=None):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid), resource_id=str(day))
    if payload is not None:
        request["body"] = payload.model_dump(mode="json")
    if key is not None:
        request["idempotency_key"] = key
    try:
        if container.matchday_repository is None:
            raise PersistenceError("Missing backend")
        raw = container.matchday_repository.execute(op, request)
        result = (DayState if op == "state" else DayReceipt).model_validate(raw)
        if result.season_id != sid or result.matchday_id != day:
            raise ValueError("Scope mismatch")
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Matchday operation rejected.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, "MATCHDAY_UNAVAILABLE", "Matchday administration is unavailable.") from exc


@router.get("/{day_id}", response_model=DayState)
def state(season_id: UUID, day_id: UUID, principal: Admin, container: Container):
    return execute("state", season_id, day_id, principal, container)


@router.post("/{day_id}/open", response_model=DayReceipt)
def open_day(season_id: UUID, day_id: UUID, payload: OpenDayBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute("open", season_id, day_id, principal, container, payload, idempotency_key)


@router.put("/{day_id}/results", response_model=DayReceipt)
def results(season_id: UUID, day_id: UUID, payload: ResultsBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute("results", season_id, day_id, principal, container, payload, idempotency_key)


@router.post("/{day_id}/cancel-editing", response_model=DayReceipt)
def cancel(season_id: UUID, day_id: UUID, payload: CancelDayBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute("cancel", season_id, day_id, principal, container, payload, idempotency_key)


@router.post("/{day_id}/close", response_model=DayReceipt)
def close(season_id: UUID, day_id: UUID, payload: CloseDayBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute("close", season_id, day_id, principal, container, payload, idempotency_key)


@router.post("/{day_id}/correct", response_model=DayReceipt)
def correct(season_id: UUID, day_id: UUID, payload: CorrectDayBody, idempotency_key: Key, principal: Admin, container: Container):
    return execute("correct", season_id, day_id, principal, container, payload, idempotency_key)
