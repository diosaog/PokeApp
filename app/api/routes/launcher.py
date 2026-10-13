"""Authenticated private observation receipt, separate from competitive ingestion."""

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.errors import api_error
from app.api.routes.cups import Reader
from app.api.routes.season_admin import Container
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.cloud import (
    MAX_OBSERVATION_BYTES,
    CloudObservation,
    ObservationReceipt,
)

router = APIRouter(
    prefix="/v1/launcher/seasons/{season_id}/observations", tags=["launcher"]
)


def execute(operation, season_id, observation_id, principal, container, body=None):
    tid, sid, oid = str(principal.trainer_id), str(season_id), str(observation_id)
    if body is not None and body.identifier(tid, sid) != oid:
        raise api_error(409, "OBSERVATION_ID_MISMATCH", "Observation identity changed.")
    request = {"trainer_id": tid, "season_id": sid, "id": oid}
    if body is not None:
        request.update(body=body.model_dump(mode="json"), payload_digest=body.digest())
    try:
        if container.launcher_repository is None:
            raise PersistenceError("Missing observation backend")
        receipt = ObservationReceipt.model_validate(
            container.launcher_repository.execute(operation, request)
        )
        if (receipt.id, receipt.trainer_id, receipt.season_id) != (oid, tid, sid):
            raise ValueError("Receipt scope mismatch")
        if body is not None and receipt.payload_digest != body.digest():
            raise ValueError("Receipt digest mismatch")
        return receipt
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Observation request rejected.") from exc
    except (PersistenceError, ValueError, TypeError) as exc:
        raise api_error(
            503, "OBSERVATION_UNAVAILABLE", "Observation status unavailable."
        ) from exc


@router.get("/{observation_id}", response_model=ObservationReceipt)
def receipt(
    season_id: UUID, observation_id: UUID, principal: Reader, container: Container
):
    return execute("receipt", season_id, observation_id, principal, container)


@router.put("/{observation_id}", response_model=ObservationReceipt)
async def receive(
    season_id: UUID,
    observation_id: UUID,
    request: Request,
    principal: Reader,
    container: Container,
):
    # Bound actual bytes before JSON decoding; Content-Length alone is untrusted.
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_OBSERVATION_BYTES:
            raise api_error(413, "OBSERVATION_TOO_LARGE", "Observation is too large.")
    try:
        body = CloudObservation.model_validate_json(data)
    except ValidationError:
        raise api_error(422, "INVALID_OBSERVATION", "Invalid observation.") from None
    return await run_in_threadpool(
        execute, "receive", season_id, observation_id, principal, container, body
    )
