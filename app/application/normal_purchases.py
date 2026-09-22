from __future__ import annotations

from app.domain.normal_purchases import NormalPurchaseReceipt, NormalPurchaseRequest
from app.repositories.protocols import NormalPurchaseRepository


def create_normal_purchase_v2(
    repository: NormalPurchaseRepository, *, season_id: str, trainer_id: str,
    item_id: str, idempotency_key: str, confirm_base_price: bool = False,
) -> NormalPurchaseReceipt:
    # Eligibility and effects share one database transaction, not separate API reads.
    return repository.create_normal_purchase(NormalPurchaseRequest(
        season_id=season_id, trainer_id=trainer_id, item_id=item_id,
        idempotency_key=idempotency_key, confirm_base_price=confirm_base_price,
    ))
