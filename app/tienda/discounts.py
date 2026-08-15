from __future__ import annotations

import json
import random
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.services import shop as shop_domain
from app.discord_notify import notify_shop_discounts_created_async
from app.liga.context import current_jornada
from storage import (
    all_purchased_items,
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
DISCOUNT_BLOCKLIST = shop_domain.DISCOUNT_BLOCKLIST
CATEGORY_RULES = shop_domain.CATEGORY_RULES


def _generation_key(target_round: int) -> str:
    return f"shop_promotions:generated:{int(target_round)}"


def _catalog_items(catalog: dict[str, list[dict]]) -> list[dict[str, Any]]:
    return shop_domain.catalog_items(catalog)


def _item_key(name: Any) -> str:
    return shop_domain.item_key(name)


def _discount_price(base_price: int, kind: str, *, item: str = "") -> int:
    return shop_domain.discount_price(base_price, kind, item=item)


def _mega_allowed(item: dict[str, Any]) -> bool:
    return shop_domain.mega_allowed(item)


def _consecutive_zero_rounds(
    item: str, closed_round: int, counts: dict[int, dict[str, int]]
) -> int:
    return shop_domain.consecutive_zero_rounds(item, closed_round, counts)


def _priority_score(
    item: dict[str, Any],
    *,
    closed_round: int,
    counts: dict[int, dict[str, int]],
    last_seen: dict[str, int],
) -> float:
    return shop_domain.priority_score(
        item,
        closed_round=closed_round,
        counts=counts,
        last_seen=last_seen,
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
    return shop_domain.weighted_pick(
        candidates,
        amount,
        closed_round=closed_round,
        counts=counts,
        last_seen=last_seen,
        rng=rng,
    )


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
    return shop_domain.pick_avoiding_previous(
        candidates,
        amount,
        previous_items=previous_items,
        closed_round=closed_round,
        counts=counts,
        last_seen=last_seen,
        rng=rng,
    )


def select_shop_promotions(
    catalog: dict[str, list[dict]],
    *,
    closed_round: int,
    purchase_counts: dict[int, dict[str, int]],
    discount_history: list[dict[str, Any]],
    purchased_items: set[str] | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    generator = rng or random.SystemRandom()
    return shop_domain.select_shop_promotions(
        catalog,
        closed_round=closed_round,
        purchase_counts=purchase_counts,
        discount_history=discount_history,
        purchased_items=purchased_items,
        rng=generator,
    )


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
    purchased = all_purchased_items()
    history = list_shop_discounts(active_only=None)
    selected = select_shop_promotions(
        catalog,
        closed_round=int(closed_round),
        purchase_counts=counts,
        discount_history=history,
        purchased_items=purchased,
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
    current = int(now if now is not None else time.time())
    return shop_domain.promotion_state(discount, now=current).value


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
