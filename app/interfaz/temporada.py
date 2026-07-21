from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st

from app.liga.ranking import MAX_JORNADAS
from app.liga.rewards import CURRENT_COINS_BY_POSITION, CURRENT_POINTS_BY_POSITION
from storage import settings_get
from utils import active_users


def _league_state() -> dict[str, Any]:
    try:
        raw = settings_get("league_state")
        data = json.loads(raw or "{}")
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _render_css() -> None:
    st.markdown(
        """
        <style>
        .season-hero {
          padding: 18px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(135deg, rgba(143,214,107,0.18), transparent 38%),
            linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 30px rgba(0,0,0,0.2);
        }
        .season-kicker {
          color: var(--accent-soft);
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .season-title {
          margin-top: 10px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 21px;
          line-height: 1.25;
          text-transform: uppercase;
        }
        .season-subtitle {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-size: 21px;
          line-height: 1.14;
        }
        .season-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin: 14px 0;
        }
        .season-card {
          min-height: 106px;
          padding: 12px;
          border: 1px solid rgba(216,223,232,0.2);
          background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
        }
        .season-label {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .season-value {
          margin-top: 11px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 14px;
          line-height: 1.24;
        }
        .season-detail {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 18px;
          line-height: 1.08;
          overflow-wrap: anywhere;
        }
        .season-section-title {
          margin: 18px 0 8px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 13px;
          text-transform: uppercase;
        }
        .season-table {
          width: 100%;
          border-collapse: collapse;
          background: #101720;
          border: 1px solid rgba(216,223,232,0.2);
        }
        .season-table th,
        .season-table td {
          padding: 8px 10px;
          border-bottom: 1px solid rgba(216,223,232,0.1);
          color: var(--bw2-text-soft);
          text-align: left;
        }
        .season-table th {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        @media (max-width: 980px) {
          .season-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
          .season-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _card(label: str, value: str, detail: str) -> str:
    return (
        "<div class='season-card'>"
        f"<div class='season-label'>{escape(label)}</div>"
        f"<div class='season-value'>{escape(value)}</div>"
        f"<div class='season-detail'>{escape(detail)}</div>"
        "</div>"
    )


def _reward_table_html() -> str:
    rows = []
    for pos in sorted(CURRENT_POINTS_BY_POSITION):
        rows.append(
            "<tr>"
            f"<td>{pos}</td>"
            f"<td>{CURRENT_POINTS_BY_POSITION.get(pos, 0)}</td>"
            f"<td>{CURRENT_COINS_BY_POSITION.get(pos, 0)}</td>"
            "</tr>"
        )
    return (
        "<table class='season-table'>"
        "<thead><tr><th>Posicion</th><th>Puntos</th><th>Monedas</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _division_label(players: list[str]) -> str:
    return ", ".join(str(player) for player in players) if players else "-"


def _render_current_config() -> None:
    state = _league_state()
    users = list(active_users().keys())
    divisions = state.get("divisions") if isinstance(state.get("divisions"), dict) else {}
    div_a = list((divisions or {}).get("A") or users[:5])
    div_b = list((divisions or {}).get("B") or users[5:])
    tramo = max(int(state.get("tramo") or 1), 1)
    active = bool(state.get("active"))

    st.markdown(
        (
            "<div class='season-grid'>"
            + _card("Jornada actual", f"Tramo {tramo}", "En edicion" if active else "Cerrada")
            + _card("Jugadores activos", str(len(users)), _division_label(users))
            + _card("Divisiones", "Liga A / Liga B", f"{len(div_a)} y {len(div_b)} jugadores")
            + _card("Duracion", f"{MAX_JORNADAS} jornadas", "Configurable en 2.0")
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='season-section-title'>Liga A</div>", unsafe_allow_html=True)
        st.markdown(_card("Roster", f"{len(div_a)} jugadores", _division_label(div_a)), unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='season-section-title'>Liga B</div>", unsafe_allow_html=True)
        st.markdown(_card("Roster", f"{len(div_b)} jugadores", _division_label(div_b)), unsafe_allow_html=True)

    st.markdown("<div class='season-section-title'>Recompensas actuales</div>", unsafe_allow_html=True)
    st.markdown(_reward_table_html(), unsafe_allow_html=True)


def _render_draft_builder() -> None:
    st.markdown("<div class='season-section-title'>Borrador 2.0</div>", unsafe_allow_html=True)
    with st.form("season_draft_builder"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Nombre temporada", value="Temporada 2.0")
            rounds = st.number_input("Jornadas", min_value=1, max_value=12, value=int(MAX_JORNADAS), step=1)
        with c2:
            division_count = st.number_input("Divisiones", min_value=1, max_value=4, value=2, step=1)
            promote_count = st.number_input("Ascensos/descensos", min_value=0, max_value=5, value=3, step=1)
        with c3:
            players_text = st.text_area(
                "Jugadores",
                value="\n".join(active_users().keys()),
                height=126,
            )
        submitted = st.form_submit_button("Generar borrador local", use_container_width=True)

    if submitted:
        players = [line.strip() for line in players_text.splitlines() if line.strip()]
        draft = {
            "name": name.strip() or "Temporada",
            "rounds": int(rounds),
            "division_count": int(division_count),
            "movement_count": int(promote_count),
            "players": players,
            "points": CURRENT_POINTS_BY_POSITION,
            "coins": CURRENT_COINS_BY_POSITION,
            "saved": False,
        }
        st.session_state["season_draft_v2"] = draft

    draft = st.session_state.get("season_draft_v2")
    if isinstance(draft, dict):
        st.success("Borrador generado solo en esta sesion. No modifica la liga todavia.")
        st.json(draft)
    else:
        st.info("Este bloque prepara el modelo 2.0 sin guardar nada en Supabase todavia.")


def _render_future_flags() -> None:
    st.markdown("<div class='season-section-title'>Reglas que desbloquea este panel</div>", unsafe_allow_html=True)
    rows = [
        ("Cambios desde ahora", "Las modificaciones futuras no tocaran jornadas ya cerradas."),
        ("Aaron Avisa", "Cada publicacion o cambio importante tendra mensaje en Discord."),
        ("Sin SQL aun", "La persistencia final se decide cuando cerremos Supabase o migracion."),
        ("Copa separada", "La copa mantiene su propio sistema y no depende de esta config."),
    ]
    html = "<table class='season-table'><thead><tr><th>Sistema</th><th>Decision</th></tr></thead><tbody>"
    html += "".join(
        f"<tr><td>{escape(title)}</td><td>{escape(body)}</td></tr>"
        for title, body in rows
    )
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


def render_temporada() -> None:
    current_user = str(st.session_state.get("user") or "")
    if current_user.lower() != "anto":
        st.error("Solo Anto puede abrir la configuracion de temporada.")
        return

    _render_css()
    st.markdown(
        """
        <div class='season-hero'>
          <div class='season-kicker'>Panel Admin</div>
          <div class='season-title'>Temporada y configuracion 2.0</div>
          <div class='season-subtitle'>
            Estado actual de la liga y primer borrador para convertir las reglas en configuracion real.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_current_config()
    _render_draft_builder()
    _render_future_flags()
