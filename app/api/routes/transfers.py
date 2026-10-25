"""Paired robbery routes. Disabled (503) unless the engineering service is wired.

Nothing here issues a proof, completes a leg or consumes an entitlement: the
restricted verifier alone does that. Trainer scope is the authenticated principal.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.routes.purchases import IdempotencyHeader
from app.api.schemas import (
    TransferLauncherListResponse,
    TransferLegBody,
    TransferLegResponse,
    TransferListResponse,
    TransferRequestBody,
    TransferRequestResponse,
)
from app.api.security import require_enabled_principal
from app.application.item_use_verification import VerificationRejected
from app.repositories.errors import PersistenceError, TransferRejectedError
from app.save_parser.writer import NATIVE_SIZES

router = APIRouter(tags=["transfers"])
Reader = Depends(require_enabled_principal)
ContainerReader = Depends(get_api_container)

MESSAGES = {
    "TRANSFER_FORBIDDEN": "Los robos entre guardados no están habilitados para tu cuenta.",
    "TRANSFER_PEER_UNAVAILABLE": "Ese entrenador todavía no puede participar en robos entre guardados.",
    "TRANSFER_TARGET_INVALID": "Ese Pokémon no se puede robar.",
    "TRANSFER_NATIVE_SCOPE_UNQUALIFIED": "Solo se pueden robar Pokémon guardados en las cajas 1–7. Los del equipo todavía no están admitidos.",
    "STEAL_TARGET_SHIELDED": "Ese Pokémon está blindado o ya ha sido robado.",
    "STEAL_VICTIM_ALREADY_ROBBED": "Ese entrenador ya ha sido robado en este ciclo.",
    "TRANSFER_RESERVED": "Uno de los entrenadores ya tiene una operación en curso.",
    "PURCHASE_NOT_REDEEMABLE": "Este objeto ya no está disponible para canjear.",
    "SAVE_CONTEXT_CHANGED": "Los guardados han cambiado. Sincroniza y vuelve a intentarlo.",
    "PARTICIPANT_INACTIVE": "Uno de los entrenadores no participa en la Liga activa.",
    "TRANSFER_PEER_PENDING": "Esperando al otro entrenador.",
    "TRANSFER_EXPIRED": "La autorización ha caducado.",
    "TRANSFER_ASSISTED_RECOVERY_REQUIRED": "Ya se ha aplicado una parte: no se puede cancelar. El Launcher completará o recuperará la operación.",
    "TRANSFER_TERMINAL": "La operación ya ha terminado.",
    "TRANSFER_NOT_OWNED": "Esta operación no te pertenece.",
    "TRANSFER_NOT_FOUND": "No se encuentra la operación.",
}


def _service(container: ApiContainer):
    if container.transfer_integration is None:
        raise api_error(
            503,
            "TRANSFER_UNAVAILABLE",
            "Los robos entre guardados no están habilitados.",
        )
    return container.transfer_integration


def _execute(operation, *args):
    try:
        return operation(*args)
    except TransferRejectedError as exc:
        raise api_error(
            exc.status,
            exc.code,
            MESSAGES.get(exc.code, "La operación de robo no puede continuar."),
        ) from None
    except PersistenceError:
        raise api_error(
            503, "TRANSFER_UNAVAILABLE", "No se puede comprobar el robo ahora."
        ) from None
    except VerificationRejected:
        raise api_error(
            422, "SAVE_REJECTED", "El archivo resultante no es válido."
        ) from None


def _validated(model, value):
    try:
        return model.model_validate(value)
    except (ValidationError, TypeError, ValueError):
        raise api_error(
            503, "TRANSFER_UNAVAILABLE", "La operación no coincide."
        ) from None


@router.post(
    "/v1/seasons/{season_id}/shop/purchases/{purchase_id}/transfer",
    response_model=TransferRequestResponse,
)
def request_transfer(
    season_id: UUID,
    purchase_id: UUID,
    payload: TransferRequestBody,
    idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    try:
        operation_id = str(UUID(idempotency_key))
    except ValueError:
        raise api_error(
            422, "INVALID_IDEMPOTENCY_KEY", "Solicitud no válida."
        ) from None
    service = _service(container)
    return _validated(
        TransferRequestResponse,
        _execute(
            lambda: service.request(
                str(season_id),
                principal.trainer_id,
                str(purchase_id),
                str(payload.pokemon_entity_id),
                operation_id,
            )
        ),
    )


@router.get("/v1/seasons/{season_id}/transfers", response_model=TransferListResponse)
def list_transfers(
    season_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = container.transfer_integration
    if service is None:
        return TransferListResponse(items=[])
    rows = _execute(lambda: service.list(str(season_id), principal.trainer_id))
    return _validated(
        TransferListResponse,
        {"items": rows, "transfer_enabled": service.enabled(principal.trainer_id)},
    )


@router.post(
    "/v1/seasons/{season_id}/transfers/{authorization_id}/cancel",
    response_model=TransferLegResponse,
)
def withdraw_transfer(
    season_id: UUID,
    authorization_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = _service(container)
    return _validated(
        TransferLegResponse,
        _execute(
            service.withdraw,
            str(season_id),
            principal.trainer_id,
            str(authorization_id),
        ),
    )


@router.get(
    "/v1/launcher/seasons/{season_id}/transfers",
    response_model=TransferLauncherListResponse,
)
def launcher_transfers(
    season_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = container.transfer_integration
    if service is None:
        return TransferLauncherListResponse(items=[])
    rows = _execute(
        lambda: service.list(str(season_id), principal.trainer_id, launcher=True)
    )
    return _validated(
        TransferLauncherListResponse,
        {"items": rows, "transfer_enabled": service.enabled(principal.trainer_id)},
    )


@router.get(
    "/v1/launcher/seasons/{season_id}/transfers/{authorization_id}",
    response_model=TransferLegResponse,
)
def transfer_leg(
    season_id: UUID,
    authorization_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = _service(container)
    return _validated(
        TransferLegResponse,
        _execute(
            service.leg,
            str(season_id),
            principal.trainer_id,
            str(authorization_id),
            "get",
        ),
    )


@router.put(
    "/v1/launcher/seasons/{season_id}/transfers/{authorization_id}",
    response_model=TransferLegResponse,
)
def update_leg(
    season_id: UUID,
    authorization_id: UUID,
    payload: TransferLegBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = _service(container)
    if (payload.operation == "cancel") != (payload.claim_id is None) or (
        payload.operation == "ready"
    ) != (payload.backup_sha256 is not None):
        raise api_error(422, "INVALID_TRANSFER_OPERATION", "Solicitud no válida.")
    return _validated(
        TransferLegResponse,
        _execute(
            lambda: service.leg(
                str(season_id),
                principal.trainer_id,
                str(authorization_id),
                payload.operation,
                claim_id=str(payload.claim_id) if payload.claim_id else None,
                backup_sha256=payload.backup_sha256,
            )
        ),
    )


@router.put(
    "/v1/launcher/seasons/{season_id}/transfers/{authorization_id}/result",
    response_model=TransferLegResponse,
)
async def submit_result(
    season_id: UUID,
    authorization_id: UUID,
    claim_id: UUID,
    request: Request,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    service = _service(container)
    if request.headers.get("content-type") != "application/octet-stream":
        raise api_error(
            415, "SAVE_BYTES_REQUIRED", "Se necesita el archivo resultante."
        )
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > max(NATIVE_SIZES.values()):
            raise api_error(413, "SAVE_TOO_LARGE", "El archivo es demasiado grande.")
    row = await run_in_threadpool(
        _execute,
        service.submit,
        str(season_id),
        principal.trainer_id,
        str(authorization_id),
        str(claim_id),
        bytes(data),
    )
    return _validated(TransferLegResponse, row)
