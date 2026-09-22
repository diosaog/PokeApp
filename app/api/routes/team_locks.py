from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.schemas import TeamLockRequest, TeamLockResponse
from app.api.security import require_enabled_principal
from app.application.team_locks import lock_team_v2
from app.repositories.errors import ConflictError, NotFoundError, PermissionDeniedError, PersistenceError


router = APIRouter(prefix="/v1/seasons", tags=["team-locks"])


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
        raise api_error(404, "TEAM_LOCK_SOURCE_NOT_FOUND", "Team lock source was not found.") from exc
    except PermissionDeniedError as exc:
        raise api_error(403, "TEAM_LOCK_FORBIDDEN", "Trainer cannot lock a team.") from exc
    except ConflictError as exc:
        raise api_error(409, "TEAM_LOCK_CONFLICT", "The current state does not allow this team lock.") from exc
    except PersistenceError as exc:
        raise api_error(503, "TEAM_LOCK_UNAVAILABLE", "Team lock backend is unavailable.") from exc
    return TeamLockResponse.model_validate(result, from_attributes=True)
