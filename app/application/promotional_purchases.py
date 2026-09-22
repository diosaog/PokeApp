from app.domain.promotional_purchases import PromotionalPurchaseReceipt, PromotionalPurchaseRequest
from app.repositories.protocols import PromotionalPurchaseRepository


def create_promotional_purchase_v2(
    repository: PromotionalPurchaseRepository, *, season_id: str, trainer_id: str,
    promotion_id: str, idempotency_key: str,
) -> PromotionalPurchaseReceipt:
    return repository.create_promotional_purchase(PromotionalPurchaseRequest(
        season_id=season_id, trainer_id=trainer_id,
        promotion_id=promotion_id, idempotency_key=idempotency_key,
    ))
