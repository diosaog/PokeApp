"""«Mi PC» outside seasons: the trainer's own latest synced save (065).

Same wire protocol as /v1/seasons/{id}/saves (context, receipt, raw) so the
Launcher's outbox delivers it unchanged; /v1/me/pc reads it back.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.api.errors import api_error
from app.api.progress_models import ProgressRead
from app.api.read_models import PCRead
from app.api.routes.cups import Reader
from app.api.routes.saves import Hash
from app.api.routes.season_admin import Container
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.files import MAX_SAVE_BYTES
from app.save_parser.registration import SaveRegistration

router = APIRouter(prefix="/v1/me", tags=["saves"])
public_router = APIRouter(prefix="/v1/read", tags=["saves"])


class ActiveSaveRead(BaseModel):
    trainer_id: UUID
    game: str | None
    uploaded_at: datetime
    progress: ProgressRead


class ActiveSavePage(BaseModel):
    items: list[ActiveSaveRead]


def execute(container, operation, *args):
    try:
        if container.personal_saves is None:
            raise PersistenceError("personal_saves_not_configured")
        return getattr(container.personal_saves, operation)(*args)
    except SeasonAdminRejected as error:
        raise api_error(
            error.status, error.code, "No se pudo registrar tu partida. Revisa el archivo."
        ) from None
    except (PersistenceError, ValueError, TypeError):
        raise api_error(
            503, "SAVE_UNAVAILABLE", "No se puede verificar tu partida ahora."
        ) from None


@router.get("/save/context")
def context(principal: Reader, container: Container):
    return execute(container, "context", str(principal.trainer_id))


@router.get("/save/receipt", response_model=SaveRegistration)
def receipt(sha256: Hash, principal: Reader, container: Container):
    return execute(container, "receipt", str(principal.trainer_id), sha256)


@router.put("/save/raw", response_model=SaveRegistration)
async def receive(
    sha256: Hash,
    observation_digest: Hash,
    request: Request,
    principal: Reader,
    container: Container,
    expected_save_id: str = Query(default="none", pattern=r"^(none|[0-9a-f-]{36})$"),
):
    # expected_save_id is accepted for wire compatibility: the personal save is
    # the trainer's latest file, there is no cross-device CAS to honour.
    if request.headers.get("content-type") != "application/octet-stream":
        raise api_error(415, "SAVE_BYTES_REQUIRED", "Se necesita el archivo original.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_SAVE_BYTES:
            raise api_error(413, "SAVE_TOO_LARGE", "El save es demasiado grande.")
    return await run_in_threadpool(
        execute, container, "receive", str(principal.trainer_id), sha256, observation_digest, bytes(data)
    )


@router.get("/pc", response_model=PCRead)
def pc(principal: Reader, container: Container):
    return execute(container, "pc", str(principal.trainer_id))


@public_router.get("/active-saves", response_model=ActiveSavePage)
def active_saves(principal: Reader, container: Container):
    """Each trainer's active save (game and badges), for «Entrenadores»."""
    return execute(container, "summaries")
