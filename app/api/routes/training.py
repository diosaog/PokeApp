"""Trainer-owned virtual consumables; output proof is actual save bytes."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_api_container
from app.api.errors import api_error
from app.api.security import require_enabled_principal
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.files import MAX_SAVE_BYTES
from app.save_parser.models import SaveError

router = APIRouter(prefix="/v1/launcher/seasons/{season_id}/training", tags=["virtual training"])
Reader = Depends(require_enabled_principal)
Container = Depends(get_api_container)
Stat = Literal["hp", "atk", "defense", "spa", "spd", "spe"]


class TrainingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["nature", "iv", "ivs"]
    nature_id: Annotated[int, Field(strict=True, ge=0, le=24)] | None = None
    stat: Stat | None = None

    @model_validator(mode="after")
    def shape(self):
        if ((self.kind == "nature") != (self.nature_id is not None)
            or (self.kind == "iv") != (self.stat is not None)):
            raise ValueError("Invalid virtual consumable choice")
        return self


class TrainingReserveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_id: UUID
    pokemon_entity_id: UUID
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    change: TrainingChange


class TrainingReleaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrainingReceipt(BaseModel):
    season_id: UUID
    trainer_id: UUID
    operation_id: UUID
    purchase_id: UUID
    purchase_season_id: UUID
    pokemon_entity_id: UUID
    save_file_id: UUID
    identity_revision_id: UUID
    status: Literal["RESERVED", "APPLIED", "RELEASED"]
    intent: dict
    reserved_at: datetime
    finished_at: datetime | None
    result: dict | None


class TrainingItem(BaseModel):
    purchase_id: UUID
    purchase_season_id: UUID
    item_code: Literal["menta_naturaleza", "chapa_plateada", "chapa_dorada"]
    name: str
    effect: Literal["nature", "iv", "ivs"]


class TrainingPokemon(BaseModel):
    species: str
    nickname: str
    level: int = Field(ge=1, le=100)
    nature_id: int = Field(ge=0, le=24)
    ivs: dict[Stat, int]
    is_shiny: bool
    form: int


class TrainingTarget(BaseModel):
    pokemon_entity_id: UUID
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    game: Literal["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"]
    source: Literal["party", "box"]
    box_number: int = Field(ge=0, le=32)
    slot_number: int = Field(ge=1, le=30)
    pokemon: TrainingPokemon


class TrainingList(BaseModel):
    items: list[TrainingItem]
    targets: list[TrainingTarget]
    operations: list[TrainingReceipt]


def execute(container, operation, *args):
    service = getattr(container, "training_service", None)
    if service is None:
        raise api_error(503, "TRAINING_UNAVAILABLE", "El entrenamiento no está disponible ahora.")
    try:
        return getattr(service, operation)(*args)
    except SeasonAdminRejected as error:
        raise api_error(error.status, error.code, "No se puede aplicar este consumible ahora.") from None
    except SaveError as error:
        raise api_error(422, error.code.value, "No se pudo verificar la partida.") from None
    except PersistenceError:
        raise api_error(503, "TRAINING_UNAVAILABLE", "No se puede verificar el entrenamiento ahora.") from None
    except Exception as error:
        # Native writer exceptions contain only bounded public error codes;
        # unrelated exceptions and payloads never escape the server boundary.
        from app.save_parser.writer import NativeWriteError

        if isinstance(error, NativeWriteError):
            raise api_error(409, error.code, "El cambio no puede aplicarse de forma segura.") from None
        raise api_error(503, "TRAINING_UNAVAILABLE", "No se puede verificar el entrenamiento ahora.") from None


@router.get("", response_model=TrainingList)
def listing(season_id: UUID, principal=Reader, container=Container):
    return execute(container, "listing", str(season_id), principal.trainer_id)


@router.put("/{operation_id}", response_model=TrainingReceipt)
def reserve(season_id: UUID, operation_id: UUID, payload: TrainingReserveBody, principal=Reader, container=Container):
    return execute(container, "reserve", str(season_id), principal.trainer_id, str(operation_id), payload.model_dump(mode="json"))


@router.put("/{operation_id}/complete", response_model=TrainingReceipt)
async def complete(season_id: UUID, operation_id: UUID, request: Request, principal=Reader, container=Container):
    if request.headers.get("content-type") != "application/octet-stream":
        raise api_error(415, "TRAINING_BYTES_REQUIRED", "Se necesita el resultado original de la escritura.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_SAVE_BYTES:
            raise api_error(413, "TRAINING_RESULT_TOO_LARGE", "La partida supera el tamaño permitido.")
    if not data:
        raise api_error(422, "TRAINING_BYTES_REQUIRED", "Se necesita el resultado original de la escritura.")
    return await run_in_threadpool(execute, container, "complete", str(season_id), principal.trainer_id, str(operation_id), bytes(data))


@router.put("/{operation_id}/release", response_model=TrainingReceipt)
def release(season_id: UUID, operation_id: UUID, payload: TrainingReleaseBody, principal=Reader, container=Container):
    return execute(container, "release", str(season_id), principal.trainer_id, str(operation_id))
