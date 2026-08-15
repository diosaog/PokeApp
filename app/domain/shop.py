from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    PurchaseId,
    RedemptionId,
    SeasonId,
    ShopItemId,
    ShopPromotionId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_int,
    require_positive_int,
    StringEnum,
)


class PromotionKind(StringEnum):
    NORMAL = "normal"
    MEGA = "mega"


class PromotionState(StringEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class PurchaseStatus(StringEnum):
    PENDING = "pending"
    USED = "used"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ShopItem:
    id: ShopItemId
    category: str
    name: str
    description: str
    base_price: int
    image_url: str = ""
    enabled: bool = True
    stock_rule: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "shop_item.id"))
        object.__setattr__(self, "category", require_id(self.category, "shop_item.category"))
        object.__setattr__(self, "name", require_id(self.name, "shop_item.name"))
        object.__setattr__(self, "description", clean_text(self.description))
        object.__setattr__(self, "base_price", require_non_negative_int(self.base_price, "shop_item.base_price"))
        object.__setattr__(self, "image_url", clean_text(self.image_url))
        object.__setattr__(self, "stock_rule", clean_text(self.stock_rule))


@dataclass(frozen=True)
class ShopPromotion:
    id: ShopPromotionId
    item_id: ShopItemId
    season_id: SeasonId = ""
    matchday_number: int | None = None
    kind: PromotionKind = PromotionKind.NORMAL
    base_price: int = 0
    discount_price: int = 0
    stock_total: int = 0
    stock_used: int = 0
    announced_at: UtcTimestamp = ""
    activates_at: UtcTimestamp = ""
    ends_at: UtcTimestamp = ""
    state: PromotionState = PromotionState.PENDING
    dedupe_key: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "shop_promotion.id"))
        object.__setattr__(self, "item_id", require_id(self.item_id, "shop_promotion.item_id"))
        object.__setattr__(self, "season_id", optional_id(self.season_id))
        if self.matchday_number is not None:
            object.__setattr__(self, "matchday_number", require_positive_int(self.matchday_number, "shop_promotion.matchday_number"))
        object.__setattr__(self, "base_price", require_non_negative_int(self.base_price, "shop_promotion.base_price"))
        object.__setattr__(self, "discount_price", require_non_negative_int(self.discount_price, "shop_promotion.discount_price"))
        object.__setattr__(self, "stock_total", require_non_negative_int(self.stock_total, "shop_promotion.stock_total"))
        object.__setattr__(self, "stock_used", require_non_negative_int(self.stock_used, "shop_promotion.stock_used"))
        if self.stock_used > self.stock_total:
            raise ValueError("shop_promotion.stock_used cannot exceed stock_total.")
        object.__setattr__(self, "dedupe_key", clean_text(self.dedupe_key))


@dataclass(frozen=True)
class Purchase:
    id: PurchaseId
    trainer_id: TrainerId
    item_id: ShopItemId
    item_name: str
    quantity: int
    unit_price: int
    total_price: int
    purchased_at: UtcTimestamp
    status: PurchaseStatus = PurchaseStatus.PENDING
    season_id: SeasonId = ""
    matchday_number: int | None = None
    promotion_id: ShopPromotionId = ""
    base_unit_price: int | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "purchase.id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "purchase.trainer_id"))
        object.__setattr__(self, "item_id", require_id(self.item_id, "purchase.item_id"))
        object.__setattr__(self, "item_name", require_id(self.item_name, "purchase.item_name"))
        object.__setattr__(self, "quantity", require_positive_int(self.quantity, "purchase.quantity"))
        object.__setattr__(self, "unit_price", require_non_negative_int(self.unit_price, "purchase.unit_price"))
        object.__setattr__(self, "total_price", require_non_negative_int(self.total_price, "purchase.total_price"))
        if self.total_price != self.quantity * self.unit_price:
            raise ValueError("purchase.total_price must equal quantity * unit_price.")
        object.__setattr__(self, "purchased_at", clean_text(self.purchased_at))
        if not self.purchased_at:
            raise ValueError("purchase.purchased_at must be set.")
        object.__setattr__(self, "season_id", optional_id(self.season_id))
        object.__setattr__(self, "promotion_id", optional_id(self.promotion_id))


@dataclass(frozen=True)
class Redemption:
    id: RedemptionId
    purchase_id: PurchaseId
    trainer_id: TrainerId
    item_id: ShopItemId
    item_name: str
    redeemed_at: UtcTimestamp
    payload: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "redemption.id"))
        object.__setattr__(self, "purchase_id", require_id(self.purchase_id, "redemption.purchase_id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "redemption.trainer_id"))
        object.__setattr__(self, "item_id", require_id(self.item_id, "redemption.item_id"))
        object.__setattr__(self, "item_name", require_id(self.item_name, "redemption.item_name"))
        object.__setattr__(self, "redeemed_at", clean_text(self.redeemed_at))
