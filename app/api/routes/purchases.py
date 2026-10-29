from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.schemas import NormalPurchaseBody, NormalPurchaseResponse, PromotionalPurchaseBody, PromotionalPurchaseResponse
from app.api.security import require_enabled_principal
from app.application.normal_purchases import create_normal_purchase_v2
from app.application.promotional_purchases import create_promotional_purchase_v2
from app.repositories.errors import PersistenceError, PurchaseRejectedError


router = APIRouter(prefix="/v1/seasons", tags=["purchases"])
IdempotencyHeader = Annotated[str, Header(min_length=1, max_length=128, pattern=r"^[!-~]+$")]


def _usable_for_trainer(container, season_id, trainer_id, item_code):
    """072: never sell an object that cannot be used. Menta de Naturaleza
    exists in no Gen 6/7 game; an object absent from the trainer's league game
    (e.g. the Chapa Plateada in Pokémon Y) is refused while that game is known."""
    from app.api.routes.item_delivery import league_game
    from app.domain.shop_item_uses import purchase_refusal

    refusal = purchase_refusal(item_code, league_game(container, season_id, trainer_id))
    if refusal == "ITEM_NOT_USABLE":
        raise api_error(409, refusal, "Este objeto no existe en los juegos de PokeApp.")
    if refusal:
        raise api_error(409, refusal, "Este objeto no existe en el juego de tu partida de la Liga.")


def _item_code(container, lookup, *args):
    repo = getattr(container, "item_delivery_repository", None)
    if repo is None:
        return None
    try:
        return getattr(repo, lookup)(*args)
    except PersistenceError as exc:
        raise api_error(503, "PURCHASE_UNAVAILABLE", "Purchase backend is unavailable.") from exc


def _purchase_response(operation, repository, response_model, **args):
    if repository is None:
        raise api_error(503, "PURCHASE_UNAVAILABLE", "Purchase backend is unavailable.")
    try:
        result = operation(repository, **args)
    except PurchaseRejectedError as exc:
        raise api_error(exc.status, exc.code, "Purchase cannot be completed in the current state.") from exc
    except PersistenceError as exc:
        raise api_error(503, "PURCHASE_UNAVAILABLE", "Purchase backend is unavailable.") from exc
    return response_model.model_validate(result, from_attributes=True)


@router.post("/{season_id}/shop/purchases", response_model=NormalPurchaseResponse)
def post_normal_purchase(
    season_id: UUID, payload: NormalPurchaseBody,
    idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Depends(require_enabled_principal),
    container: ApiContainer = Depends(get_api_container),
) -> NormalPurchaseResponse:
    code = _item_code(container, "item_code", str(payload.item_id))
    if code is not None:
        _usable_for_trainer(container, str(season_id), principal.trainer_id, code)
    return _purchase_response(create_normal_purchase_v2, container.purchase_repository, NormalPurchaseResponse,
        season_id=str(season_id), trainer_id=principal.trainer_id,
        item_id=str(payload.item_id), idempotency_key=idempotency_key,
        confirm_base_price=payload.confirm_base_price)


@router.post("/{season_id}/shop/promotions/{promotion_id}/purchases", response_model=PromotionalPurchaseResponse)
def post_promotional_purchase(
    season_id: UUID, promotion_id: UUID, payload: PromotionalPurchaseBody,
    idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Depends(require_enabled_principal),
    container: ApiContainer = Depends(get_api_container),
) -> PromotionalPurchaseResponse:
    code = _item_code(container, "promotion_item_code", str(season_id), str(promotion_id))
    if code is not None:
        _usable_for_trainer(container, str(season_id), principal.trainer_id, code)
    return _purchase_response(create_promotional_purchase_v2, container.promotional_purchase_repository,
        PromotionalPurchaseResponse, season_id=str(season_id), trainer_id=principal.trainer_id,
        promotion_id=str(promotion_id), idempotency_key=idempotency_key)
