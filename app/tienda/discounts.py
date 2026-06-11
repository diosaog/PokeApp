from __future__ import annotations

import math
from typing import Any

from app.discord_notify import notify_shop_discounts_created_async
from app.liga.context import current_jornada
from storage import (
    create_shop_discount,
    list_shop_discounts,
    purchase_counts_by_item_for_jornadas,
    settings_get,
    settings_set,
)

DISCOUNT_START_KEY = "shop_discounts:start_jornada"


def _catalog_items(catalog: dict[str, list[dict]]) -> list[dict]:
    out: list[dict] = []
    for items in catalog.values():
        for item in items:
            name = str(item.get("name") or "").strip()
            price = int(item.get("price") or 0)
            if name and price > 1:
                out.append(item)
    return out


def _discount_price(base_price: int, kind: str) -> int:
    floor = max(1, math.ceil(int(base_price) * 0.5))
    if kind == "mega":
        return floor
    step = 2 if int(base_price) >= 6 else 1
    return max(floor, int(base_price) - step)


def _start_jornada(current: int) -> int:
    try:
        raw = settings_get(DISCOUNT_START_KEY)
        if raw not in (None, ""):
            return max(int(raw), 1)
    except Exception:
        pass
    try:
        settings_set(DISCOUNT_START_KEY, str(int(current)))
    except Exception:
        pass
    return int(current)


def ensure_shop_discounts(catalog: dict[str, list[dict]], jornada: int | None = None) -> list[dict[str, Any]]:
    round_no = int(jornada or current_jornada())
    start_round = _start_jornada(round_no)
    if round_no <= start_round:
        return []

    existing = {
        str(discount.get("item") or "")
        for discount in list_shop_discounts(jornada=round_no, active_only=None)
    }
    previous_rounds = [round_no - 1]
    if round_no - 2 >= start_round:
        previous_rounds.append(round_no - 2)
    counts = purchase_counts_by_item_for_jornadas(previous_rounds)

    created: list[dict[str, Any]] = []
    for item in _catalog_items(catalog):
        name = str(item.get("name") or "").strip()
        if not name or name in existing:
            continue

        prev_1_count = int(counts.get(round_no - 1, {}).get(name, 0))
        prev_2_count = int(counts.get(round_no - 2, {}).get(name, 0))
        kind = ""
        if round_no - 2 >= start_round and prev_1_count == 0 and prev_2_count == 0:
            kind = "mega"
        elif prev_1_count == 0:
            kind = "normal"
        if not kind:
            continue

        base_price = int(item.get("price") or 0)
        discount_price = _discount_price(base_price, kind)
        if discount_price >= base_price:
            continue
        discount = create_shop_discount(
            item=name,
            base_price=base_price,
            discount_price=discount_price,
            stock_total=1 if kind == "mega" else 2,
            discount_kind=kind,
            jornada=round_no,
        )
        if discount:
            created.append(discount)
            existing.add(name)

    if created:
        notify_shop_discounts_created_async(jornada=round_no, discounts=created)
    return created


def active_discounts_by_item(jornada: int | None = None) -> dict[str, dict[str, Any]]:
    round_no = int(jornada or current_jornada())
    out: dict[str, dict[str, Any]] = {}
    for discount in list_shop_discounts(jornada=round_no, active_only=True):
        if int(discount.get("stock_used") or 0) >= int(discount.get("stock_total") or 0):
            continue
        item = str(discount.get("item") or "")
        if item:
            out[item] = discount
    return out


def discount_label(kind: str) -> str:
    return "Mega Rebaja" if str(kind) == "mega" else "Rebaja"
