from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.discord_notify import notify_shop_discounts_created_async
from app.liga.context import current_jornada
from storage import (
    create_shop_discount,
    list_shop_discounts,
    purchase_counts_by_item_for_jornadas,
    settings_get,
    settings_set,
)

PROMOTION_DELAY_SECONDS = 24 * 60 * 60
MADRID_TZ = ZoneInfo("Europe/Madrid")
GOLD_BOTTLE_CAP = "Chapa Dorada"
EVOLUTION_ITEM = "Objeto Evolutivo"

CATEGORY_RULES: dict[str, dict[str, int]] = {
    "comodines": {"normal": 1, "mega": 1},
    "competitivos": {"normal": 4, "mega": 2},
    "crianza": {"normal": 1, "mega": 1},
}


def _generation_key(target_round: int) -> str:
    return f"shop_promotions:generated:{int(target_round)}"


def _catalog_items(catalog: dict[str, list[dict]]) -> list[dict[str, Any]]:
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


def _discount_price(base_price: int, kind: str, *, item: str = "") -> int:
    price = int(base_price)
    if item == GOLD_BOTTLE_CAP:
        return 10 if kind == "mega" else 13
    if kind == "mega":
        if price == 12:
            return 8
        return max(1, math.ceil(price * 0.5))
    step = 2 if price >= 6 else 1
    return max(1, price - step)


def _mega_allowed(item: dict[str, Any]) -> bool:
    name = str(item.get("name") or "")
    price = int(item.get("price") or 0)
    return price > 4 and name != EVOLUTION_ITEM


def _consecutive_zero_rounds(
    item: str, closed_round: int, counts: dict[int, dict[str, int]]
) -> int:
    streak = 0
    for round_no in range(int(closed_round), 0, -1):
        if int(counts.get(round_no, {}).get(item, 0)) > 0:
            break
        streak += 1
    return streak


def _priority_score(
    item: dict[str, Any],
    *,
    closed_round: int,
    counts: dict[int, dict[str, int]],
    last_seen: dict[str, int],
) -> float:
    name = str(item.get("name") or "")
    streak = _consecutive_zero_rounds(name, closed_round, counts)
    total_purchases = sum(
        int(round_counts.get(name, 0)) for round_counts in counts.values()
    )
    seen_round = int(last_seen.get(name, 0))
    rounds_since_offer = max(int(closed_round) + 1 - seen_round, 1)
    return (
        float(streak * 4)
        + float(rounds_since_offer * 2)
        + float(max(4 - total_purchases, 0))
    )


def _weighted_pick(
    candidates: list[dict[str, Any]],
    amount: int,
    *,
    closed_round: int,
    counts: dict[int, dict[str, int]],
    last_seen: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    pool = list(candidates)
    selected: list[dict[str, Any]] = []
    while pool and len(selected) < int(amount):
        priorities = [
            _priority_score(
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


def _pick_avoiding_previous(
    candidates: list[dict[str, Any]],
    amount: int,
    *,
    previous_items: set[str],
    closed_round: int,
    counts: dict[int, dict[str, int]],
    last_seen: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    fresh = [
        item for item in candidates if str(item.get("name") or "") not in previous_items
    ]
    selected = _weighted_pick(
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
    repeats = [
        item
        for item in candidates
        if str(item.get("name") or "") not in selected_names
    ]
    selected.extend(
        _weighted_pick(
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
    catalog: dict[str, list[dict]],
    *,
    closed_round: int,
    purchase_counts: dict[int, dict[str, int]],
    discount_history: list[dict[str, Any]],
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    generator = rng or random.SystemRandom()
    items = _catalog_items(catalog)
    item_category = {
        str(item.get("name") or ""): str(item.get("category") or "")
        for item in items
    }
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
            item for item in items if item_category.get(str(item.get("name") or "")) == category
        ]
        normal_candidates = [
            item
            for item in category_items
            if int(
                purchase_counts.get(int(closed_round), {}).get(
                    str(item.get("name") or ""), 0
                )
            )
            == 0
        ]
        mega_candidates = [
            item
            for item in normal_candidates
            if int(closed_round) >= 2
            and int(
                purchase_counts.get(int(closed_round) - 1, {}).get(
                    str(item.get("name") or ""), 0
                )
            )
            == 0
            and _mega_allowed(item)
        ]

        mega = _pick_avoiding_previous(
            mega_candidates,
            int(quotas["mega"]),
            previous_items=previous_items,
            closed_round=closed_round,
            counts=purchase_counts,
            last_seen=last_seen,
            rng=generator,
        )
        for item in mega:
            name = str(item.get("name") or "")
            selected.append({**item, "discount_kind": "mega"})
            used_names.add(name)

        normal_pool = [
            item
            for item in normal_candidates
            if str(item.get("name") or "") not in used_names
        ]
        normal = _pick_avoiding_previous(
            normal_pool,
            int(quotas["normal"]),
            previous_items=previous_items,
            closed_round=closed_round,
            counts=purchase_counts,
            last_seen=last_seen,
            rng=generator,
        )
        for item in normal:
            name = str(item.get("name") or "")
            selected.append({**item, "discount_kind": "normal"})
            used_names.add(name)
    return selected


def schedule_shop_promotions(
    catalog: dict[str, list[dict]], *, closed_round: int
) -> list[dict[str, Any]]:
    target_round = int(closed_round) + 1
    marker_key = _generation_key(target_round)
    if settings_get(marker_key):
        return list_shop_discounts(jornada=target_round, active_only=None)

    existing = list_shop_discounts(jornada=target_round, active_only=None)
    if existing:
        settings_set(marker_key, json.dumps({"existing": True, "count": len(existing)}))
        return existing

    rounds = list(range(1, int(closed_round) + 1))
    counts = purchase_counts_by_item_for_jornadas(rounds)
    history = list_shop_discounts(active_only=None)
    selected = select_shop_promotions(
        catalog,
        closed_round=int(closed_round),
        purchase_counts=counts,
        discount_history=history,
    )
    announced_at = int(time.time())
    activates_at = announced_at + PROMOTION_DELAY_SECONDS
    created: list[dict[str, Any]] = []
    for item in selected:
        name = str(item.get("name") or "")
        kind = str(item.get("discount_kind") or "normal")
        base_price = int(item.get("price") or 0)
        discount_price = _discount_price(base_price, kind, item=name)
        if discount_price >= base_price:
            continue
        discount = create_shop_discount(
            item=name,
            category=str(item.get("category") or ""),
            base_price=base_price,
            discount_price=discount_price,
            stock_total=1 if kind == "mega" else 2,
            discount_kind=kind,
            jornada=target_round,
            announced_at=announced_at,
            activates_at=activates_at,
        )
        if not discount:
            raise RuntimeError(
                "No se pudieron guardar las promociones. Revisa la migracion de Supabase."
            )
        created.append(discount)

    settings_set(
        marker_key,
        json.dumps(
            {
                "closed_round": int(closed_round),
                "target_round": target_round,
                "announced_at": announced_at,
                "activates_at": activates_at,
                "count": len(created),
            },
            ensure_ascii=True,
        ),
    )
    if created:
        notify_shop_discounts_created_async(
            jornada=target_round,
            discounts=created,
            activates_at=activates_at,
        )
    return created


def promotion_state(discount: dict[str, Any], *, now: int | None = None) -> str:
    if not bool(discount.get("active")):
        return "ended"
    if int(discount.get("stock_used") or 0) >= int(discount.get("stock_total") or 0):
        return "ended"
    current = int(now if now is not None else time.time())
    if current < int(discount.get("activates_at") or 0):
        return "pending"
    return "active"


def promotion_opens_label(discount: dict[str, Any]) -> str:
    timestamp = int(discount.get("activates_at") or 0)
    if timestamp <= 0:
        return "Proximamente"
    return datetime.fromtimestamp(timestamp, tz=MADRID_TZ).strftime(
        "%d/%m/%Y a las %H:%M"
    )


def shop_promotions_by_item(jornada: int | None = None) -> dict[str, dict[str, Any]]:
    round_no = int(jornada or current_jornada())
    out: dict[str, dict[str, Any]] = {}
    for discount in list_shop_discounts(jornada=round_no, active_only=True):
        state = promotion_state(discount)
        if state == "ended":
            continue
        item = str(discount.get("item") or "")
        if item:
            out[item] = {**discount, "promotion_state": state}
    return out


def active_discounts_by_item(jornada: int | None = None) -> dict[str, dict[str, Any]]:
    return {
        item: discount
        for item, discount in shop_promotions_by_item(jornada).items()
        if discount.get("promotion_state") == "active"
    }


def discount_label(kind: str) -> str:
    return "Mega Rebaja" if str(kind) == "mega" else "Rebaja"
