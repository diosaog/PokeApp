from __future__ import annotations

from html import escape

import streamlit as st

from app.entrenadores.trainer_flags import is_trainer_retired
from app.interfaz.notifications import (
    collect_notifications,
    league_state_snapshot,
    money_snapshot,
    promo_snapshot,
    render_notifications_popover,
    save_snapshot,
    team_lock_snapshot,
)
from app.liga.context import current_jornada
from app.season.config import max_rounds
from utils import active_users


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
    league = league_state_snapshot()
    lock = team_lock_snapshot(user, jornada)
    save = save_snapshot(user)
    money = money_snapshot(user)
    promos = promo_snapshot(jornada)
    notices = collect_notifications(user=user, jornada=jornada)
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

    render_notifications_popover(notices)

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
    cols = st.columns(5)
    actions = [
        ("Fijar equipo", "Revisa tu perfil y guarda el equipo de la jornada.", "Entrenadores", "home_go_trainers"),
        ("Team Preview", "Consulta equipos fijados y prepara el combate.", "Team Preview", "home_go_preview"),
        ("Tienda", "Mira monedas, rebajas y objetos disponibles.", "Tienda", "home_go_shop"),
        ("Liga y Tabla", "Resultados, divisiones e historial competitivo.", "Liga y Tabla", "home_go_league"),
        ("Hall of Fame", "Campeones archivados, copas y equipos historicos.", "Hall of Fame", "home_go_hall"),
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
