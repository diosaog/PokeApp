from __future__ import annotations
import time
from typing import Optional, List, Tuple
from storage_core import _supabase_enabled, _sb, _now_iso, _conn, _iso_to_ts

def add_purchase(user: str, item: str, price: int) -> int:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("purchases").insert(
                {
                    "user": user,
                    "item": item,
                    "price": int(price),
                    "created_at": _now_iso(),
                    "status": "pending",
                    "redeemed_at": None,
                }
            ).execute()
            data = res.data or []
            if data:
                return int(data[0].get("id") or 0)
        except Exception as e:
            # Supabase está configurado pero falló: no hacemos fallback silencioso
            raise RuntimeError(f"Supabase add_purchase failed: {e}")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO purchases(user, item, price, created_at, status) VALUES(?,?,?,?,?)",
            (user, item, int(price), ts, 'pending')
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        return int(rowid)


def total_spent(user: str) -> int:
    if _supabase_enabled():
        try:
            client = _sb()
            # 1) RPC opcional; si falla seguimos sin lanzar excepci?n
            try:
                res = client.rpc("rpc_total_spent", {"p_user": user}).execute()
                if res.data:
                    val = res.data[0] if isinstance(res.data, list) else res.data
                    return int(val)
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
            return s
        except Exception:
            pass
    with _conn() as cx:
        row = cx.execute("SELECT COALESCE(SUM(price),0) FROM purchases WHERE user=?", (user,)).fetchone()
        return int(row[0] or 0)


def list_purchases(user: str | None = None, limit: int = 100):
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
            return out
        except Exception:
            pass
    with _conn() as cx:
        if user:
            return cx.execute(
                "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit)
            ).fetchall()
        return cx.execute(
            "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()


def list_inventory(user: str, *, status: str | None = None, limit: int = 200):
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
            return out
        except Exception:
            pass
    with _conn() as cx:
        if status:
            return cx.execute(
                "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? AND status=? ORDER BY id DESC LIMIT ?",
                (user, status, limit)
            ).fetchall()
        return cx.execute(
            "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
            (user, limit)
        ).fetchall()

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


def set_purchase_status(purchase_id: int, status: str) -> None:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            data = {"status": status}
            if status == "used":
                data["redeemed_at"] = _now_iso()
            client.table("purchases").update(data).eq("id", int(purchase_id)).execute()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase set_purchase_status failed: {e}")
    with _conn() as cx:
        if status == 'used':
            cx.execute("UPDATE purchases SET status=?, redeemed_at=? WHERE id=?", (status, ts, int(purchase_id)))
        else:
            cx.execute("UPDATE purchases SET status=? WHERE id=?", (status, int(purchase_id)))
        cx.commit()

# Pokemon flags
