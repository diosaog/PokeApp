"""One raw-save registration API for Launcher and future web upload adapters."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from starlette.concurrency import run_in_threadpool

from app.api.errors import api_error
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Container
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.files import MAX_SAVE_BYTES
from app.save_parser.registration import SaveRegistration

router = APIRouter(prefix="/v1/seasons/{season_id}/saves", tags=["saves"])
Hash = Annotated[str, Query(pattern=r"^[0-9a-f]{64}$")]


def execute(container, operation, *args):
    try:
        if container.save_ingestion is None:
            raise PersistenceError("save_ingestion_not_configured")
        return getattr(container.save_ingestion, operation)(*args)
    except SeasonAdminRejected as error:
        raise api_error(
            error.status,
            error.code,
            "No se pudo registrar el save. Revisa el archivo y el contexto.",
        ) from None
    except (PersistenceError, ValueError, TypeError):
        raise api_error(
            503, "SAVE_UNAVAILABLE", "No se puede verificar el save ahora."
        ) from None


@router.get("/context")
def context(season_id: UUID, principal: Reader, container: Container):
    return execute(container, "context", str(season_id), str(principal.trainer_id))


@router.get("/receipt", response_model=SaveRegistration)
def receipt(season_id: UUID, sha256: Hash, principal: Reader, container: Container):
    return execute(
        container, "receipt", str(season_id), str(principal.trainer_id), sha256
    )


@router.put("/raw", response_model=SaveRegistration)
async def receive(
    season_id: UUID,
    sha256: Hash,
    observation_digest: Hash,
    expected_save_id: Annotated[str, Query(pattern=r"^(none|[0-9a-f-]{36})$")],
    request: Request,
    principal: Reader,
    container: Container,
):
    if request.headers.get("content-type") != "application/octet-stream":
        raise api_error(415, "SAVE_BYTES_REQUIRED", "Se necesita el archivo original.")
    try:
        expected = None if expected_save_id == "none" else str(UUID(expected_save_id))
    except ValueError:
        raise api_error(
            422, "INVALID_SAVE_CONTEXT", "Contexto de save no valido."
        ) from None
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_SAVE_BYTES:
            raise api_error(413, "SAVE_TOO_LARGE", "El save es demasiado grande.")
    return await run_in_threadpool(
        execute,
        container,
        "receive",
        str(season_id),
        str(principal.trainer_id),
        sha256,
        expected,
        observation_digest,
        bytes(data),
    )
