from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.routes.purchases import IdempotencyHeader
from app.api.schemas import (
    ItemUseCompleteBody,
    ItemUseListResponse,
    ItemUsePrepareBody,
    ItemUseResponse,
)
from app.api.security import require_enabled_principal
from app.application.item_use import prepare_item_use
from app.repositories.errors import ItemUseRejectedError, PersistenceError


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
    return ItemUseResponse.model_validate(result)


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
        items=[ItemUseResponse.model_validate(row) for row in rows]
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
            payload.model_dump(),
        )
    )
    if (
        str(result.get("season_id")) != str(season_id)
        or str(result.get("trainer_id")) != principal.trainer_id
    ):
        raise api_error(503, "ITEM_USE_UNAVAILABLE", "La autorización no coincide.")
    return ItemUseResponse.model_validate(result)
