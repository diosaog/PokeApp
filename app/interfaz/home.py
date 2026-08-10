from __future__ import annotations

from html import escape

import streamlit as st

from app.entrenadores.trainer_flags import is_trainer_retired
from app.interfaz.notifications import (
    collect_notifications,
    league_state_snapshot,
    money_snapshot,
    promo_snapshot,
    save_snapshot,
    team_lock_snapshot,
)
from app.liga.context import current_jornada
from app.season.config import max_rounds


def _go_to(section: str) -> None:
    st.session_state["selected_section"] = section
    st.session_state["selected_section_radio"] = section
    st.rerun()


def _render_css() -> None:
    st.markdown(
        """
        <style>
        .home-hero {
          position: relative;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
          gap: 22px;
          align-items: center;
          overflow: hidden;
          min-height: 188px;
          padding: 24px;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-large);
          background:
            radial-gradient(circle at 50% 0, rgba(77,141,255,0.12), transparent 42%),
            linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)),
            var(--surface-1);
          box-shadow: var(--shadow-hero);
        }
        .home-hero::after {
          content: "";
          position: absolute;
          right: -54px;
          top: -64px;
          width: 188px;
          height: 188px;
          border-radius: 50%;
          border: 26px solid rgba(255,255,255,0.035);
          box-shadow: inset 0 0 0 18px rgba(0,0,0,0.24);
          pointer-events: none;
        }
        .home-side {
          position: relative;
          z-index: 1;
          min-width: 0;
        }
        .home-side.home-right {
          text-align: right;
        }
        .home-versus {
          position: relative;
          z-index: 1;
          width: 86px;
          height: 86px;
          display: grid;
          place-items: center;
          border: 1px solid var(--border-normal);
          border-radius: 50%;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02)),
            var(--surface-2);
          color: var(--pokemon-yellow);
          font-size: 22px;
          font-weight: 950;
          box-shadow: var(--shadow-card);
        }
        .home-kicker {
          color: var(--text-secondary);
          font-size: 12px;
          font-weight: 850;
          text-transform: uppercase;
        }
        .home-title {
          margin-top: 10px;
          color: var(--text-primary);
          font-size: clamp(28px, 4vw, 44px);
          font-weight: 950;
          line-height: 1.02;
        }
        .home-subtitle {
          margin-top: 10px;
          color: var(--text-secondary);
          font-size: 14px;
          line-height: 1.35;
        }
        .home-hero-actions {
          position: relative;
          z-index: 1;
          margin-top: 16px;
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .home-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin: 16px 0 4px;
        }
        .home-card {
          min-height: 118px;
          padding: 15px;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-card);
          background: var(--surface-1);
          box-shadow: var(--shadow-card);
        }
        .home-card-label {
          color: var(--text-muted);
          font-size: 11px;
          font-weight: 850;
          text-transform: uppercase;
        }
        .home-card-value {
          margin-top: 10px;
          color: var(--text-primary);
          font-size: 20px;
          font-weight: 900;
          line-height: 1.15;
          overflow-wrap: anywhere;
        }
        .home-card-detail {
          margin-top: 7px;
          color: var(--text-secondary);
          font-size: 13px;
          line-height: 1.35;
          overflow-wrap: anywhere;
        }
        .home-section-title {
          margin: 22px 0 10px;
          color: var(--text-primary);
          font-size: 18px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .home-context-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }
        .home-context-card {
          min-height: 88px;
          padding: 14px;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-card);
          background: var(--surface-2);
        }
        .home-activity {
          margin-top: 16px;
          display: grid;
          gap: 8px;
        }
        .home-activity-row {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding: 11px 12px;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-input);
          background: rgba(255,255,255,0.025);
        }
        .home-activity-row strong {
          color: var(--text-primary);
          font-size: 13px;
        }
        .home-activity-row span {
          color: var(--text-muted);
          font-size: 12px;
        }
        @media (max-width: 980px) {
          .home-hero { grid-template-columns: 1fr; }
          .home-side.home-right { text-align: left; }
          .home-versus { width: 64px; height: 64px; }
          .home-grid,
          .home-context-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
          .home-grid,
          .home-context-grid { grid-template-columns: 1fr; }
          .home-title { font-size: 26px; }
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


def _context_card(title: str, value: str, detail: str) -> str:
    return (
        "<div class='home-context-card'>"
        f"<div class='home-card-label'>{escape(title)}</div>"
        f"<div class='home-card-value'>{escape(value)}</div>"
        f"<div class='home-card-detail'>{escape(detail)}</div>"
        "</div>"
    )


def _activity_html(items: list[dict[str, str]]) -> str:
    rows = []
    for item in items[:3]:
        title = str(item.get("title") or "Actividad")
        body = str(item.get("body") or "").strip()
        when = str(item.get("time") or "").strip()
        label = f"{title}: {body}" if body else title
        rows.append(
            "<div class='home-activity-row'>"
            f"<strong>{escape(label)}</strong>"
            f"<span>{escape(when)}</span>"
            "</div>"
        )
    return "".join(rows) or (
        "<div class='home-activity-row'>"
        "<strong>Sin actividad reciente</strong><span></span>"
        "</div>"
    )


def _division_for_user(user: str, league: dict) -> str:
    if user in (league.get("division_a") or []):
        return "Liga A"
    if user in (league.get("division_b") or []):
        return "Liga B"
    return "Liga"


def _next_opponent(user: str, jornada: int, league: dict) -> tuple[str, str]:
    matches = league.get("matches") if isinstance(league.get("matches"), dict) else {}
    round_matches = matches.get(str(jornada)) or matches.get(int(jornada)) or {}
    unresolved: list[tuple[str, str | None]] = []
    resolved: list[tuple[str, str | None]] = []
    for div_name in ("A", "B"):
        for match in (round_matches.get(div_name) or []):
            if not isinstance(match, dict):
                continue
            p1 = str(match.get("p1") or "")
            p2 = str(match.get("p2") or "")
            if user not in (p1, p2):
                continue
            other = p2 if user == p1 else p1
            winner = match.get("winner")
            target = unresolved if not winner else resolved
            target.append((other or "Por definir", winner))
    if unresolved:
        return unresolved[0][0], "Pendiente"
    if resolved:
        return resolved[0][0], "Resultado marcado"

    division = (
        list(league.get("division_a") or [])
        if user in (league.get("division_a") or [])
        else list(league.get("division_b") or [])
    )
    for candidate in division:
        if candidate != user:
            return str(candidate), "Calendario por definir"
    return "Por definir", "Sin rival asignado"


def render_home() -> None:
    _render_css()
    user = str(st.session_state.get("user") or "")
    jornada = current_jornada()
    league = league_state_snapshot()
    lock = team_lock_snapshot(user, jornada)
    save = save_snapshot(user)
    money = money_snapshot(user)
    promos = promo_snapshot(jornada)
    notices = collect_notifications(user=user, jornada=jornada)
    status = "Modo espectador" if is_trainer_retired(user) else "Entrenador activo"
    opponent, opponent_state = _next_opponent(user, jornada, league)
    division = _division_for_user(user, league)
    division_roster = (
        league.get("division_a")
        if division == "Liga A"
        else league.get("division_b")
        if division == "Liga B"
        else []
    )
    lock_ready = str(lock.get("title") or "").lower().startswith("fijado")

    st.markdown(
        (
            "<div class='home-hero'>"
            "<div class='home-side'>"
            f"<div class='home-kicker'>Jornada {int(jornada)} · {escape(division)}</div>"
            f"<div class='home-title'>{escape(user or '-')}</div>"
            f"<div class='home-subtitle'>{escape(status)} · {escape(lock['title'])}</div>"
            "</div>"
            "<div class='home-versus'>VS</div>"
            "<div class='home-side home-right'>"
            f"<div class='home-kicker'>{escape(opponent_state)}</div>"
            f"<div class='home-title'>{escape(opponent)}</div>"
            f"<div class='home-subtitle'>Team Preview y preparación de combate.</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    cta_1, cta_2, _spacer = st.columns([1, 1, 3])
    with cta_1:
        if st.button(
            "Ver Team Preview",
            key="home_primary_preview",
            type="primary",
            use_container_width=True,
        ):
            _go_to("Team Preview")
    with cta_2:
        if st.button(
            "Fijar equipo" if not lock_ready else "Ver equipo",
            key="home_primary_team",
            use_container_width=True,
        ):
            _go_to("Entrenadores")

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
            + _card("Monedas", money["title"], money["detail"])
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='home-section-title'>Contexto rapido</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='home-context-grid'>"
            + _context_card("Tienda", promo_title, promo_detail)
            + _context_card("Save", save["title"], save["detail"])
            + _context_card("Division", division, ", ".join(division_roster or ["-"]))
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='home-section-title'>Actividad reciente</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='home-activity'>{_activity_html(notices)}</div>",
        unsafe_allow_html=True,
    )
