from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from app.common import COIN
from app.liga.context import current_jornada
from app.tienda.discounts import (
    discount_label,
    promotion_opens_label,
    promotion_state,
    shop_promotions_by_item,
)
from app.tienda.money import _money_available
from storage import (
    get_current_save_for_user,
    get_team_lock,
    list_purchases,
    list_saves,
    list_team_locks,
    settings_get,
)


MAX_VISIBLE_NOTIFICATIONS = 5


def _cache_data(ttl: int = 20):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


def _fmt_ts(value: Any) -> str:
    try:
        ts = int(value or 0)
        if ts <= 0:
            return "-"
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "-"


@_cache_data(ttl=10)
def league_state_snapshot() -> dict[str, Any]:
    try:
        raw = settings_get("league_state")
        data = json.loads(raw or "{}")
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    divisions = data.get("divisions") if isinstance(data, dict) else {}
    if not isinstance(divisions, dict):
        divisions = {}
    try:
        tramo = max(int(data.get("tramo") or 1), 1)
    except Exception:
        tramo = 1
    return {
        "tramo": tramo,
        "active": bool(data.get("active")),
        "division_a": list(divisions.get("A") or []),
        "division_b": list(divisions.get("B") or []),
    }


@_cache_data(ttl=15)
def save_snapshot(user: str | None) -> dict[str, str]:
    if not user:
        return {"title": "Sin entrenador", "detail": "-"}
    try:
        cur = get_current_save_for_user(str(user))
    except Exception:
        cur = None
    if not cur:
        return {"title": "Sin save actual", "detail": "Sube un save"}
    original = str(cur[2] or cur[1] or "Save actual")
    return {"title": original, "detail": _fmt_ts(cur[5] if len(cur) > 5 else 0)}


@_cache_data(ttl=10)
def team_lock_snapshot(user: str | None, jornada: int) -> dict[str, str]:
    if not user:
        return {"title": "Sin fijar", "detail": "-"}
    try:
        lock = get_team_lock(int(jornada), str(user))
    except Exception:
        lock = None
    if not lock or not lock.get("team"):
        return {"title": "Sin fijar", "detail": f"Jornada {int(jornada)}"}
    total = len(lock.get("team") or [])
    suffix = " tarde" if lock.get("is_late") else ""
    return {
        "title": f"Fijado{suffix}",
        "detail": f"{total}/6 Pokemon - {_fmt_ts(lock.get('locked_at'))}",
    }


@_cache_data(ttl=10)
def money_snapshot(user: str | None) -> dict[str, str]:
    if not user:
        return {"title": f"{COIN} 0", "detail": "-"}
    try:
        coins = int(_money_available(str(user)))
    except Exception:
        coins = 0
    return {"title": f"{COIN} {coins}", "detail": "Monedas disponibles"}


@_cache_data(ttl=15)
def promo_snapshot(jornada: int) -> dict[str, Any]:
    try:
        promos = list(shop_promotions_by_item(int(jornada)).values())
    except Exception:
        promos = []
    active = [p for p in promos if promotion_state(p) == "active"]
    pending = [p for p in promos if promotion_state(p) == "pending"]
    sample = active[:3] or pending[:3]
    return {
        "active": len(active),
        "pending": len(pending),
        "sample": [
            {
                "item": str(p.get("item") or ""),
                "kind": discount_label(str(p.get("discount_kind") or "normal")),
                "opens": promotion_opens_label(p),
            }
            for p in sample
        ],
    }


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _activity_item(
    *,
    source: str,
    title: str,
    body: str,
    timestamp: Any,
) -> dict[str, str]:
    ts = _safe_int(timestamp)
    return {
        "kind": "info",
        "source": source,
        "title": title,
        "body": body,
        "time": _fmt_ts(ts),
        "ts": str(ts),
    }


def _team_lock_activity(round_no: int) -> list[dict[str, str]]:
    try:
        locks = list_team_locks(int(round_no))
    except Exception:
        locks = []
    items: list[dict[str, str]] = []
    for lock in locks:
        team = list(lock.get("team") or [])
        if not team:
            continue
        user = str(lock.get("user") or "Entrenador").strip() or "Entrenador"
        late = " tarde" if lock.get("is_late") else ""
        items.append(
            _activity_item(
                source=f"lock:{round_no}:{user}",
                title="Equipo fijado",
                body=f"{user} ha fijado equipo{late}.",
                timestamp=lock.get("locked_at"),
            )
        )
    return items


def _purchase_activity(limit: int) -> list[dict[str, str]]:
    try:
        purchases = list_purchases(limit=max(int(limit) * 6, 20))
    except Exception:
        purchases = []
    items: list[dict[str, str]] = []
    for row in purchases:
        if len(row) >= 7:
            pid, user, item, price, ts, _status, _redeemed_at = row[:7]
        elif len(row) >= 5:
            pid, user, item, price, ts = row[:5]
        else:
            continue
        price_i = _safe_int(price)
        if price_i <= 0:
            continue
        buyer = str(user or "Entrenador").strip() or "Entrenador"
        item_name = str(item or "objeto").strip() or "objeto"
        items.append(
            _activity_item(
                source=f"purchase:{pid}",
                title="Compra",
                body=f"{buyer} ha comprado {item_name}.",
                timestamp=ts,
            )
        )
    return items


def _save_activity(limit: int) -> list[dict[str, str]]:
    try:
        saves = list_saves(limit=max(int(limit) * 6, 20))
    except Exception:
        saves = []
    items: list[dict[str, str]] = []
    for row in saves:
        if len(row) < 6:
            continue
        save_id, filename, original_name, _sha256, uploader, ts = row[:6]
        trainer = str(uploader or "Entrenador").strip() or "Entrenador"
        save_name = str(original_name or filename or "save").strip() or "save"
        items.append(
            _activity_item(
                source=f"save:{save_id}",
                title="Save subido",
                body=f"{trainer} ha subido {save_name}.",
                timestamp=ts,
            )
        )
    return items


def collect_notifications(
    *,
    user: str | None = None,
    jornada: int | None = None,
    limit: int = MAX_VISIBLE_NOTIFICATIONS,
) -> list[dict[str, str]]:
    _ = user
    round_no = int(jornada or current_jornada())
    cap = max(1, int(limit or MAX_VISIBLE_NOTIFICATIONS))
    items = [
        *_team_lock_activity(round_no),
        *_purchase_activity(cap),
        *_save_activity(cap),
    ]
    items.sort(
        key=lambda item: (_safe_int(item.get("ts")), str(item.get("source") or "")),
        reverse=True,
    )
    visible = items[:cap]
    if visible:
        return visible
    return [
        {
            "kind": "ok",
            "source": "empty",
            "title": "Sin actividad reciente",
            "body": "Cuando se fijen equipos, se compre o se suba un save, aparecera aqui.",
            "time": "",
            "ts": "0",
        }
    ]


def notification_count(items: list[dict[str, str]]) -> int:
    return sum(1 for item in items if item.get("kind") in {"danger", "warn", "info"})


def render_notification_styles(container: Any = None) -> None:
    target = container or st
    target.markdown(
        """
        <style>
        .app-notice {
          padding: 11px 12px;
          margin-bottom: 8px;
          border: 1px solid rgba(248,251,255,0.22);
          border-radius: var(--poke-radius);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.08), transparent 62%),
            linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.14), 0 6px 14px rgba(2,18,46,0.18);
        }
        .app-notice-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .app-notice-body {
          margin-top: 5px;
          color: var(--bw2-text-soft);
          font-size: 18px;
          line-height: 1.08;
        }
        .app-notice-time {
          margin-top: 7px;
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 8px;
          text-transform: uppercase;
        }
        .app-notice--danger { border-left: 4px solid #ef5e68; }
        .app-notice--warn { border-left: 4px solid #efc257; }
        .app-notice--ok { border-left: 4px solid #58d18e; }
        .app-notice--info { border-left: 4px solid #6ea8ff; }
        section[data-testid="stSidebar"] .stPopover button {
          width: 100%;
          min-height: 42px;
          justify-content: flex-start;
          border-color: rgba(248,251,255,0.24);
          border-radius: var(--poke-radius);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.09), transparent 62%),
            linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
          color: #fff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def notice_html(item: dict[str, str]) -> str:
    kind = escape(str(item.get("kind") or "info"))
    time_text = str(item.get("time") or "").strip()
    time_html = (
        f"<div class='app-notice-time'>{escape(time_text)}</div>"
        if time_text and time_text != "-"
        else ""
    )
    return (
        f"<div class='app-notice app-notice--{kind}'>"
        f"<div class='app-notice-title'>{escape(str(item.get('title') or 'Aviso'))}</div>"
        f"<div class='app-notice-body'>{escape(str(item.get('body') or ''))}</div>"
        f"{time_html}"
        "</div>"
    )


def render_notifications_popover(
    items: list[dict[str, str]],
    *,
    container: Any = None,
    label: str = "Notificaciones",
    use_container_width: bool = True,
) -> None:
    target = container or st
    render_notification_styles(target)
    pending = notification_count(items)
    title = f"{label} ({pending})" if pending else label
    if hasattr(target, "popover"):
        with target.popover(title, use_container_width=use_container_width):
            for item in items:
                st.markdown(notice_html(item), unsafe_allow_html=True)
    else:
        with target.expander(title, expanded=False):
            for item in items:
                st.markdown(notice_html(item), unsafe_allow_html=True)
