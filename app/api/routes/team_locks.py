from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.schemas import TeamLockRequest, TeamLockResponse
from app.api.security import require_enabled_principal
from app.application.team_locks import lock_team_v2
from app.repositories.errors import ConflictError, NotFoundError, PermissionDeniedError, PersistenceError


router = APIRouter(prefix="/v1/seasons", tags=["team-locks"])
# Refusals the trainer can understand and act on (079: «Fijar Equipo»).
REASONS = frozenset((
    "season_not_found", "season_not_active", "matchday_not_found", "matchday_not_lockable",
    "participation_not_found", "participant_inactive", "trainer_disabled", "save_not_found",
    "save_not_ready", "invalid_save_hash", "parsed_save_not_ready", "parsed_save_changed",
    "parsed_save_identity_mismatch", "invalid_parsed_team", "invalid_team_snapshot",
    "team_requires_six", "team_lock_not_saved",
))


def _refusal(status: int, code: str, message: str, exc: Exception) -> HTTPException:
    error = api_error(status, code, message)
    if str(exc) in REASONS:
        error.detail["reason"] = str(exc)
    return error


@router.put("/{season_id}/matchdays/{matchday_id}/team-lock", response_model=TeamLockResponse)
def put_team_lock(
    season_id: UUID, matchday_id: UUID, payload: TeamLockRequest,
    principal: AuthenticatedPrincipal = Depends(require_enabled_principal),
    container: ApiContainer = Depends(get_api_container),
) -> TeamLockResponse:
    if container.team_lock_repository is None:
        raise api_error(503, "TEAM_LOCK_UNAVAILABLE", "Team lock backend is unavailable.")
    try:
        result = lock_team_v2(
            container.team_lock_repository, season_id=str(season_id), matchday_id=str(matchday_id),
            trainer_id=principal.trainer_id, save_file_id=str(payload.save_file_id),
        )
    except NotFoundError as exc:
        raise _refusal(404, "TEAM_LOCK_SOURCE_NOT_FOUND", "Team lock source was not found.", exc) from exc
    except PermissionDeniedError as exc:
        raise _refusal(403, "TEAM_LOCK_FORBIDDEN", "Trainer cannot lock a team.", exc) from exc
    except ConflictError as exc:
        raise _refusal(409, "TEAM_LOCK_CONFLICT", "The current state does not allow this team lock.", exc) from exc
    except PersistenceError as exc:
        raise api_error(503, "TEAM_LOCK_UNAVAILABLE", "Team lock backend is unavailable.") from exc
    return TeamLockResponse.model_validate(result, from_attributes=True)
