from uuid import UUID

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.initial_assignment_models import (
    FinalizeInitialAssignmentBody,
    InitialAssignmentRead,
)
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Admin, Container, Key
from app.api.season_admin_models import AdminReceipt
from app.application.initial_assignment import InitialAssignmentRejected
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(tags=["initial division assignment"])
REJECTIONS = {
    "INITIAL_ASSIGNMENT_REVIEW_STALE",
    "INITIAL_ASSIGNMENT_LOCKED",
    "INITIAL_ASSIGNMENT_NOT_READY",
    "INITIAL_BOUNDARY_TIE_UNRESOLVED",
    "INVALID_TIE_RESOLUTION",
    "STALE_REVISION",
}


def execute(operation, sid, principal, container, payload=None, key=None):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid))
    if payload is not None:
        request["body"] = payload.model_dump(mode="json", exclude_none=True)
        request["idempotency_key"] = key
    try:
        if container.season_admin_repository is None:
            raise PersistenceError("Missing backend")
        raw = container.season_admin_repository.execute(operation, request)
        model = InitialAssignmentRead if operation == "initial_state" else AdminReceipt
        result = model.model_validate(raw)
        if result.season_id != sid:
            raise ValueError("Scope mismatch")
        return result
    except InitialAssignmentRejected as exc:
        if exc.code not in REJECTIONS:
            raise api_error(
                503, "INITIAL_ASSIGNMENT_UNAVAILABLE", "Initial assignment unavailable."
            ) from exc
        raise api_error(
            409, exc.code, "Initial assignment requires a current review."
        ) from exc
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Initial assignment rejected.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError, KeyError) as exc:
        raise api_error(
            503, "INITIAL_ASSIGNMENT_UNAVAILABLE", "Initial assignment unavailable."
        ) from exc


@router.get(
    "/v1/seasons/{season_id}/initial-assignment", response_model=InitialAssignmentRead
)
def read(season_id: UUID, principal: Reader, container: Container):
    return execute("initial_state", season_id, principal, container)


@router.post(
    "/v1/admin/seasons/{season_id}/initial-assignment/finalize",
    response_model=AdminReceipt,
)
def finalize(
    season_id: UUID,
    payload: FinalizeInitialAssignmentBody,
    idempotency_key: Key,
    principal: Admin,
    container: Container,
):
    return execute(
        "initial_finalize", season_id, principal, container, payload, idempotency_key
    )
