from dataclasses import dataclass
from uuid import UUID

from app.domain.normal_purchases import NormalPurchaseReceipt, validate_idempotency_key


@dataclass(frozen=True)
class PromotionalPurchaseRequest:
    season_id: str
    trainer_id: str
    promotion_id: str
    idempotency_key: str

    def __post_init__(self):
        for value in (self.season_id, self.trainer_id, self.promotion_id):
            UUID(value)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True)
class PromotionalPurchaseReceipt(NormalPurchaseReceipt):
    promotion_id: str
    base_price: int
    promotion_kind: str
    remaining_stock: int

    def __post_init__(self):
        super().__post_init__()
        UUID(self.promotion_id)
        if (type(self.base_price) is not int or self.base_price < self.unit_price
                or type(self.remaining_stock) is not int or self.remaining_stock < 0
                or self.promotion_kind not in ("normal", "mega")):
            raise ValueError("invalid_promotion_receipt")
