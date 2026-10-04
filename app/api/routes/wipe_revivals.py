from uuid import UUID

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Container, Key
from app.api.wipe_revival_models import SetWipeRevivalsBody, WipeRevivalsRead
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(
    prefix="/v1/seasons/{season_id}/wipe-revivals", tags=["owned wipe revivals"]
)


def execute(operation, sid, principal, container, payload=None, key=None):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid))
    if payload is not None:
        request.update(body=payload.model_dump(mode="json"), idempotency_key=key)
    try:
        if container.wipe_revivals_repository is None:
            raise PersistenceError("Missing backend")
        result = WipeRevivalsRead.model_validate(
            container.wipe_revivals_repository.execute(operation, request)
        )
        if result.season_id != sid or (operation == "state" and result.replayed):
            raise ValueError("Scope mismatch")
        if payload is not None and (
            result.revived_after_wipe != payload.revived_after_wipe
            or result.revision
            not in (payload.expected_revision, payload.expected_revision + 1)
            or not result.editable
        ):
            raise ValueError("Command response mismatch")
        return result
    except SeasonAdminRejected as exc:
        raise api_error(
            exc.status, exc.code, "Wipe revival operation rejected."
        ) from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(
            503, "WIPE_STATE_UNAVAILABLE", "Wipe revival state is unavailable."
        ) from exc


@router.get("", response_model=WipeRevivalsRead)
def state(season_id: UUID, principal: Reader, container: Container):
    return execute("state", season_id, principal, container)


@router.put("", response_model=WipeRevivalsRead)
def set_count(
    season_id: UUID,
    payload: SetWipeRevivalsBody,
    idempotency_key: Key,
    principal: Reader,
    container: Container,
):
    return execute("set", season_id, principal, container, payload, idempotency_key)
