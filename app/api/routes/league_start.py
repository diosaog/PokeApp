"""Ordinary League start for every active participant (079).

Readiness, the idempotent preparation of an all-vs-all J1 and the trainer's
own death-history confirmation. Authority is the authenticated caller only:
the SQL principal checks season membership; no route takes a target trainer.
"""

from uuid import UUID

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.league_start_models import (
    FirstMatchdayRead,
    LeagueReadinessRead,
    OwnDeathHistoryBody,
    OwnDeathHistoryRead,
)
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Container, Key
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix="/v1/seasons/{season_id}", tags=["league start"])
MODELS = {
    "league_readiness": LeagueReadinessRead,
    "prepare_first": FirstMatchdayRead,
    "own_death_state": OwnDeathHistoryRead,
    "own_death_confirm": OwnDeathHistoryRead,
}


def execute(operation, sid, principal, container, payload=None, key=None):
    request = dict(actor_trainer_id=principal.trainer_id, season_id=str(sid))
    if payload is not None:
        request.update(body=payload.model_dump(mode="json"), idempotency_key=key)
    try:
        if container.matchday_repository is None:
            raise PersistenceError("Missing backend")
        result = MODELS[operation].model_validate(
            container.matchday_repository.execute(operation, request)
        )
        if result.season_id != sid:
            raise ValueError("Scope mismatch")
        if isinstance(result, OwnDeathHistoryRead) and (
            str(result.trainer_id) != str(principal.trainer_id)
            or (operation == "own_death_state" and result.replayed)
        ):
            raise ValueError("Owner mismatch")
        if operation == "own_death_confirm" and (not result.known or (
            not result.replayed and (result.actual_deaths, result.wipe_deaths) != (
                payload.actual_deaths, payload.wipe_deaths))):
            raise ValueError("Command response mismatch")
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "League operation rejected.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(
            503, "LEAGUE_UNAVAILABLE", "League state is unavailable."
        ) from exc


@router.get("/league/readiness", response_model=LeagueReadinessRead)
def readiness(season_id: UUID, principal: Reader, container: Container):
    """Why the next matchday can or cannot open now (the open stays authoritative)."""
    return execute("league_readiness", season_id, principal, container)


@router.post("/league/first-matchday", response_model=FirstMatchdayRead)
def prepare_first(season_id: UUID, principal: Reader, container: Container):
    """Prepare J1 of an all-vs-all League. Idempotent by state: always the same J1."""
    return execute("prepare_first", season_id, principal, container)


@router.get("/death-history", response_model=OwnDeathHistoryRead)
def own_death_history(season_id: UUID, principal: Reader, container: Container):
    return execute("own_death_state", season_id, principal, container)


@router.put("/death-history", response_model=OwnDeathHistoryRead)
def confirm_own_death_history(
    season_id: UUID,
    payload: OwnDeathHistoryBody,
    idempotency_key: Key,
    principal: Reader,
    container: Container,
):
    """Confirm the observed values shown; corrections stay administrative."""
    return execute(
        "own_death_confirm", season_id, principal, container, payload, idempotency_key
    )
