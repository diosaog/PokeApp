from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from app.common import COIN
from app.entrenadores.trainer_flags import is_trainer_retired
from app.liga.context import current_jornada
from app.season.config import max_rounds
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


def _go_to(section: str) -> None:
    st.session_state["selected_section"] = section
    st.session_state["selected_section_radio"] = section
    st.rerun()


def _fmt_ts(value: Any) -> str:
    try:
        ts = int(value or 0)
        if ts <= 0:
            return "-"
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "-"


@_cache_data(ttl=10)
def _league_state_snapshot() -> dict[str, Any]:
    try:
        raw = settings_get("league_state")
        data = json.loads(raw or "{}")
    except Exception:
        data = {}
    divisions = data.get("divisions") if isinstance(data, dict) else {}
    if not isinstance(divisions, dict):
        divisions = {}
    return {
        "tramo": max(int((data or {}).get("tramo") or 1), 1),
        "active": bool((data or {}).get("active")),
        "division_a": list(divisions.get("A") or []),
        "division_b": list(divisions.get("B") or []),
    }


@_cache_data(ttl=15)
def _save_snapshot(user: str | None) -> dict[str, str]:
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
def _team_lock_snapshot(user: str | None, jornada: int) -> dict[str, str]:
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
def _money_snapshot(user: str | None) -> dict[str, str]:
    if not user:
        return {"title": f"{COIN} 0", "detail": "-"}
    try:
        coins = int(_money_available(str(user)))
    except Exception:
        coins = 0
    return {"title": f"{COIN} {coins}", "detail": "Monedas disponibles"}


@_cache_data(ttl=15)
def _promo_snapshot(jornada: int) -> dict[str, Any]:
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
def _team_lock_counts(jornada: int) -> tuple[int, int]:
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


def _notifications(
    *,
    user: str | None,
    jornada: int,
    lock: dict[str, str],
    save: dict[str, str],
    promos: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if user and is_trainer_retired(user):
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
                "body": f"Falta fijar equipo para la jornada {int(jornada)}.",
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
    locked, total = _team_lock_counts(int(jornada))
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


def _render_css() -> None:
    st.markdown(
        """
        <style>
        .home-hero {
          position: relative;
          overflow: hidden;
          padding: 18px 18px 16px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(135deg, rgba(110,168,255,0.24), transparent 34%),
            linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 30px rgba(0,0,0,0.2);
        }
        .home-hero:after {
          content: "";
          position: absolute;
          right: -72px;
          top: -86px;
          width: 210px;
          height: 210px;
          border-radius: 50%;
          border: 28px solid rgba(255,255,255,0.08);
          box-shadow: inset 0 0 0 22px rgba(0,0,0,0.18);
        }
        .home-kicker {
          color: var(--accent-soft);
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .home-title {
          margin-top: 10px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 22px;
          line-height: 1.25;
          text-transform: uppercase;
        }
        .home-subtitle {
          margin-top: 8px;
          max-width: 860px;
          color: var(--bw2-text-soft);
          font-size: 22px;
          line-height: 1.16;
        }
        .home-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin: 14px 0 4px;
        }
        .home-card {
          min-height: 116px;
          padding: 12px;
          border: 1px solid rgba(216,223,232,0.22);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.06), transparent 58%),
            linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .home-card-label {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .home-card-value {
          margin-top: 12px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 15px;
          line-height: 1.24;
          overflow-wrap: anywhere;
        }
        .home-card-detail {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 19px;
          line-height: 1.1;
          overflow-wrap: anywhere;
        }
        .home-section-title {
          margin: 18px 0 8px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 13px;
          text-transform: uppercase;
        }
        .home-action-card {
          min-height: 122px;
          padding: 12px;
          margin-bottom: 8px;
          border: 1px solid rgba(216,223,232,0.2);
          background: linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
        }
        .home-action-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 12px;
          text-transform: uppercase;
        }
        .home-action-body {
          margin-top: 8px;
          min-height: 44px;
          color: var(--bw2-text-soft);
          font-size: 19px;
          line-height: 1.08;
        }
        .home-notice {
          padding: 10px 11px;
          margin-bottom: 8px;
          border: 1px solid rgba(216,223,232,0.18);
          background: #101720;
        }
        .home-notice-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .home-notice-body {
          margin-top: 5px;
          color: var(--bw2-text-soft);
          font-size: 18px;
          line-height: 1.08;
        }
        .home-notice--danger { border-left: 4px solid #ef5e68; }
        .home-notice--warn { border-left: 4px solid #efc257; }
        .home-notice--ok { border-left: 4px solid #58d18e; }
        .home-notice--info { border-left: 4px solid #6ea8ff; }
        @media (max-width: 980px) {
          .home-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
          .home-grid { grid-template-columns: 1fr; }
          .home-title { font-size: 18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _card(label: str, value: str, detail: str) -> str:
    return (
        "<div class='home-card'>"
        f"<div class='home-card-label'>{escape(label)}</div>"
        f"<div class='home-card-value'>{escape(value)}</div>"
        f"<div class='home-card-detail'>{escape(detail)}</div>"
        "</div>"
    )


def _notice_html(item: dict[str, str]) -> str:
    kind = escape(str(item.get("kind") or "info"))
    return (
        f"<div class='home-notice home-notice--{kind}'>"
        f"<div class='home-notice-title'>{escape(str(item.get('title') or 'Aviso'))}</div>"
        f"<div class='home-notice-body'>{escape(str(item.get('body') or ''))}</div>"
        "</div>"
    )


def _render_notifications(items: list[dict[str, str]]) -> None:
    pending = sum(1 for item in items if item.get("kind") in {"danger", "warn", "info"})
    label = f"Notificaciones ({pending})" if pending else "Notificaciones"
    if hasattr(st, "popover"):
        with st.popover(label, use_container_width=True):
            for item in items:
                st.markdown(_notice_html(item), unsafe_allow_html=True)
    else:
        with st.expander(label, expanded=False):
            for item in items:
                st.markdown(_notice_html(item), unsafe_allow_html=True)


def _render_action(title: str, body: str, target: str, key: str) -> None:
    st.markdown(
        (
            "<div class='home-action-card'>"
            f"<div class='home-action-title'>{escape(title)}</div>"
            f"<div class='home-action-body'>{escape(body)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if st.button(title, key=key, use_container_width=True):
        _go_to(target)


def render_home() -> None:
    _render_css()
    user = str(st.session_state.get("user") or "")
    jornada = current_jornada()
    league = _league_state_snapshot()
    lock = _team_lock_snapshot(user, jornada)
    save = _save_snapshot(user)
    money = _money_snapshot(user)
    promos = _promo_snapshot(jornada)
    notices = _notifications(
        user=user,
        jornada=jornada,
        lock=lock,
        save=save,
        promos=promos,
    )
    status = "Modo espectador" if is_trainer_retired(user) else "Entrenador activo"

    st.markdown(
        (
            "<div class='home-hero'>"
            f"<div class='home-kicker'>{escape(status)}</div>"
            f"<div class='home-title'>Centro de entrenador - {escape(user or '-')}</div>"
            "<div class='home-subtitle'>"
            "Resumen rapido de jornada, equipo, save, tienda y avisos importantes."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    _render_notifications(notices)

    promo_title = "Sin rebajas"
    promo_detail = "Tienda a precio base"
    if int(promos.get("active") or 0):
        promo_title = f"{int(promos['active'])} activas"
        names = ", ".join(p["item"] for p in promos.get("sample") or [] if p.get("item"))
        promo_detail = names or "Descuentos disponibles"
    elif int(promos.get("pending") or 0):
        promo_title = f"{int(promos['pending'])} anunciadas"
        sample = promos.get("sample") or []
        promo_detail = sample[0]["opens"] if sample else "Apertura pendiente"

    st.markdown(
        (
            "<div class='home-grid'>"
            + _card(
                "Jornada",
                f"Tramo {int(league.get('tramo') or jornada)}/{max_rounds(int(league.get('tramo') or jornada))}",
                "En edicion" if league.get("active") else "Cerrada",
            )
            + _card("Equipo fijado", lock["title"], lock["detail"])
            + _card("Save actual", save["title"], save["detail"])
            + _card("Tienda", promo_title, promo_detail)
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='home-grid'>"
            + _card("Monedas", money["title"], money["detail"])
            + _card("Liga A", f"{len(league.get('division_a') or [])} jugadores", ", ".join(league.get("division_a") or ["-"]))
            + _card("Liga B", f"{len(league.get('division_b') or [])} jugadores", ", ".join(league.get("division_b") or ["-"]))
            + _card("Roster activo", f"{len(active_users())} entrenadores", "Temporada actual")
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='home-section-title'>Accesos rapidos</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    actions = [
        ("Fijar equipo", "Revisa tu perfil y guarda el equipo de la jornada.", "Entrenadores", "home_go_trainers"),
        ("Team Preview", "Consulta equipos fijados y prepara el combate.", "Team Preview", "home_go_preview"),
        ("Tienda", "Mira monedas, rebajas y objetos disponibles.", "Tienda", "home_go_shop"),
        ("Liga y Tabla", "Resultados, divisiones e historial competitivo.", "Liga y Tabla", "home_go_league"),
    ]
    for col, action in zip(cols, actions):
        with col:
            _render_action(*action)

    if user.lower() == "anto":
        st.markdown("<div class='home-section-title'>Panel Anto</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            _render_action(
                "Temporada",
                "Borrador de configuracion 2.0 y estado actual.",
                "Temporada",
                "home_go_season",
            )
        with c2:
            _render_action(
                "Saves",
                "Subidas, wipe y notas privadas de temporada.",
                "Saves",
                "home_go_saves",
            )
