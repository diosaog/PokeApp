from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import ValidationError

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_admin_principal
from app.api.season_admin_models import (
    AddParticipantBody, AdminReceipt, ConfigVersionBody, CreateSeasonBody, InitialDivisionsBody,
    RemoveParticipantBody, RenameSeasonBody, ReplaceConfigBody, SeasonSetup, SetupRevisionBody,
)
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix="/v1/admin", tags=["season administration"])
Admin = Annotated[AuthenticatedPrincipal, Depends(require_admin_principal)]
Container = Annotated[ApiContainer, Depends(get_api_container)]
Key = Annotated[str, Header(min_length=1, max_length=128, pattern=r"^[!-~]+$")]


def _execute(op, principal, container, payload=None, season_id=None, resource_id=None, key=None):
    repo = container.season_admin_repository
    request = {"actor_trainer_id": principal.trainer_id}
    if payload is not None:
        request["body"] = payload.model_dump(mode="json")
    for name, value in (("season_id", season_id), ("resource_id", resource_id), ("idempotency_key", key)):
        if value is not None:
            request[name] = str(value)
    try:
        if repo is None:
            raise PersistenceError("Missing backend")
        raw = repo.execute(op, request)
        model = SeasonSetup if op == "setup" else AdminReceipt
        result = model.model_validate(raw)
        actual_season = result.season.id if op == "setup" else result.season_id
        if season_id is not None and str(actual_season) != str(season_id):
            raise ValueError("Mismatched scope")
        if op in ("replace_config", "remove_participant") and str(result.resource_id) != str(resource_id):
            raise ValueError("Mismatched resource")
        return result
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Season setup operation rejected.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, "SEASON_ADMIN_UNAVAILABLE", "Season administration is unavailable.") from exc


@router.get("/seasons/{season_id}/setup", response_model=SeasonSetup)
def get_setup(season_id: UUID, principal: Admin, container: Container):
    return _execute("setup", principal, container, season_id=season_id)


@router.post("/seasons", response_model=AdminReceipt)
def create_season(payload: CreateSeasonBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("create", principal, container, payload, key=idempotency_key)


@router.put("/seasons/{season_id}/name", response_model=AdminReceipt)
def rename_season(season_id: UUID, payload: RenameSeasonBody, principal: Admin, container: Container):
    return _execute("rename", principal, container, payload, season_id, key=f"revision:{payload.expected_revision}")


@router.post("/seasons/{season_id}/participants", response_model=AdminReceipt)
def add_participant(season_id: UUID, payload: AddParticipantBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("add_participant", principal, container, payload, season_id, key=idempotency_key)


@router.post("/seasons/{season_id}/participants/{season_player_id}/remove-from-draft", response_model=AdminReceipt)
def remove_participant(season_id: UUID, season_player_id: UUID, payload: RemoveParticipantBody,
                       idempotency_key: Key, principal: Admin, container: Container):
    return _execute("remove_participant", principal, container, payload, season_id, season_player_id, idempotency_key)


@router.post("/seasons/{season_id}/config-versions", response_model=AdminReceipt)
def create_config(season_id: UUID, payload: ConfigVersionBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("create_config", principal, container, payload, season_id, key=idempotency_key)


@router.post("/seasons/{season_id}/config-versions/{version_id}/replace-unused", response_model=AdminReceipt)
def replace_config(season_id: UUID, version_id: UUID, payload: ReplaceConfigBody,
                   idempotency_key: Key, principal: Admin, container: Container):
    return _execute("replace_config", principal, container, payload, season_id, version_id, idempotency_key)


@router.put("/seasons/{season_id}/initial-divisions", response_model=AdminReceipt)
def initial_divisions(season_id: UUID, payload: InitialDivisionsBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("initial_divisions", principal, container, payload, season_id, key=idempotency_key)


@router.post("/seasons/{season_id}/matchdays/prepare-current", response_model=AdminReceipt)
def prepare(season_id: UUID, payload: SetupRevisionBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("prepare", principal, container, payload, season_id, key=idempotency_key)


@router.post("/seasons/{season_id}/activate", response_model=AdminReceipt)
def activate(season_id: UUID, payload: SetupRevisionBody, idempotency_key: Key, principal: Admin, container: Container):
    return _execute("activate", principal, container, payload, season_id, key=idempotency_key)
