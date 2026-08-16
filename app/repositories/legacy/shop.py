from __future__ import annotations

from typing import Any

from app.domain.shop import Purchase, Redemption, ShopItem, ShopPromotion
from app.repositories import mappers


class LegacyShopRepository:
    def __init__(self, *, season_id: str = mappers.LEGACY_SEASON_ID) -> None:
        self.season_id = season_id

    def list_catalog(self) -> tuple[ShopItem, ...]:
        from app.tienda.catalog_data import get_catalog

        items: list[ShopItem] = []
        for category, rows in get_catalog().items():
            for row in rows:
                if isinstance(row, dict):
                    items.append(mappers.shop_item_from_catalog(category, row))
        return tuple(items)

    def list_promotions(
        self,
        *,
        matchday_number: int | None = None,
        active_only: bool | None = None,
    ) -> tuple[ShopPromotion, ...]:
        from storage import list_shop_discounts

        rows = list_shop_discounts(
            jornada=int(matchday_number) if matchday_number is not None else None,
            active_only=active_only,
        )
        return tuple(
            mappers.promotion_from_legacy(row, season_id=self.season_id)
            for row in rows
            if isinstance(row, dict)
        )

    def get_promotion(self, promotion_id: str) -> ShopPromotion | None:
        target = str(promotion_id)
        for promo in self.list_promotions():
            if str(promo.id) == target:
                return promo
        return None

    def create_promotion(self, promotion: ShopPromotion) -> ShopPromotion | None:
        from storage import create_shop_discount

        payload = mappers.promotion_to_legacy_payload(promotion)
        row = create_shop_discount(
            item=str(payload["item"]),
            category=str(payload.get("category") or ""),
            base_price=int(payload["base_price"]),
            discount_price=int(payload["discount_price"]),
            stock_total=int(payload["stock_total"]),
            discount_kind=str(payload["discount_kind"]),
            jornada=int(payload["jornada"]),
            announced_at=int(payload["announced_at"]),
            activates_at=int(payload["activates_at"]),
        )
        return (
            mappers.promotion_from_legacy(row, season_id=self.season_id)
            if isinstance(row, dict)
            else None
        )

    def purchase_counts_by_matchday(self, matchdays: tuple[int, ...]) -> dict[int, dict[str, int]]:
        from storage import purchase_counts_by_item_for_jornadas

        return purchase_counts_by_item_for_jornadas([int(value) for value in matchdays])

    def all_purchased_item_names(self) -> set[str]:
        from storage import all_purchased_items

        return set(all_purchased_items())

    def expire_promotions_through_matchday(self, matchday_number: int) -> None:
        from storage import expire_shop_discounts_through_jornada

        expire_shop_discounts_through_jornada(int(matchday_number))

    def claimed_promotion_ids(self, trainer_id: str, promotion_ids: tuple[str, ...]) -> set[str]:
        from storage import claimed_shop_discount_ids

        ids = [mappers.as_int(value, 0) for value in promotion_ids]
        return {str(value) for value in claimed_shop_discount_ids(str(trainer_id), ids)}

    def purchase_discount(self, *, trainer_id: str, promotion_id: str, matchday_number: int) -> dict[str, Any]:
        from storage import purchase_shop_discount

        return purchase_shop_discount(
            user=str(trainer_id),
            discount_id=mappers.as_int(promotion_id, 0),
            jornada=int(matchday_number),
        )

    def recently_exhausted_promotion(self, item_name: str, *, seconds: int = 900) -> dict[str, Any] | None:
        from storage import recently_exhausted_discount

        return recently_exhausted_discount(str(item_name), seconds=int(seconds))

    def add_purchase(
        self,
        *,
        trainer_id: str,
        item_name: str,
        price: int,
        matchday_number: int | None = None,
        promotion_id: str = "",
        base_price: int | None = None,
        notify: bool = True,
    ) -> Purchase:
        from storage import add_purchase, get_purchase

        pid = add_purchase(
            str(trainer_id),
            str(item_name),
            int(price),
            jornada=int(matchday_number) if matchday_number is not None else None,
            discount_id=mappers.as_int(promotion_id, 0) or None,
            base_price=base_price,
            notify=notify,
        )
        row = get_purchase(int(pid))
        return mappers.purchase_from_legacy(row, season_id=self.season_id)

    def list_purchases(self, trainer_id: str | None = None, *, limit: int = 100) -> tuple[Purchase, ...]:
        from storage import list_purchases

        return tuple(
            mappers.purchase_from_legacy(row, season_id=self.season_id)
            for row in list_purchases(trainer_id, limit=int(limit))
        )

    def list_inventory(self, trainer_id: str, *, status: str | None = None, limit: int = 200) -> tuple[Purchase, ...]:
        from storage import list_inventory

        rows = []
        for row in list_inventory(str(trainer_id), status=status, limit=int(limit)):
            values = list(row)
            rows.append(
                {
                    "id": values[0] if len(values) > 0 else "",
                    "user": trainer_id,
                    "item": values[1] if len(values) > 1 else "",
                    "price": values[2] if len(values) > 2 else 0,
                    "created_at": values[3] if len(values) > 3 else 0,
                    "status": values[4] if len(values) > 4 else "pending",
                }
            )
        return tuple(mappers.purchase_from_legacy(row, season_id=self.season_id) for row in rows)

    def list_redemptions(self, trainer_id: str | None = None, *, limit: int = 500) -> tuple[Redemption, ...]:
        from storage import list_redemptions

        return tuple(mappers.redemption_from_legacy(row) for row in list_redemptions(trainer_id, limit=int(limit)))

    def add_redemption(self, redemption: Redemption) -> Redemption:
        from storage import add_redemption

        rid = add_redemption(
            mappers.as_int(redemption.purchase_id, 0),
            redemption.trainer_id,
            redemption.item_name,
            mappers.json_dumps(redemption.payload),
        )
        return Redemption(
            id=str(rid),
            purchase_id=redemption.purchase_id,
            trainer_id=redemption.trainer_id,
            item_id=redemption.item_id,
            item_name=redemption.item_name,
            redeemed_at=redemption.redeemed_at,
            payload=redemption.payload,
        )

    def set_purchase_status(self, purchase_id: str, status: str) -> None:
        from storage import set_purchase_status

        set_purchase_status(mappers.as_int(purchase_id, 0), str(status))
