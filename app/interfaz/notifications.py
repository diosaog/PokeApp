from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from app.common import COIN
from app.entrenadores.trainer_flags import is_trainer_retired
from app.liga.context import current_jornada
from app.tienda.discounts import (
    discount_label,
    promotion_opens_label,
    promotion_state,
    shop_promotions_by_item,
)
from app.tienda.money import _money_available
from storage import get_current_save_for_user, get_team_lock, list_team_locks, settings_get
from utils import active_users


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


@_cache_data(ttl=10)
def team_lock_counts(jornada: int) -> tuple[int, int]:
    users = list(active_users().keys())
    try:
        locks = list_team_locks(int(jornada))
    except Exception:
        locks = []
    locked = {
        str(lock.get("user") or "")
        for lock in locks
        if lock.get("team")
    }
    return len(locked & set(users)), len(users)


def collect_notifications(
    *,
    user: str | None = None,
    jornada: int | None = None,
    lock: dict[str, str] | None = None,
    save: dict[str, str] | None = None,
    promos: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    current_user = str(user or st.session_state.get("user") or "").strip()
    round_no = int(jornada or current_jornada())
    lock = lock or team_lock_snapshot(current_user, round_no)
    save = save or save_snapshot(current_user)
    promos = promos or promo_snapshot(round_no)

    items: list[dict[str, str]] = []
    if current_user and is_trainer_retired(current_user):
        items.append(
            {
                "kind": "warn",
                "title": "Modo espectador",
                "body": "Puedes cotillear, pero no usar sistemas activos.",
            }
        )
    if lock["title"].startswith("Sin fijar"):
        items.append(
            {
                "kind": "danger",
                "title": "Equipo sin fijar",
                "body": f"Falta fijar equipo para la jornada {round_no}.",
            }
        )
    if save["title"].startswith("Sin save"):
        items.append(
            {
                "kind": "danger",
                "title": "Save pendiente",
                "body": "No hay save actual marcado para tu entrenador.",
            }
        )
    if int(promos.get("active") or 0) > 0:
        items.append(
            {
                "kind": "ok",
                "title": "Rebajas activas",
                "body": f"{int(promos.get('active') or 0)} objeto(s) con descuento.",
            }
        )
    elif int(promos.get("pending") or 0) > 0:
        items.append(
            {
                "kind": "info",
                "title": "Rebajas en camino",
                "body": f"{int(promos.get('pending') or 0)} promocion(es) anunciadas.",
            }
        )
    locked, total = team_lock_counts(round_no)
    if total and locked < total:
        items.append(
            {
                "kind": "info",
                "title": "Equipos fijados",
                "body": f"{locked}/{total} entrenadores han fijado equipo.",
            }
        )
    if not items:
        items.append(
            {
                "kind": "ok",
                "title": "Todo en orden",
                "body": "No hay avisos importantes ahora mismo.",
            }
        )
    return items


def notification_count(items: list[dict[str, str]]) -> int:
    return sum(1 for item in items if item.get("kind") in {"danger", "warn", "info"})


def render_notification_styles(container: Any = None) -> None:
    target = container or st
    target.markdown(
        """
        <style>
        .app-notice {
          padding: 10px 11px;
          margin-bottom: 8px;
          border: 1px solid rgba(216,223,232,0.18);
          background: #101720;
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
        .app-notice--danger { border-left: 4px solid #ef5e68; }
        .app-notice--warn { border-left: 4px solid #efc257; }
        .app-notice--ok { border-left: 4px solid #58d18e; }
        .app-notice--info { border-left: 4px solid #6ea8ff; }
        section[data-testid="stSidebar"] .stPopover button {
          width: 100%;
          min-height: 42px;
          justify-content: flex-start;
          border-color: rgba(216,223,232,0.32);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.08), transparent 62%),
            linear-gradient(180deg, #252a33, #151a22);
          color: #fff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def notice_html(item: dict[str, str]) -> str:
    kind = escape(str(item.get("kind") or "info"))
    return (
        f"<div class='app-notice app-notice--{kind}'>"
        f"<div class='app-notice-title'>{escape(str(item.get('title') or 'Aviso'))}</div>"
        f"<div class='app-notice-body'>{escape(str(item.get('body') or ''))}</div>"
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
