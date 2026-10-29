"""In-game Shop objects (072, owner decision 2026-10-29).

The trainer's PokeApp Launcher adds a bought object to the bag of the league
save and the server spends the purchase once: reserve (nothing spent yet) ->
the Launcher writes and natively re-reads the save -> complete; a write that
did not happen releases the reservation. The object, its game item id and
the games it exists in come from the server-owned contract
(app/domain/shop_item_uses.py), never from the client. Captura Extra has no
object: «usar» records its use once.
"""

from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.read_models import GameCode, ItemUseOption
from app.api.routes.purchases import IdempotencyHeader
from app.api.security import require_enabled_principal
from app.domain.shop_item_uses import BAG_ITEMS, GAMES, item_games, use_of
from app.repositories.errors import ItemDeliveryRejectedError, PersistenceError

router = APIRouter(tags=["item-delivery"])
Reader = Depends(require_enabled_principal)
ContainerReader = Depends(get_api_container)


class DeliveryReserveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_id: UUID
    item: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    game: GameCode


class DeliveryCompleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    output_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DeliveryReleaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeliveryReceipt(BaseModel):
    delivery_id: UUID
    purchase_id: UUID
    season_id: UUID
    trainer_id: UUID
    operation_id: UUID
    kind: Literal["bag", "permission"]
    item_code: str | None
    game_item_id: int | None
    game: GameCode | None
    status: Literal["RESERVED", "DELIVERED", "RELEASED", "USED"]
    reserved_at: datetime
    finished_at: datetime | None
    purchase_status: str
    # Only reservation supplies this server-derived native identity. The
    # Launcher compares it with the bytes it is about to write, not a cached
    # parse or a client-selected game.
    authorized_trainer_key: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class PendingDelivery(BaseModel):
    operation_id: UUID
    item_code: str
    game: GameCode


class DeliverablePurchase(BaseModel):
    purchase_id: UUID
    shop_code: str
    name: str
    mode: Literal["bag", "choice"]
    options: list[ItemUseOption]
    # A reservation this trainer's Launcher started and has not finished.
    reserved: PendingDelivery | None = None


class DeliveryList(BaseModel):
    items: list[DeliverablePurchase]
    league_game: GameCode | None = None


def _repo(container: ApiContainer):
    repo = getattr(container, "item_delivery_repository", None)
    if repo is None:
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "La entrega de objetos no está disponible.")
    return repo


def _call(operation, *args):
    try:
        return DeliveryReceipt.model_validate(operation(*args))
    except ItemDeliveryRejectedError as exc:
        raise api_error(exc.status, exc.code, "La entrega del objeto no puede continuar.") from None
    except (PersistenceError, ValueError):
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar la entrega ahora.") from None


def league_game(container: ApiContainer, season_id: str, trainer_id: str):
    """The game of the save this trainer's season accepted, or None."""
    reads = getattr(container, "frontend_read_repository", None)
    if reads is None:
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar tu partida ahora.")
    from app.application.frontend_reads import FrontendReads

    try:
        return FrontendReads(reads).league_game(season_id, trainer_id)
    except (PersistenceError, KeyError, TypeError, ValueError):
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar tu partida ahora.") from None


def _authorized_identity(container, sid, tid):
    """Use only the identity accepted by the server for this participant."""
    from app.application.frontend_reads import FrontendReads
    from app.save_parser.models import ParsedTrainer

    reads = getattr(container, "frontend_read_repository", None)
    if reads is None:
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar tu partida ahora.")
    try:
        identity = FrontendReads(reads).league_identity(sid, tid)
        if not identity:
            raise api_error(409, "DELIVERY_SAVE_NOT_BOUND", "Sincroniza primero tu partida de la Liga.")
        game = identity["game"]
        trainer = ParsedTrainer.model_validate(identity["trainer"])
        if game not in GAMES or trainer.language is None:
            raise ValueError("incomplete_save_identity")
        key = sha256("\0".join((game, trainer.name, str(trainer.tid), str(trainer.sid),
                                str(trainer.gender), str(trainer.language))).encode()).hexdigest()
        return game, key
    except (PersistenceError, KeyError, TypeError, ValueError):
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar tu partida ahora.") from None


def _option(code):
    return ItemUseOption(code=code, name=BAG_ITEMS[code][1], item_id=BAG_ITEMS[code][0], games=list(item_games(code)))


@router.get("/v1/launcher/seasons/{season_id}/deliveries", response_model=DeliveryList)
def deliveries(
    season_id: UUID,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    repo, sid, tid = _repo(container), str(season_id), principal.trainer_id
    try:
        purchases = repo.purchases(sid, tid)
        live = {
            d["purchase_id"]: d for d in repo.deliveries(sid, tid) if d["status"] == "RESERVED"
        }
    except PersistenceError:
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar la entrega ahora.") from None
    items = []
    for purchase in purchases:
        use = use_of(purchase["code"])
        if purchase["status"] != "pending" or use["mode"] not in ("bag", "choice"):
            continue
        reserved = live.get(purchase["id"])
        items.append(
            DeliverablePurchase(
                purchase_id=purchase["id"],
                shop_code=purchase["code"],
                name=purchase["name"],
                mode=use["mode"],
                options=[_option(code) for code in use["items"]],
                reserved=PendingDelivery(
                    operation_id=reserved["operation_id"], item_code=reserved["item_code"], game=reserved["game"]
                )
                if reserved
                else None,
            )
        )
    return DeliveryList(items=items, league_game=league_game(container, sid, tid))


@router.put(
    "/v1/launcher/seasons/{season_id}/deliveries/{operation_id}",
    response_model=DeliveryReceipt,
)
def reserve(
    season_id: UUID,
    operation_id: UUID,
    payload: DeliveryReserveBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    """Idempotent per operation: the same request returns the same receipt."""
    repo, sid, tid = _repo(container), str(season_id), principal.trainer_id
    purchase_id = payload.purchase_id
    try:
        code = repo.purchase_code(sid, tid, str(purchase_id))
    except PersistenceError:
        raise api_error(503, "ITEM_DELIVERY_UNAVAILABLE", "No se puede comprobar la entrega ahora.") from None
    if code is None:
        raise api_error(404, "PURCHASE_NOT_FOUND", "La compra no existe.")
    use = use_of(code)
    if use["mode"] not in ("bag", "choice"):
        raise api_error(409, "DELIVERY_NOT_SUPPORTED", "Este artículo no se entrega en la bolsa.")
    if payload.item not in use["items"]:
        raise api_error(409, "DELIVERY_ITEM_NOT_OFFERED", "Ese objeto no corresponde a esta compra.")
    if payload.game not in item_games(payload.item):
        raise api_error(409, "ITEM_INCOMPATIBLE_WITH_GAME", "Ese objeto no existe en este juego.")
    # The object goes to the save this season competes with, never another one.
    bound, trainer_key = _authorized_identity(container, sid, tid)
    if bound != payload.game:
        raise api_error(409, "DELIVERY_OTHER_GAME", "La entrega es para tu partida de la Liga.")
    receipt = _call(
        repo.reserve, sid, tid, str(purchase_id), str(operation_id),
        payload.item, BAG_ITEMS[payload.item][0], payload.game,
    )  # fmt: skip
    return receipt.model_copy(update={"authorized_trainer_key": trainer_key})


@router.put(
    "/v1/launcher/seasons/{season_id}/deliveries/{operation_id}/complete",
    response_model=DeliveryReceipt,
)
def complete(
    season_id: UUID,
    operation_id: UUID,
    payload: DeliveryCompleteBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    return _call(
        _repo(container).complete, str(season_id), principal.trainer_id, str(operation_id),
        payload.source_sha256, payload.output_sha256,
    )  # fmt: skip


@router.put(
    "/v1/launcher/seasons/{season_id}/deliveries/{operation_id}/release",
    response_model=DeliveryReceipt,
)
def release(
    season_id: UUID,
    operation_id: UUID,
    payload: DeliveryReleaseBody,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    return _call(_repo(container).release, str(season_id), principal.trainer_id, str(operation_id))


@router.post(
    "/v1/seasons/{season_id}/shop/purchases/{purchase_id}/use",
    response_model=DeliveryReceipt,
)
def use_permission(
    season_id: UUID,
    purchase_id: UUID,
    idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Reader,
    container: ApiContainer = ContainerReader,
):
    # The same key always names the same use: a retried click is one use.
    operation = uuid5(NAMESPACE_URL, f"pokeapp:item-use:{principal.trainer_id}:{purchase_id}:{idempotency_key}")
    return _call(
        _repo(container).use_permission, str(season_id), principal.trainer_id, str(purchase_id), str(operation)
    )
