from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any, Mapping

from app.domain.shop import PromotionState


GOLD_BOTTLE_CAP = "Chapa Dorada"
EVOLUTION_ITEM = "Objeto Evolutivo"
DISCOUNT_BLOCKLIST = {GOLD_BOTTLE_CAP}
CATEGORY_RULES: dict[str, dict[str, int]] = {
    "comodines": {"normal": 1, "mega": 1},
    "competitivos": {"normal": 4, "mega": 2},
    "crianza": {"normal": 1, "mega": 1},
}


@dataclass(frozen=True)
class PurchaseDecision:
    allowed: bool
    reason: str
    effective_price: int = 0
    total_price: int = 0
    base_price: int = 0
    promotion_id: int = 0
    stock_used_after: int = 0
    stock_exhausted: bool = False


def item_key(name: Any) -> str:
    return str(name or "").strip().casefold()


def catalog_items(catalog: Mapping[str, list[dict]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for category, items in catalog.items():
        if category not in CATEGORY_RULES:
            continue
        for item in items:
            name = str(item.get("name") or "").strip()
            price = int(item.get("price") or 0)
            if name and price > 1:
                out.append({**item, "category": category})
    return out


def discount_price(base_price: int, kind: str, *, item: str = "") -> int:
    price = int(base_price)
    if item in DISCOUNT_BLOCKLIST:
        return price
    if kind == "mega":
        if price == 12:
            return 8
        return max(1, math.ceil(price * 0.5))
    step = 2 if price >= 6 else 1
    return max(1, price - step)


def mega_allowed(item: Mapping[str, Any]) -> bool:
    name = str(item.get("name") or "")
    price = int(item.get("price") or 0)
    return price > 4 and name != EVOLUTION_ITEM


def consecutive_zero_rounds(
    item: str,
    closed_round: int,
    counts: Mapping[int, Mapping[str, int]],
) -> int:
    streak = 0
    for round_no in range(int(closed_round), 0, -1):
        if int(counts.get(round_no, {}).get(item, 0)) > 0:
            break
        streak += 1
    return streak


def priority_score(
    item: Mapping[str, Any],
    *,
    closed_round: int,
    counts: Mapping[int, Mapping[str, int]],
    last_seen: Mapping[str, int],
) -> float:
    name = str(item.get("name") or "")
    streak = consecutive_zero_rounds(name, closed_round, counts)
    total_purchases = sum(int(round_counts.get(name, 0)) for round_counts in counts.values())
    seen_round = int(last_seen.get(name, 0))
    rounds_since_offer = max(int(closed_round) + 1 - seen_round, 1)
    return float(streak * 4) + float(rounds_since_offer * 2) + float(max(4 - total_purchases, 0))


def weighted_pick(
    candidates: list[dict[str, Any]],
    amount: int,
    *,
    closed_round: int,
    counts: Mapping[int, Mapping[str, int]],
    last_seen: Mapping[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    pool = list(candidates)
    selected: list[dict[str, Any]] = []
    while pool and len(selected) < int(amount):
        priorities = [
            priority_score(
                item,
                closed_round=closed_round,
                counts=counts,
                last_seen=last_seen,
            )
            for item in pool
        ]
        low = min(priorities)
        high = max(priorities)
        spread = max(high - low, 1.0)
        scores = [
            0.70 * ((priority - low) / spread) + 0.30 * rng.random()
            for priority in priorities
        ]
        index = max(range(len(pool)), key=lambda idx: scores[idx])
        selected.append(pool.pop(index))
    return selected


def pick_avoiding_previous(
    candidates: list[dict[str, Any]],
    amount: int,
    *,
    previous_items: set[str],
    closed_round: int,
    counts: Mapping[int, Mapping[str, int]],
    last_seen: Mapping[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    fresh = [item for item in candidates if str(item.get("name") or "") not in previous_items]
    selected = weighted_pick(
        fresh,
        amount,
        closed_round=closed_round,
        counts=counts,
        last_seen=last_seen,
        rng=rng,
    )
    remaining = int(amount) - len(selected)
    if remaining <= 0:
        return selected
    selected_names = {str(item.get("name") or "") for item in selected}
    repeats = [item for item in candidates if str(item.get("name") or "") not in selected_names]
    selected.extend(
        weighted_pick(
            repeats,
            remaining,
            closed_round=closed_round,
            counts=counts,
            last_seen=last_seen,
            rng=rng,
        )
    )
    return selected


def select_shop_promotions(
    catalog: Mapping[str, list[dict]],
    *,
    closed_round: int,
    purchase_counts: Mapping[int, Mapping[str, int]],
    discount_history: list[dict[str, Any]],
    purchased_items: set[str] | None = None,
    rng: random.Random,
) -> list[dict[str, Any]]:
    purchased_names = {item_key(item) for item in (purchased_items or set())}
    items = catalog_items(catalog)
    item_category = {str(item.get("name") or ""): str(item.get("category") or "") for item in items}
    last_seen: dict[str, int] = {}
    previous_items: set[str] = set()
    for discount in discount_history:
        name = str(discount.get("item") or "")
        round_no = int(discount.get("jornada") or 0)
        if not name:
            continue
        last_seen[name] = max(last_seen.get(name, 0), round_no)
        if round_no == int(closed_round):
            previous_items.add(name)

    selected: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for category, quotas in CATEGORY_RULES.items():
        category_items = [
            item
            for item in items
            if item_category.get(str(item.get("name") or "")) == category
            and item_key(item.get("name")) not in purchased_names
            and str(item.get("name") or "") not in DISCOUNT_BLOCKLIST
        ]
        normal_candidates = [
            item
            for item in category_items
            if int(purchase_counts.get(int(closed_round), {}).get(str(item.get("name") or ""), 0)) == 0
        ]
        mega_candidates = [
            item
            for item in normal_candidates
            if int(closed_round) >= 2
            and int(purchase_counts.get(int(closed_round) - 1, {}).get(str(item.get("name") or ""), 0)) == 0
            and mega_allowed(item)
        ]

        mega = pick_avoiding_previous(
            mega_candidates,
            int(quotas["mega"]),
            previous_items=previous_items,
            closed_round=closed_round,
            counts=purchase_counts,
            last_seen=last_seen,
            rng=rng,
        )
        for item in mega:
            name = str(item.get("name") or "")
            selected.append({**item, "discount_kind": "mega"})
            used_names.add(name)

        normal_pool = [item for item in normal_candidates if str(item.get("name") or "") not in used_names]
        normal = pick_avoiding_previous(
            normal_pool,
            int(quotas["normal"]),
            previous_items=previous_items,
            closed_round=closed_round,
            counts=purchase_counts,
            last_seen=last_seen,
            rng=rng,
        )
        for item in normal:
            name = str(item.get("name") or "")
            selected.append({**item, "discount_kind": "normal"})
            used_names.add(name)
    return selected


def promotion_state(discount: Mapping[str, Any], *, now: int) -> PromotionState:
    if not bool(discount.get("active")):
        return PromotionState.ENDED
    if int(discount.get("stock_used") or 0) >= int(discount.get("stock_total") or 0):
        return PromotionState.ENDED
    if int(now) < int(discount.get("activates_at") or 0):
        return PromotionState.PENDING
    return PromotionState.ACTIVE


def evaluate_discount_purchase(
    discount: Mapping[str, Any] | None,
    *,
    trainer_id: str,
    promotion_id: int,
    matchday_number: int,
    now: int,
    claimed_discount_ids: set[int] | None = None,
) -> PurchaseDecision:
    if not discount:
        return PurchaseDecision(allowed=False, reason="unavailable", promotion_id=int(promotion_id))
    promo_id = int(discount.get("id") or promotion_id)
    if int(discount.get("jornada") or 0) != int(matchday_number):
        return PurchaseDecision(allowed=False, reason="expired", promotion_id=promo_id)
    if not bool(discount.get("active")):
        return PurchaseDecision(allowed=False, reason="exhausted", promotion_id=promo_id)
    if int(now) < int(discount.get("activates_at") or 0):
        return PurchaseDecision(allowed=False, reason="pending", promotion_id=promo_id)
    if promo_id in set(claimed_discount_ids or set()):
        return PurchaseDecision(allowed=False, reason="already_claimed", promotion_id=promo_id)

    stock_used_after = int(discount.get("stock_used") or 0) + 1
    stock_total = int(discount.get("stock_total") or 0)
    if stock_used_after > stock_total:
        return PurchaseDecision(allowed=False, reason="exhausted", promotion_id=promo_id)
    price = int(discount.get("discount_price") or 0)
    _ = trainer_id
    return PurchaseDecision(
        allowed=True,
        reason="ok",
        effective_price=price,
        total_price=price,
        base_price=int(discount.get("base_price") or 0),
        promotion_id=promo_id,
        stock_used_after=stock_used_after,
        stock_exhausted=stock_used_after >= stock_total,
    )
