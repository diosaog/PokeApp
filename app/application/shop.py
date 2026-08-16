from __future__ import annotations

from app.domain.services import shop as shop_domain
from app.repositories import mappers
from app.repositories.errors import ConflictError, NotFoundError
from app.repositories.protocols import ShopRepository


def purchase_discounted_item(
    repository: ShopRepository,
    *,
    trainer_id: str,
    promotion_id: str,
    matchday_number: int,
    now: int,
) -> dict:
    promotion = repository.get_promotion(promotion_id)
    if promotion is None:
        raise NotFoundError(f"Promotion {promotion_id} not found.")

    claimed = repository.claimed_promotion_ids(trainer_id, (promotion_id,))
    decision = shop_domain.evaluate_discount_purchase(
        mappers.promotion_to_legacy_payload(promotion),
        trainer_id=trainer_id,
        promotion_id=mappers.as_int(promotion_id, 0),
        matchday_number=matchday_number,
        now=now,
        claimed_discount_ids={mappers.as_int(value, 0) for value in claimed},
    )
    if not decision.allowed:
        raise ConflictError(decision.reason)

    result = repository.purchase_discount(
        trainer_id=trainer_id,
        promotion_id=promotion_id,
        matchday_number=matchday_number,
    )
    if not bool(result.get("purchased")):
        raise ConflictError(str(result.get("reason") or "purchase_failed"))
    return result
