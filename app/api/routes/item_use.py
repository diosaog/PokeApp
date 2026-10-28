from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.routes.purchases import IdempotencyHeader
from app.api.schemas import (
    ItemArtifactResponse,
    ItemUseClaimBody,
    ItemUseCompleteBody,
    ItemUseListResponse,
    ItemUsePrepareBody,
    ItemUseResponse,
)
from app.api.security import require_enabled_principal
from app.application.item_use import prepare_item_use
from app.domain.item_use_status import physical_state
from app.repositories.errors import ItemUseRejectedError, PersistenceError
from app.save_parser.native_sizes import NATIVE_SIZES

router = APIRouter(tags=["item-use"])
Reader = Depends(require_enabled_principal)
ContainerReader = Depends(get_api_container)


def _repo(container: ApiContainer):
    if container.item_use_repository is None:
        raise api_error(
            503, "ITEM_USE_UNAVAILABLE", "La aplicación física no está disponible."
        )
    return container.item_use_repository


def _execute(operation, *args):
    try:
        return operation(*args)
    except ItemUseRejectedError as exc:
        raise api_error(
            exc.status, exc.code, "La operación de objeto no puede continuar."
        ) from None
    except PersistenceError:
        raise api_error(
            503, "ITEM_USE_UNAVAILABLE", "No se puede comprobar la operación ahora."
        ) from None


@router.post(
    "/v1/seasons/{season_id}/shop/purchases/{purchase_id}/item-use",
    response_model=ItemUseResponse,
)
def prepare(
    season_id: UUID,
    purchase_id: UUID,
    payload: ItemUsePrepareBody,
    idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    result = _execute(
        lambda: prepare_item_use(
            _repo(container),
            season_id=str(season_id),
            trainer_id=principal.trainer_id,
            purchase_id=str(purchase_id),
            pokemon_entity_id=str(payload.pokemon_entity_id),
            save_file_id=str(payload.save_file_id),
            save_sha256=payload.save_sha256,
            idempotency_key=idempotency_key,
            operation_id=payload.operation_id,
        )
    )
    return _receipt(result, season_id, principal.trainer_id)


@router.get(
    "/v1/launcher/seasons/{season_id}/item-uses",
    response_model=ItemUseListResponse,
)
def pending(
    season_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    rows = _execute(lambda: _repo(container).list(str(season_id), principal.trainer_id))
    return ItemUseListResponse(
        items=[_receipt(row, season_id, principal.trainer_id) for row in rows]
    )


@router.put(
    "/v1/launcher/seasons/{season_id}/item-uses/{authorization_id}",
    response_model=ItemUseResponse,
)
def complete(
    season_id: UUID,
    authorization_id: UUID,
    payload: ItemUseCompleteBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    result = _execute(
        lambda: _repo(container).complete(
            str(authorization_id),
            str(season_id),
            principal.trainer_id,
            payload.model_dump(mode="json"),
        )
    )
    return _receipt(result, season_id, principal.trainer_id)


def _receipt(result, season_id, trainer_id):
    try:
        receipt = ItemUseResponse.model_validate(
            result | {"physical_state": physical_state(result["effect_code"], result)}
        )
        if (
            str(receipt.season_id) != str(season_id)
            or str(receipt.trainer_id) != trainer_id
        ):
            raise ValueError("scope mismatch")
        return receipt
    except (ValidationError, ValueError, TypeError, KeyError):
        raise api_error(
            503, "ITEM_USE_UNAVAILABLE", "La autorización no coincide."
        ) from None


@router.put(
    "/v1/launcher/seasons/{season_id}/item-uses/{authorization_id}/claim",
    response_model=ItemUseResponse,
)
def claim(
    season_id: UUID,
    authorization_id: UUID,
    payload: ItemUseClaimBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    result = _execute(
        lambda: _repo(container).claim(
            str(authorization_id),
            str(season_id),
            principal.trainer_id,
            payload.model_dump(mode="json"),
        )
    )
    return _receipt(result, season_id, principal.trainer_id)


def _transport(container):
    if container.item_use_transport is None:
        raise api_error(
            503, "ITEM_USE_UNAVAILABLE", "La verificación no está habilitada."
        )
    return container.item_use_transport


@router.put(
    "/v1/launcher/seasons/{season_id}/item-uses/{authorization_id}/result",
    response_model=ItemArtifactResponse,
    response_model_exclude_none=True,
)
async def submit_result(
    season_id: UUID,
    authorization_id: UUID,
    claim_id: UUID,
    request: Request,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    transport = _transport(container)
    scope = (str(authorization_id), str(season_id), principal.trainer_id, str(claim_id))
    _execute(lambda: transport.scope(*scope))
    if request.headers.get("content-type") != "application/octet-stream":
        raise api_error(
            415, "SAVE_BYTES_REQUIRED", "Se necesita el archivo resultante."
        )
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > max(NATIVE_SIZES.values()):
            raise api_error(413, "SAVE_TOO_LARGE", "El archivo es demasiado grande.")
    return await run_in_threadpool(_execute, transport.submit, *scope, bytes(data))


@router.get(
    "/v1/launcher/seasons/{season_id}/item-uses/{authorization_id}/result",
    response_model=ItemArtifactResponse,
    response_model_exclude_none=True,
)
def result_status(
    season_id: UUID,
    authorization_id: UUID,
    claim_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    return _execute(
        _transport(container).status,
        str(authorization_id),
        str(season_id),
        principal.trainer_id,
        str(claim_id),
    )
