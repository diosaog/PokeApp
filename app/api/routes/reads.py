from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query
from app.api.errors import api_error
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Container
from app.api.read_models import (
    HallPage,
    OverviewRead,
    PCRead,
    SeasonPage,
    ShopRead,
    TrainerRead,
    InventoryRead,
    LeagueGeneralRead,
)
from app.application.frontend_reads import FrontendReads
from app.application.team_preview import team_preview
from app.api.team_preview_models import TeamPreviewQuery, TeamPreviewRead
from app.api.scouting_models import ScoutingQuery, ScoutingRead
from app.api.progress_models import ProgressQuery, ProgressRead
from app.application.scouting import scouting
from app.repositories.errors import NotFoundError, PersistenceError
from app.repositories.supabase.frontend_reads import _report_failure

router = APIRouter(prefix="/v1/read", tags=["frontend reads"])
Offset = Annotated[int, Query(ge=0, le=100000)]


def read(container, operation, *args):
    try:
        if container.frontend_read_repository is None:
            raise PersistenceError("Missing backend")
        if operation == "team_preview":
            return team_preview(container.frontend_read_repository, *args)
        if operation == "scouting":
            return scouting(container.frontend_read_repository, *args)
        return getattr(FrontendReads(container.frontend_read_repository), operation)(
            *args
        )
    except NotFoundError as exc:
        raise api_error(404, "NOT_FOUND", "Resource not found.") from exc
    except (PersistenceError, ValueError, TypeError, KeyError, AttributeError) as exc:
        if exc.__cause__ is None:
            _report_failure("projection", exc)
        raise api_error(
            503, "READ_UNAVAILABLE", "Data temporarily unavailable."
        ) from exc


@router.get("/seasons", response_model=SeasonPage)
def seasons(principal: Reader, container: Container, offset: Offset = 0):
    return read(container, "seasons", offset)


@router.get("/trainers", response_model=list[TrainerRead])
def trainers(principal: Reader, container: Container):
    return read(container, "trainers")


@router.get("/seasons/{season_id}/overview", response_model=OverviewRead)
def overview(season_id: UUID, principal: Reader, container: Container):
    return read(container, "overview", str(season_id), str(principal.trainer_id))


@router.get("/seasons/{season_id}/team-preview", response_model=TeamPreviewRead)
def preview(
    season_id: UUID,
    principal: Reader,
    container: Container,
    selection: Annotated[TeamPreviewQuery, Query()],
):
    return read(
        container, "team_preview", str(season_id), str(principal.trainer_id), selection
    )


@router.get("/seasons/{season_id}/pc", response_model=PCRead)
def pc(season_id: UUID, principal: Reader, container: Container):
    return read(container, "pc", str(season_id), str(principal.trainer_id))


@router.get("/seasons/{season_id}/progress", response_model=ProgressRead)
def progress(
    season_id: UUID,
    principal: Reader,
    container: Container,
    selection: Annotated[ProgressQuery, Query()],
):
    return read(container, "progress", str(season_id), str(principal.trainer_id))


@router.get("/seasons/{season_id}/scouting", response_model=ScoutingRead)
def public_scouting(
    season_id: UUID,
    principal: Reader,
    container: Container,
    selection: Annotated[ScoutingQuery, Query()],
):
    return read(
        container, "scouting", str(season_id), str(principal.trainer_id), selection
    )


@router.get("/seasons/{season_id}/league", response_model=LeagueGeneralRead)
def league_general(season_id: UUID, principal: Reader, container: Container):
    return read(container, "league_general", str(season_id))


@router.get("/seasons/{season_id}/shop", response_model=ShopRead)
def shop(season_id: UUID, principal: Reader, container: Container):
    return read(container, "shop", str(season_id), str(principal.trainer_id))


@router.get("/hall", response_model=HallPage)
def hall(principal: Reader, container: Container, offset: Offset = 0):
    return read(container, "hall", offset)


@router.get("/seasons/{season_id}/inventory", response_model=InventoryRead)
def inventory(season_id: UUID, principal: Reader, container: Container):
    return read(container, "inventory", str(season_id), str(principal.trainer_id))
