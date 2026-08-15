from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from storage import (
    _LIST_INVENTORY_CACHE,
    _LIST_PURCHASES_CACHE,
    _SHOP_DISCOUNTS_CACHE,
    _TEAM_LOCKS_CACHE,
    _TOTAL_SPENT_CACHE,
    _conn,
    _invalidate_purchase_caches,
    _invalidate_shop_discount_caches,
    _invalidate_team_lock_caches,
    _iso_to_ts,
    _now_iso,
    _sb,
    _supabase_enabled,
)


# Tienda


def _timestamp_iso(value: int | float) -> str:
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()


def _notify_purchase_inserted(user: str, item: str, price: int, purchase_id: int) -> None:
    try:
        from app.discord_notify import notify_purchase_async

        notify_purchase_async(user=user, item=item, price=int(price), purchase_id=int(purchase_id))
    except Exception:
        pass


def _emit_purchase_event(
    *,
    user: str,
    item: str,
    price: int,
    purchase_id: int,
    created_at: int | None = None,
    jornada: int | None = None,
    discount_id: int | None = None,
    base_price: int | None = None,
    discount_kind: str | None = None,
) -> None:
    try:
        from app.activity.events import emit_purchase_completed

        emit_purchase_completed(
            trainer=str(user),
            item=str(item),
            price=int(price),
            purchase_id=int(purchase_id),
            created_at=created_at,
            jornada=jornada,
            discount_id=discount_id,
            base_price=base_price,
            discount_kind=discount_kind,
        )
    except Exception:
        pass


def _emit_team_lock_event(lock: dict[str, Any] | None) -> None:
    if not lock:
        return
    try:
        from app.activity.events import emit_team_locked

        emit_team_locked(
            trainer=str(lock.get("user") or ""),
            jornada=int(lock.get("jornada") or 0),
            lock_id=int(lock.get("id") or 0) if lock.get("id") is not None else None,
            locked_at=int(lock.get("locked_at") or 0) or None,
            is_late=bool(lock.get("is_late")),
            save_id=int(lock.get("save_id") or 0) if lock.get("save_id") is not None else None,
            save_sha256=str(lock.get("save_sha256") or ""),
        )
    except Exception:
        pass


def add_purchase(
    user: str,
    item: str,
    price: int,
    *,
    jornada: int | None = None,
    discount_id: int | None = None,
    base_price: int | None = None,
    notify: bool = True,
) -> int:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            base_payload = {
                "user": user,
                "item": item,
                "price": int(price),
                "created_at": _now_iso(),
                "status": "pending",
                "redeemed_at": None,
            }
            payload = dict(base_payload)
            if jornada is not None:
                payload["jornada"] = int(jornada)
            if discount_id is not None:
                payload["discount_id"] = int(discount_id)
            if base_price is not None:
                payload["base_price"] = int(base_price)
            try:
                res = client.table("purchases").insert(payload).execute()
            except Exception:
                if payload == base_payload:
                    raise
                res = client.table("purchases").insert(base_payload).execute()
            data = res.data or []
            if data:
                pid = int(data[0].get("id") or 0)
                _invalidate_purchase_caches(user)
                _emit_purchase_event(
                    user=user,
                    item=item,
                    price=int(price),
                    purchase_id=pid,
                    created_at=ts,
                    jornada=jornada,
                    discount_id=discount_id,
                    base_price=base_price,
                )
                if notify:
                    _notify_purchase_inserted(user, item, int(price), pid)
                return pid
        except Exception as e:
            # Supabase esta configurado pero fallo: no hacemos fallback silencioso
            raise RuntimeError(f"Supabase add_purchase failed: {e}")
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO purchases(user, item, price, created_at, status, discount_id, base_price, jornada)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                user,
                item,
                int(price),
                ts,
                "pending",
                int(discount_id) if discount_id is not None else None,
                int(base_price) if base_price is not None else None,
                int(jornada) if jornada is not None else None,
            ),
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        _invalidate_purchase_caches(user)
        pid = int(rowid)
        _emit_purchase_event(
            user=user,
            item=item,
            price=int(price),
            purchase_id=pid,
            created_at=ts,
            jornada=jornada,
            discount_id=discount_id,
            base_price=base_price,
        )
        if notify:
            _notify_purchase_inserted(user, item, int(price), pid)
        return pid


def _discount_row_from_mapping(row: dict) -> dict[str, Any]:
    return {
        "id": int(row.get("id") or 0),
        "item": str(row.get("item") or ""),
        "category": str(row.get("category") or ""),
        "base_price": int(row.get("base_price") or 0),
        "discount_price": int(row.get("discount_price") or 0),
        "stock_total": int(row.get("stock_total") or 0),
        "stock_used": int(row.get("stock_used") or 0),
        "discount_kind": str(row.get("discount_kind") or "normal"),
        "jornada": int(row.get("jornada") or 0),
        "active": bool(row.get("active")),
        "created_at": _iso_to_ts(row.get("created_at")),
        "announced_at": _iso_to_ts(row.get("announced_at") or row.get("created_at")),
        "activates_at": _iso_to_ts(row.get("activates_at") or row.get("created_at")),
        "exhausted_at": _iso_to_ts(row.get("exhausted_at")),
    }


def _discount_row_from_tuple(row: tuple) -> dict[str, Any]:
    (
        discount_id,
        item,
        category,
        base_price,
        discount_price,
        stock_total,
        stock_used,
        discount_kind,
        jornada,
        active,
        created_at,
        announced_at,
        activates_at,
        exhausted_at,
    ) = row
    return {
        "id": int(discount_id or 0),
        "item": str(item or ""),
        "category": str(category or ""),
        "base_price": int(base_price or 0),
        "discount_price": int(discount_price or 0),
        "stock_total": int(stock_total or 0),
        "stock_used": int(stock_used or 0),
        "discount_kind": str(discount_kind or "normal"),
        "jornada": int(jornada or 0),
        "active": bool(active),
        "created_at": int(created_at or 0),
        "announced_at": int(announced_at or created_at or 0),
        "activates_at": int(activates_at or created_at or 0),
        "exhausted_at": int(exhausted_at or 0),
    }


def list_shop_discounts(
    *, jornada: int | None = None, active_only: bool | None = None
) -> list[dict[str, Any]]:
    cache_key = (jornada, active_only)
    hit, cached = _SHOP_DISCOUNTS_CACHE.get(cache_key)
    if hit:
        return list(cached)

    if _supabase_enabled():
        try:
            query = _sb().table("shop_discounts").select("*").order("id", desc=True)
            if jornada is not None:
                query = query.eq("jornada", int(jornada))
            if active_only is not None:
                query = query.eq("active", bool(active_only))
            res = query.execute()
            out = [_discount_row_from_mapping(row) for row in (res.data or [])]
            _SHOP_DISCOUNTS_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            return []

    clauses: list[str] = []
    params: list[Any] = []
    if jornada is not None:
        clauses.append("jornada=?")
        params.append(int(jornada))
    if active_only is not None:
        clauses.append("active=?")
        params.append(1 if active_only else 0)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with _conn() as cx:
        rows = cx.execute(
            """
            SELECT id, item, category, base_price, discount_price, stock_total,
                   stock_used, discount_kind, jornada, active, created_at,
                   announced_at, activates_at, exhausted_at
            FROM shop_discounts
            """
            + where
            + " ORDER BY id DESC",
            tuple(params),
        ).fetchall()
    out = [_discount_row_from_tuple(row) for row in rows]
    _SHOP_DISCOUNTS_CACHE.set(cache_key, list(out))
    return out


def create_shop_discount(
    *,
    item: str,
    category: str,
    base_price: int,
    discount_price: int,
    stock_total: int,
    discount_kind: str,
    jornada: int,
    announced_at: int,
    activates_at: int,
) -> dict[str, Any] | None:
    payload = {
        "item": item,
        "category": str(category or ""),
        "base_price": int(base_price),
        "discount_price": int(discount_price),
        "stock_total": int(stock_total),
        "stock_used": 0,
        "discount_kind": str(discount_kind or "normal"),
        "jornada": int(jornada),
        "active": True,
        "created_at": _now_iso(),
        "announced_at": _timestamp_iso(announced_at),
        "activates_at": _timestamp_iso(activates_at),
        "exhausted_at": None,
    }
    if _supabase_enabled():
        try:
            res = _sb().table("shop_discounts").insert(payload).execute()
            data = res.data or []
            _invalidate_shop_discount_caches()
            return _discount_row_from_mapping(data[0]) if data else None
        except Exception:
            return None

    ts = int(time.time())
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO shop_discounts(
                item, category, base_price, discount_price, stock_total, stock_used,
                discount_kind, jornada, active, created_at, announced_at,
                activates_at, exhausted_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item,
                str(category or ""),
                int(base_price),
                int(discount_price),
                int(stock_total),
                0,
                str(discount_kind or "normal"),
                int(jornada),
                1,
                ts,
                int(announced_at),
                int(activates_at),
                None,
            ),
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
    _invalidate_shop_discount_caches()
    return {
        "id": int(rowid),
        "item": item,
        "category": str(category or ""),
        "base_price": int(base_price),
        "discount_price": int(discount_price),
        "stock_total": int(stock_total),
        "stock_used": 0,
        "discount_kind": str(discount_kind or "normal"),
        "jornada": int(jornada),
        "active": True,
        "created_at": ts,
        "announced_at": int(announced_at),
        "activates_at": int(activates_at),
        "exhausted_at": 0,
    }


def purchase_counts_by_item_for_jornadas(jornadas: list[int]) -> dict[int, dict[str, int]]:
    rounds = sorted({int(j) for j in jornadas if int(j) > 0})
    if not rounds:
        return {}
    cache_key = ("purchase_counts", tuple(rounds))
    hit, cached = _SHOP_DISCOUNTS_CACHE.get(cache_key)
    if hit:
        return dict(cached)

    out: dict[int, dict[str, int]] = {j: {} for j in rounds}
    if _supabase_enabled():
        try:
            res = (
                _sb()
                .table("purchases")
                .select("item,jornada")
                .in_("jornada", rounds)
                .execute()
            )
            for row in res.data or []:
                jornada = int(row.get("jornada") or 0)
                item = str(row.get("item") or "")
                if jornada in out and item:
                    out[jornada][item] = out[jornada].get(item, 0) + 1
            _SHOP_DISCOUNTS_CACHE.set(cache_key, dict(out))
            return out
        except Exception:
            return out

    qmarks = ",".join(["?"] * len(rounds))
    with _conn() as cx:
        rows = cx.execute(
            f"SELECT item, jornada FROM purchases WHERE jornada IN ({qmarks})",
            tuple(rounds),
        ).fetchall()
    for item, jornada in rows:
        j = int(jornada or 0)
        item_s = str(item or "")
        if j in out and item_s:
            out[j][item_s] = out[j].get(item_s, 0) + 1
    _SHOP_DISCOUNTS_CACHE.set(cache_key, dict(out))
    return out


def all_purchased_items() -> set[str]:
    cache_key = ("all_purchased_items",)
    hit, cached = _SHOP_DISCOUNTS_CACHE.get(cache_key)
    if hit:
        return set(cached)

    out: set[str] = set()
    if _supabase_enabled():
        try:
            client = _sb()
            chunk_size = 1000
            offset = 0
            while True:
                res = (
                    client.table("purchases")
                    .select("item")
                    .range(offset, offset + chunk_size - 1)
                    .execute()
                )
                rows = res.data or []
                out.update(
                    str(row.get("item") or "").strip()
                    for row in rows
                    if str(row.get("item") or "").strip()
                )
                if len(rows) < chunk_size:
                    break
                offset += chunk_size
            _SHOP_DISCOUNTS_CACHE.set(cache_key, set(out))
            return out
        except Exception:
            return set()

    with _conn() as cx:
        rows = cx.execute(
            "SELECT DISTINCT item FROM purchases WHERE item IS NOT NULL AND item<>''"
        ).fetchall()
    out = {str(row[0] or "").strip() for row in rows if str(row[0] or "").strip()}
    _SHOP_DISCOUNTS_CACHE.set(cache_key, set(out))
    return out


def expire_shop_discounts_through_jornada(jornada: int) -> None:
    round_no = int(jornada)
    if _supabase_enabled():
        try:
            (
                _sb()
                .table("shop_discounts")
                .update({"active": False})
                .eq("active", True)
                .lte("jornada", round_no)
                .execute()
            )
            _invalidate_shop_discount_caches()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase expire_shop_discounts failed: {e}")
    with _conn() as cx:
        cx.execute(
            "UPDATE shop_discounts SET active=0 WHERE active=1 AND jornada<=?",
            (round_no,),
        )
        cx.commit()
    _invalidate_shop_discount_caches()


def claimed_shop_discount_ids(user: str, discount_ids: list[int]) -> set[int]:
    ids = sorted({int(value) for value in discount_ids if int(value) > 0})
    if not user or not ids:
        return set()
    if _supabase_enabled():
        try:
            res = (
                _sb()
                .table("purchases")
                .select("discount_id")
                .eq("user", user)
                .in_("discount_id", ids)
                .execute()
            )
            return {
                int(row.get("discount_id") or 0)
                for row in (res.data or [])
                if int(row.get("discount_id") or 0) > 0
            }
        except Exception:
            return set()
    qmarks = ",".join("?" for _ in ids)
    with _conn() as cx:
        rows = cx.execute(
            f"SELECT DISTINCT discount_id FROM purchases "
            f"WHERE user=? AND discount_id IN ({qmarks})",
            (user, *ids),
        ).fetchall()
    return {int(row[0]) for row in rows if row and row[0] is not None}


def purchase_shop_discount(
    *, user: str, discount_id: int, jornada: int
) -> dict[str, Any]:
    if _supabase_enabled():
        try:
            res = _sb().rpc(
                "rpc_purchase_shop_discount",
                {
                    "p_discount_id": int(discount_id),
                    "p_user": str(user),
                    "p_jornada": int(jornada),
                },
            ).execute()
            data = res.data or []
            row = data[0] if isinstance(data, list) and data else data
            _invalidate_shop_discount_caches()
            _invalidate_purchase_caches(user)
            if isinstance(row, dict):
                out = {
                    "purchased": bool(row.get("purchased")),
                    "reason": str(row.get("reason") or ""),
                    "purchase_id": int(row.get("purchase_id") or 0),
                    "discount_id": int(row.get("discount_id") or discount_id),
                    "item": str(row.get("item") or ""),
                    "base_price": int(row.get("base_price") or 0),
                    "discount_price": int(row.get("discount_price") or 0),
                    "stock_total": int(row.get("stock_total") or 0),
                    "stock_used": int(row.get("stock_used") or 0),
                    "discount_kind": str(row.get("discount_kind") or "normal"),
                }
                if out["purchased"]:
                    _emit_purchase_event(
                        user=str(user),
                        item=str(out.get("item") or ""),
                        price=int(out.get("discount_price") or 0),
                        purchase_id=int(out.get("purchase_id") or 0),
                        created_at=int(time.time()),
                        jornada=int(jornada),
                        discount_id=int(out.get("discount_id") or discount_id),
                        base_price=int(out.get("base_price") or 0),
                        discount_kind=str(out.get("discount_kind") or "normal"),
                    )
                return out
        except Exception as e:
            raise RuntimeError(
                "Supabase no tiene instalada la migracion de promociones: "
                f"{e}"
            )
        return {
            "purchased": False,
            "reason": "unavailable",
            "discount_id": int(discount_id),
        }

    ts = int(time.time())
    with _conn() as cx:
        cx.execute("BEGIN IMMEDIATE")
        row = cx.execute(
            """
            SELECT id, item, category, base_price, discount_price, stock_total,
                   stock_used, discount_kind, jornada, active, created_at,
                   announced_at, activates_at, exhausted_at
            FROM shop_discounts
            WHERE id=?
            """,
            (int(discount_id),),
        ).fetchone()
        if not row:
            cx.commit()
            return {
                "purchased": False,
                "reason": "unavailable",
                "discount_id": int(discount_id),
            }
        discount = _discount_row_from_tuple(row)
        if int(discount.get("jornada") or 0) != int(jornada):
            cx.commit()
            return {"purchased": False, "reason": "expired", **discount}
        if not bool(discount.get("active")):
            cx.commit()
            return {"purchased": False, "reason": "exhausted", **discount}
        if ts < int(discount.get("activates_at") or 0):
            cx.commit()
            return {"purchased": False, "reason": "pending", **discount}
        previous = cx.execute(
            "SELECT id FROM purchases WHERE user=? AND discount_id=? LIMIT 1",
            (str(user), int(discount_id)),
        ).fetchone()
        if previous:
            cx.commit()
            return {"purchased": False, "reason": "already_claimed", **discount}
        if int(discount["stock_used"]) >= int(discount["stock_total"]):
            cx.execute(
                "UPDATE shop_discounts SET active=0 WHERE id=?",
                (int(discount_id),),
            )
            cx.commit()
            _invalidate_shop_discount_caches()
            return {"purchased": False, "reason": "exhausted", **discount}

        next_used = int(discount["stock_used"]) + 1
        exhausted = next_used >= int(discount["stock_total"])
        exhausted_at = ts if exhausted else None
        cx.execute(
            """
            INSERT INTO purchases(
                user, item, price, created_at, status, redeemed_at,
                discount_id, base_price, jornada
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                str(user),
                str(discount["item"]),
                int(discount["discount_price"]),
                ts,
                "pending",
                None,
                int(discount_id),
                int(discount["base_price"]),
                int(jornada),
            ),
        )
        purchase_id = int(cx.execute("SELECT last_insert_rowid()").fetchone()[0])
        cx.execute(
            """
            UPDATE shop_discounts
            SET stock_used=?, active=?, exhausted_at=?
            WHERE id=?
            """,
            (next_used, 0 if exhausted else 1, exhausted_at, int(discount_id)),
        )
        cx.commit()

    _invalidate_shop_discount_caches()
    _invalidate_purchase_caches(user)
    _emit_purchase_event(
        user=str(user),
        item=str(discount["item"]),
        price=int(discount["discount_price"]),
        purchase_id=int(purchase_id),
        created_at=ts,
        jornada=int(jornada),
        discount_id=int(discount_id),
        base_price=int(discount["base_price"]),
        discount_kind=str(discount["discount_kind"]),
    )
    return {
        "purchased": True,
        "reason": "ok",
        "purchase_id": purchase_id,
        "discount_id": int(discount_id),
        "item": str(discount["item"]),
        "base_price": int(discount["base_price"]),
        "discount_price": int(discount["discount_price"]),
        "stock_total": int(discount["stock_total"]),
        "stock_used": next_used,
        "discount_kind": str(discount["discount_kind"]),
    }


def claim_shop_discount(discount_id: int) -> dict[str, Any]:
    if _supabase_enabled():
        try:
            res = _sb().rpc(
                "rpc_claim_shop_discount",
                {"p_discount_id": int(discount_id)},
            ).execute()
            data = res.data or []
            row = data[0] if isinstance(data, list) and data else data
            _invalidate_shop_discount_caches()
            if isinstance(row, dict):
                return {
                    "claimed": bool(row.get("claimed")),
                    "discount_id": int(row.get("discount_id") or 0),
                    "item": str(row.get("item") or ""),
                    "base_price": int(row.get("base_price") or 0),
                    "discount_price": int(row.get("discount_price") or 0),
                    "stock_total": int(row.get("stock_total") or 0),
                    "stock_used": int(row.get("stock_used") or 0),
                    "discount_kind": str(row.get("discount_kind") or "normal"),
                    "exhausted_at": _iso_to_ts(row.get("exhausted_at")),
                }
        except Exception:
            pass
        return {"claimed": False, "discount_id": int(discount_id)}

    ts = int(time.time())
    with _conn() as cx:
        try:
            cx.execute("BEGIN IMMEDIATE")
        except Exception:
            pass
        row = cx.execute(
            """
            SELECT id, item, category, base_price, discount_price, stock_total,
                   stock_used, discount_kind, jornada, active, created_at,
                   announced_at, activates_at, exhausted_at
            FROM shop_discounts
            WHERE id=? AND active=1 AND COALESCE(activates_at, created_at)<=?
            """,
            (int(discount_id), ts),
        ).fetchone()
        if not row:
            cx.commit()
            return {"claimed": False, "discount_id": int(discount_id)}
        discount = _discount_row_from_tuple(row)
        if int(discount["stock_used"]) >= int(discount["stock_total"]):
            cx.commit()
            return {"claimed": False, **discount}
        next_used = int(discount["stock_used"]) + 1
        exhausted_at = ts if next_used >= int(discount["stock_total"]) else int(discount.get("exhausted_at") or 0)
        active = 0 if next_used >= int(discount["stock_total"]) else 1
        cx.execute(
            "UPDATE shop_discounts SET stock_used=?, exhausted_at=?, active=? WHERE id=?",
            (next_used, exhausted_at or None, active, int(discount_id)),
        )
        cx.commit()
    _invalidate_shop_discount_caches()
    discount.update(
        {
            "claimed": True,
            "discount_id": int(discount_id),
            "stock_used": next_used,
            "active": bool(active),
            "exhausted_at": exhausted_at,
        }
    )
    return discount


def recently_exhausted_discount(item: str, *, seconds: int = 900) -> dict[str, Any] | None:
    if _supabase_enabled():
        try:
            res = _sb().rpc("rpc_recently_exhausted_discount", {"p_item": item}).execute()
            data = res.data or []
            row = data[0] if isinstance(data, list) and data else data
            if isinstance(row, dict) and row.get("discount_id"):
                return {
                    "discount_id": int(row.get("discount_id") or 0),
                    "item": str(row.get("item") or ""),
                    "base_price": int(row.get("base_price") or 0),
                    "discount_price": int(row.get("discount_price") or 0),
                    "discount_kind": str(row.get("discount_kind") or "normal"),
                    "exhausted_at": _iso_to_ts(row.get("exhausted_at")),
                    "seconds_since_exhausted": int(row.get("seconds_since_exhausted") or 0),
                }
        except Exception:
            return None
        return None

    threshold = int(time.time()) - int(seconds)
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT id, item, category, base_price, discount_price, stock_total,
                   stock_used, discount_kind, jornada, active, created_at,
                   announced_at, activates_at, exhausted_at
            FROM shop_discounts
            WHERE item=? AND exhausted_at IS NOT NULL AND exhausted_at>=?
            ORDER BY exhausted_at DESC
            LIMIT 1
            """,
            (item, threshold),
        ).fetchone()
    if not row:
        return None
    discount = _discount_row_from_tuple(row)
    discount["discount_id"] = int(discount["id"])
    discount["seconds_since_exhausted"] = max(
        int(time.time()) - int(discount.get("exhausted_at") or 0),
        0,
    )
    return discount


def _team_lock_from_mapping(row: dict) -> dict[str, Any]:
    team = row.get("team_json") or []
    if isinstance(team, str):
        try:
            team = json.loads(team)
        except Exception:
            team = []
    return {
        "id": int(row.get("id") or 0),
        "jornada": int(row.get("jornada") or 0),
        "user": str(row.get("user") or ""),
        "team": list(team) if isinstance(team, list) else [],
        "save_id": row.get("save_id"),
        "save_sha256": row.get("save_sha256"),
        "locked_at": _iso_to_ts(row.get("locked_at")),
        "deadline_at": _iso_to_ts(row.get("deadline_at")),
        "is_late": bool(row.get("is_late")),
    }


def _team_lock_from_tuple(row: tuple) -> dict[str, Any]:
    (
        lock_id,
        jornada,
        user,
        team_json,
        save_id,
        save_sha256,
        locked_at,
        deadline_at,
        is_late,
    ) = row
    try:
        team = json.loads(team_json or "[]")
    except Exception:
        team = []
    return {
        "id": int(lock_id or 0),
        "jornada": int(jornada or 0),
        "user": str(user or ""),
        "team": list(team) if isinstance(team, list) else [],
        "save_id": save_id,
        "save_sha256": save_sha256,
        "locked_at": int(locked_at or 0),
        "deadline_at": int(deadline_at or 0),
        "is_late": bool(is_late),
    }


def get_team_lock(jornada: int, user: str) -> dict[str, Any] | None:
    cache_key = ("team_lock", int(jornada), str(user))
    hit, cached = _TEAM_LOCKS_CACHE.get(cache_key)
    if hit:
        return dict(cached) if cached else None

    if _supabase_enabled():
        try:
            res = (
                _sb()
                .table("team_locks")
                .select("*")
                .eq("jornada", int(jornada))
                .eq("user", user)
                .limit(1)
                .execute()
            )
            data = res.data or []
            lock = _team_lock_from_mapping(data[0]) if data else None
            _TEAM_LOCKS_CACHE.set(cache_key, lock)
            return lock
        except Exception:
            return None

    with _conn() as cx:
        row = cx.execute(
            """
            SELECT id, jornada, user, team_json, save_id, save_sha256, locked_at, deadline_at, is_late
            FROM team_locks
            WHERE jornada=? AND user=?
            LIMIT 1
            """,
            (int(jornada), user),
        ).fetchone()
    lock = _team_lock_from_tuple(row) if row else None
    _TEAM_LOCKS_CACHE.set(cache_key, lock)
    return lock


def list_team_locks(jornada: int) -> list[dict[str, Any]]:
    cache_key = ("team_locks", int(jornada))
    hit, cached = _TEAM_LOCKS_CACHE.get(cache_key)
    if hit:
        return list(cached)

    if _supabase_enabled():
        try:
            res = (
                _sb()
                .table("team_locks")
                .select("*")
                .eq("jornada", int(jornada))
                .execute()
            )
            out = [_team_lock_from_mapping(row) for row in (res.data or [])]
            _TEAM_LOCKS_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            return []

    with _conn() as cx:
        rows = cx.execute(
            """
            SELECT id, jornada, user, team_json, save_id, save_sha256, locked_at, deadline_at, is_late
            FROM team_locks
            WHERE jornada=?
            """,
            (int(jornada),),
        ).fetchall()
    out = [_team_lock_from_tuple(row) for row in rows]
    _TEAM_LOCKS_CACHE.set(cache_key, list(out))
    return out


def upsert_team_lock(
    *,
    jornada: int,
    user: str,
    team: list[dict],
    save_id: int | None = None,
    save_sha256: str | None = None,
    is_late: bool = False,
) -> dict[str, Any] | None:
    deadline_at = "2000-01-01T00:00:00Z" if is_late else None
    if _supabase_enabled():
        try:
            res = _sb().rpc(
                "rpc_upsert_team_lock",
                {
                    "p_jornada": int(jornada),
                    "p_user": user,
                    "p_team_json": team,
                    "p_save_id": int(save_id) if save_id is not None else None,
                    "p_save_sha256": save_sha256,
                    "p_deadline_at": deadline_at,
                },
            ).execute()
            data = res.data
            row = data[0] if isinstance(data, list) and data else data
            _invalidate_team_lock_caches()
            lock = _team_lock_from_mapping(row) if isinstance(row, dict) else None
            _emit_team_lock_event(lock)
            return lock
        except Exception:
            return None

    ts = int(time.time())
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO team_locks(
                jornada, user, team_json, save_id, save_sha256, locked_at, deadline_at, is_late
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(jornada, user) DO UPDATE SET
                team_json=excluded.team_json,
                save_id=excluded.save_id,
                save_sha256=excluded.save_sha256,
                locked_at=excluded.locked_at,
                deadline_at=excluded.deadline_at,
                is_late=excluded.is_late
            """,
            (
                int(jornada),
                user,
                json.dumps(team, ensure_ascii=False, default=str),
                int(save_id) if save_id is not None else None,
                save_sha256,
                ts,
                1 if is_late else None,
                1 if is_late else 0,
            ),
        )
        row = cx.execute(
            """
            SELECT id, jornada, user, team_json, save_id, save_sha256, locked_at, deadline_at, is_late
            FROM team_locks
            WHERE jornada=? AND user=?
            LIMIT 1
            """,
            (int(jornada), user),
        ).fetchone()
        cx.commit()
    _invalidate_team_lock_caches()
    lock = _team_lock_from_tuple(row) if row else None
    _emit_team_lock_event(lock)
    return lock


def total_spent(user: str) -> int:
    if not user:
        return 0
    hit, cached = _TOTAL_SPENT_CACHE.get(user)
    if hit:
        return int(cached)

    if _supabase_enabled():
        try:
            client = _sb()
            # 1) RPC opcional; si falla seguimos sin lanzar excepci?n
            try:
                res = client.rpc("rpc_total_spent", {"p_user": user}).execute()
                if res.data:
                    val = res.data[0] if isinstance(res.data, list) else res.data
                    out = int(val)
                    _TOTAL_SPENT_CACHE.set(user, out)
                    return out
            except Exception:
                pass

            # 2) Suma manual en la tabla purchases
            s = 0
            try:
                res = client.table("purchases").select("price").eq("user", user).execute()
                data = res.data or []
                for row in data:
                    try:
                        s += int(row.get("price") or 0)
                    except Exception:
                        continue
            except Exception:
                s = 0

            # 3) Fallback adicional: inventario si sigue en 0
            if s == 0:
                try:
                    inv = list_inventory(user, limit=300)
                    for r in inv or []:
                        try:
                            s += int(r[2] or 0)
                        except Exception:
                            continue
                except Exception:
                    pass
            out = int(s)
            _TOTAL_SPENT_CACHE.set(user, out)
            return out
        except Exception:
            pass
    with _conn() as cx:
        row = cx.execute("SELECT COALESCE(SUM(price),0) FROM purchases WHERE user=?", (user,)).fetchone()
        out = int(row[0] or 0)
        _TOTAL_SPENT_CACHE.set(user, out)
        return out


def list_purchases(user: str | None = None, limit: int = 100):
    cache_key = (user, int(limit))
    hit, cached = _LIST_PURCHASES_CACHE.get(cache_key)
    if hit:
        return list(cached)
    if _supabase_enabled():
        try:
            client = _sb()
            query = client.table("purchases").select("*").order("id", desc=True).limit(limit)
            if user:
                query = query.eq("user", user)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("user"),
                        row.get("item"),
                        row.get("price"),
                        _iso_to_ts(row.get("created_at")),
                        row.get("status"),
                        _iso_to_ts(row.get("redeemed_at")),
                    )
                )
            _LIST_PURCHASES_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            pass
    with _conn() as cx:
        if user:
            rows = cx.execute(
                "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit)
            ).fetchall()
            _LIST_PURCHASES_CACHE.set(cache_key, list(rows))
            return rows
        rows = cx.execute(
            "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        _LIST_PURCHASES_CACHE.set(cache_key, list(rows))
        return rows


def get_purchase(purchase_id: int):
    if _supabase_enabled():
        try:
            client = _sb()
            res = (
                client.table("purchases")
                .select("*")
                .eq("id", int(purchase_id))
                .limit(1)
                .execute()
            )
            data = res.data or []
            if not data:
                return None
            row = data[0]
            return (
                row.get("id"),
                row.get("user"),
                row.get("item"),
                row.get("price"),
                _iso_to_ts(row.get("created_at")),
                row.get("status"),
                _iso_to_ts(row.get("redeemed_at")),
            )
        except Exception:
            pass
    with _conn() as cx:
        return cx.execute(
            "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases WHERE id=?",
            (int(purchase_id),),
        ).fetchone()


def list_inventory(user: str, *, status: str | None = None, limit: int = 200):
    cache_key = (user, status, int(limit))
    hit, cached = _LIST_INVENTORY_CACHE.get(cache_key)
    if hit:
        return list(cached)
    if _supabase_enabled():
        try:
            client = _sb()
            query = (
                client.table("purchases")
                .select("id,item,price,created_at,status,redeemed_at")
                .eq("user", user)
                .order("id", desc=True)
                .limit(limit)
            )
            if status:
                query = query.eq("status", status)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("item"),
                        row.get("price"),
                        _iso_to_ts(row.get("created_at")),
                        row.get("status"),
                        _iso_to_ts(row.get("redeemed_at")),
                    )
                )
            _LIST_INVENTORY_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            pass
    with _conn() as cx:
        if status:
            rows = cx.execute(
                "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? AND status=? ORDER BY id DESC LIMIT ?",
                (user, status, limit)
            ).fetchall()
            _LIST_INVENTORY_CACHE.set(cache_key, list(rows))
            return rows
        rows = cx.execute(
            "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
            (user, limit)
        ).fetchall()
        _LIST_INVENTORY_CACHE.set(cache_key, list(rows))
        return rows

# Redemptions / vouchers

def add_redemption(purchase_id: int, user: str, item: str, payload_json: str) -> int:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("redemptions").insert(
                {
                    "purchase_id": int(purchase_id),
                    "user": user,
                    "item": item,
                    "payload_json": payload_json,
                    "created_at": _now_iso(),
                }
            ).execute()
            data = res.data or []
            if data:
                return int(data[0].get("id") or 0)
        except Exception as e:
            raise RuntimeError(f"Supabase add_redemption failed: {e}")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO redemptions(purchase_id, user, item, payload_json, created_at) VALUES(?,?,?,?,?)",
            (int(purchase_id), user, item, payload_json, ts)
        )
        rid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        return int(rid)


def list_redemptions(user: str | None = None, limit: int = 500):
    if _supabase_enabled():
        try:
            client = _sb()
            query = (
                client.table("redemptions")
                .select("id,purchase_id,user,item,payload_json,created_at")
                .order("id", desc=True)
                .limit(limit)
            )
            if user:
                query = query.eq("user", user)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("purchase_id"),
                        row.get("user"),
                        row.get("item"),
                        row.get("payload_json"),
                        _iso_to_ts(row.get("created_at")),
                    )
                )
            return out
        except Exception:
            pass
    with _conn() as cx:
        if user:
            return cx.execute(
                "SELECT id, purchase_id, user, item, payload_json, created_at "
                "FROM redemptions WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit),
            ).fetchall()
        return cx.execute(
            "SELECT id, purchase_id, user, item, payload_json, created_at "
            "FROM redemptions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


def set_purchase_status(purchase_id: int, status: str) -> None:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            data = {"status": status}
            if status == "used":
                data["redeemed_at"] = _now_iso()
            client.table("purchases").update(data).eq("id", int(purchase_id)).execute()
            _invalidate_purchase_caches()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase set_purchase_status failed: {e}")
    with _conn() as cx:
        if status == 'used':
            cx.execute("UPDATE purchases SET status=?, redeemed_at=? WHERE id=?", (status, ts, int(purchase_id)))
        else:
            cx.execute("UPDATE purchases SET status=? WHERE id=?", (status, int(purchase_id)))
        cx.commit()
    _invalidate_purchase_caches()
