from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.domain.activity import ActivityEvent
from app.domain.league import MatchdaySnapshot
from app.domain.services import activity as activity_domain
from app.domain.services import shop as shop_domain
from app.domain.services import trainers as trainer_domain
from app.domain.shop import Purchase, Redemption, ShopItem, ShopPromotion
from app.domain.team_locks import TeamLock
from app.domain.trainers import Trainer, TrainerFlags, TrainerStatus
from app.repositories import mappers
from app.repositories.errors import ConflictError, NotFoundError


class InMemoryActivityRepository:
    def __init__(self, events: tuple[ActivityEvent, ...] = ()) -> None:
        self.events: list[ActivityEvent] = list(events)

    def append(self, event: ActivityEvent) -> ActivityEvent:
        existing = self.find_by_dedupe_key(event.dedupe_key)
        if existing:
            return existing
        self.events = list(activity_domain.dedupe_events((event, *self.events)))
        return event

    def list_recent(
        self,
        *,
        limit: int = 5,
        viewer: str | None = None,
        event_types: tuple[str, ...] | None = None,
    ) -> tuple[ActivityEvent, ...]:
        allowed = {str(value).lower() for value in event_types or ()}
        out = []
        for event in sorted(self.events, key=lambda item: (item.created_at, item.id), reverse=True):
            if allowed and event.type.value not in allowed and event.type.name.lower() not in allowed:
                continue
            if activity_domain.visible_to(event, viewer).visible:
                out.append(event)
        return tuple(out[: max(0, int(limit))])

    def find_by_dedupe_key(self, dedupe_key: str) -> ActivityEvent | None:
        key = str(dedupe_key or "").strip()
        for event in self.events:
            if event.dedupe_key == key:
                return event
        return None


class InMemoryShopRepository:
    def __init__(
        self,
        *,
        catalog: tuple[ShopItem, ...] = (),
        promotions: tuple[ShopPromotion, ...] = (),
        purchases: tuple[Purchase, ...] = (),
        redemptions: tuple[Redemption, ...] = (),
    ) -> None:
        self.catalog = list(catalog)
        self.promotions = list(promotions)
        self.purchases = list(purchases)
        self.redemptions = list(redemptions)

    def list_catalog(self) -> tuple[ShopItem, ...]:
        return tuple(self.catalog)

    def list_promotions(
        self,
        *,
        matchday_number: int | None = None,
        active_only: bool | None = None,
    ) -> tuple[ShopPromotion, ...]:
        out = []
        for promo in self.promotions:
            if matchday_number is not None and promo.matchday_number != int(matchday_number):
                continue
            if active_only is not None and bool(promo.state.value == "active") != bool(active_only):
                continue
            out.append(promo)
        return tuple(out)

    def get_promotion(self, promotion_id: str) -> ShopPromotion | None:
        target = str(promotion_id)
        for promo in self.promotions:
            if str(promo.id) == target:
                return promo
        return None

    def create_promotion(self, promotion: ShopPromotion) -> ShopPromotion | None:
        self.promotions.append(promotion)
        return promotion

    def purchase_counts_by_matchday(self, matchdays: tuple[int, ...]) -> dict[int, dict[str, int]]:
        out: dict[int, dict[str, int]] = {int(matchday): {} for matchday in matchdays}
        for purchase in self.purchases:
            if purchase.matchday_number in out:
                out[purchase.matchday_number][purchase.item_name] = (
                    out[purchase.matchday_number].get(purchase.item_name, 0) + purchase.quantity
                )
        return out

    def all_purchased_item_names(self) -> set[str]:
        return {purchase.item_name for purchase in self.purchases}

    def claimed_promotion_ids(self, trainer_id: str, promotion_ids: tuple[str, ...]) -> set[str]:
        allowed = {str(value) for value in promotion_ids}
        return {
            purchase.promotion_id
            for purchase in self.purchases
            if purchase.trainer_id == trainer_id and purchase.promotion_id in allowed
        }

    def purchase_discount(self, *, trainer_id: str, promotion_id: str, matchday_number: int) -> dict[str, Any]:
        promotion = self.get_promotion(promotion_id)
        if not promotion:
            return {"purchased": False, "reason": "unavailable", "discount_id": mappers.as_int(promotion_id, 0)}
        claimed = self.claimed_promotion_ids(trainer_id, (promotion_id,))
        decision = shop_domain.evaluate_discount_purchase(
            mappers.promotion_to_legacy_payload(promotion),
            trainer_id=trainer_id,
            promotion_id=mappers.as_int(promotion_id, 0),
            matchday_number=matchday_number,
            now=mappers.iso_to_epoch(promotion.activates_at),
            claimed_discount_ids={mappers.as_int(value, 0) for value in claimed},
        )
        if not decision.allowed:
            return {"purchased": False, "reason": decision.reason, "discount_id": mappers.as_int(promotion_id, 0)}
        purchase = self.add_purchase(
            trainer_id=trainer_id,
            item_name=str(promotion.metadata.get("item_name") or promotion.item_id),
            price=promotion.discount_price,
            matchday_number=matchday_number,
            promotion_id=promotion_id,
            base_price=promotion.base_price,
            notify=False,
        )
        index = self.promotions.index(promotion)
        self.promotions[index] = replace(
            promotion,
            stock_used=min(promotion.stock_total, promotion.stock_used + 1),
        )
        return {
            "purchased": True,
            "reason": "ok",
            "purchase_id": mappers.as_int(purchase.id, 0),
            "discount_id": mappers.as_int(promotion_id, 0),
            "item": purchase.item_name,
            "base_price": promotion.base_price,
            "discount_price": promotion.discount_price,
            "stock_total": promotion.stock_total,
            "stock_used": min(promotion.stock_total, promotion.stock_used + 1),
            "discount_kind": promotion.kind.value,
        }

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
        purchase = Purchase(
            id=str(len(self.purchases) + 1),
            trainer_id=trainer_id,
            item_id=shop_domain.item_key(item_name),
            item_name=item_name,
            quantity=1,
            unit_price=int(price),
            total_price=int(price),
            purchased_at="2026-01-01T00:00:00Z",
            matchday_number=matchday_number,
            promotion_id=promotion_id,
            base_unit_price=base_price,
        )
        self.purchases.append(purchase)
        return purchase

    def list_purchases(self, trainer_id: str | None = None, *, limit: int = 100) -> tuple[Purchase, ...]:
        rows = [p for p in self.purchases if trainer_id is None or p.trainer_id == trainer_id]
        return tuple(rows[-int(limit):])

    def list_redemptions(self, trainer_id: str | None = None, *, limit: int = 500) -> tuple[Redemption, ...]:
        rows = [r for r in self.redemptions if trainer_id is None or r.trainer_id == trainer_id]
        return tuple(rows[-int(limit):])


class InMemoryTrainerRepository:
    def __init__(self, trainers: tuple[Trainer, ...] = (), flags: dict[str, dict[str, Any]] | None = None) -> None:
        self.trainers = list(trainers)
        self.flags = {str(k): dict(v) for k, v in (flags or {}).items()}

    def list_trainers(self) -> tuple[Trainer, ...]:
        return tuple(self.trainers)

    def load_flag_map(self) -> dict[str, dict[str, Any]]:
        return {k: dict(v) for k, v in self.flags.items()}

    def save_flag_map(self, flags: dict[str, dict[str, Any]]) -> None:
        self.flags = {str(k): dict(v) for k, v in flags.items()}

    def get_status(self, trainer_id: str) -> TrainerStatus:
        return trainer_domain.status_from_flags(self.flags.get(trainer_id, {}))

    def set_status(self, trainer_id: str, status: TrainerStatus, *, by_user: str, now: int) -> TrainerStatus:
        current = dict(self.flags.get(trainer_id, {}))
        self.flags[trainer_id] = trainer_domain.apply_status_transition(
            current,
            status,
            by_user=by_user,
            now=now,
        )
        return self.get_status(trainer_id)

    def get_flags(self, trainer_id: str) -> TrainerFlags:
        return mappers.trainer_flags_from_legacy(trainer_id, self.flags.get(trainer_id, {}))

    def set_flags(self, flags: TrainerFlags) -> TrainerFlags:
        self.flags[flags.trainer_id] = mappers.trainer_flags_to_legacy(
            flags,
            previous=self.flags.get(flags.trainer_id, {}),
        )
        return self.get_flags(flags.trainer_id)


class InMemoryTeamLockRepository:
    def __init__(self, locks: tuple[TeamLock, ...] = ()) -> None:
        self.locks = list(locks)

    def get_team_lock(self, *, matchday_number: int, trainer_id: str) -> TeamLock | None:
        for lock in self.locks:
            if lock.matchday_number == int(matchday_number) and lock.trainer_id == trainer_id:
                return lock
        return None

    def list_team_locks(self, *, matchday_number: int) -> tuple[TeamLock, ...]:
        return tuple(lock for lock in self.locks if lock.matchday_number == int(matchday_number))

    def upsert_team_lock(self, lock: TeamLock) -> TeamLock | None:
        self.locks = [
            existing
            for existing in self.locks
            if not (
                existing.matchday_number == lock.matchday_number
                and existing.trainer_id == lock.trainer_id
            )
        ]
        self.locks.append(lock)
        return lock


class InMemoryLeagueRepository:
    def __init__(self, *, state: dict[str, Any] | None = None, snapshots: tuple[MatchdaySnapshot, ...] = ()) -> None:
        self.state = dict(state or {})
        self.snapshots = list(snapshots)

    def load_state(self) -> dict[str, Any]:
        return dict(self.state)

    def save_state(self, state: dict[str, Any]) -> None:
        self.state = dict(state or {})

    def list_matchday_snapshots(self) -> tuple[MatchdaySnapshot, ...]:
        return tuple(sorted(self.snapshots, key=lambda item: item.matchday_number))

    def save_matchday_snapshots(self, snapshots: tuple[MatchdaySnapshot, ...]) -> None:
        self.snapshots = list(snapshots)
