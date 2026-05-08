from __future__ import annotations

import base64
import mimetypes
from html import escape
from pathlib import Path

import streamlit as st

from app.entrenadores.bridge import try_auto_load_bridge
from app.entrenadores.profile import find_trainer_image
from app.entrenadores.snapshot import get_trainer_snapshot
from app.juicios.penalties import get_user_penalties
from app.tienda.money import money_breakdown_from_parts
from dexdata import item_name_es
from showdown_sprites import showdown_sprite_url
from utils import USERS


def _cache_data(ttl: int = 20):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


@_cache_data(ttl=120)
def _img_uri(path: str, mtime: float | None = None) -> str:
    try:
        if not path:
            return ""
        mime = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def _division_for_player(player: str) -> str:
    divisions = st.session_state.get("league_divisions")
    if not isinstance(divisions, dict):
        return "-"
    if player in (divisions.get("A") or []):
        return "Liga A"
    if player in (divisions.get("B") or []):
        return "Liga B"
    return "-"


def _head_to_head(player_a: str, player_b: str) -> tuple[int, int]:
    wins_a = 0
    wins_b = 0
    matches = st.session_state.get("league_matches") or {}
    for divs in matches.values():
        if not isinstance(divs, dict):
            continue
        for division in ("A", "B"):
            for pair, winner in (divs.get(division) or {}).items():
                if not isinstance(pair, tuple) or len(pair) != 2:
                    continue
                p1, p2 = pair
                if {p1, p2} != {player_a, player_b}:
                    continue
                if winner == player_a:
                    wins_a += 1
                elif winner == player_b:
                    wins_b += 1
    return wins_a, wins_b


def _move_names(mon: dict) -> list[str]:
    moves = list(mon.get("moves") or [])
    if moves:
        return [str(move).strip() for move in moves if str(move).strip()][:4]

    detailed = []
    for move in list(mon.get("moves_detail") or []):
        if not isinstance(move, dict):
            continue
        name = str(move.get("name") or "").strip()
        if name:
            detailed.append(name)
    return detailed[:4]


def _held_item_name(mon: dict) -> str:
    found_numeric_item = False
    no_item_names = {"-", "0", "#0", "none", "no item", "(ningun objeto)", "(ningún objeto)"}
    for raw in (
        mon.get("held_item_id"),
        mon.get("ItemId"),
        mon.get("item_id"),
        mon.get("held_item"),
        mon.get("Item"),
        mon.get("item"),
    ):
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        if text.lower() in no_item_names:
            continue
        raw_id = text.lstrip("#")
        found_numeric_item = found_numeric_item or raw_id.isdigit()
        resolved = item_name_es(text)
        if not resolved or resolved.lower() in no_item_names:
            continue
        if raw_id.isdigit() and resolved in {text, raw_id}:
            continue
        if resolved:
            return resolved
    return "Objeto desconocido" if found_numeric_item else "-"


def _summary_snapshot(player: str) -> dict:
    from app.liga.ranking import current_points_total

    snapshot = get_trainer_snapshot(player)

    penalties = get_user_penalties(player)
    raw_dead_count = int(snapshot.get("dead_count") or 0)
    badges = int(snapshot.get("badge_count") or snapshot.get("badges") or 0)
    breakdown = money_breakdown_from_parts(
        player,
        badge_coins=4 * badges,
        penalties=penalties,
    )
    portrait = find_trainer_image(player)
    portrait_mtime = None
    try:
        if portrait:
            portrait_mtime = Path(portrait).stat().st_mtime
    except Exception:
        portrait_mtime = None

    return {
        "player": player,
        "division": _division_for_player(player),
        "points": current_points_total(player, raw_dead_count=raw_dead_count, penalties=penalties),
        "coins": int(breakdown.get("available") or 0),
        "badges": badges,
        "dead_count": raw_dead_count,
        "team": list(snapshot.get("team") or []),
        "save_name": str(snapshot.get("save_name") or "Sin save"),
        "store_blocked": bool(penalties.get("store_blocked")),
        "portrait_uri": _img_uri(portrait, portrait_mtime) if portrait else "",
    }


def _summary_card_html(snapshot: dict) -> str:
    portrait_html = (
        f"<img src='{snapshot['portrait_uri']}' alt='{escape(snapshot['player'])}'/>"
        if snapshot.get("portrait_uri")
        else "<div class='matchup-avatar-fallback'>SIN<br/>RETRATO</div>"
    )
    status_chip = (
        "<span class='matchup-alert'>Tienda bloqueada</span>"
        if snapshot.get("store_blocked")
        else "<span class='matchup-ok'>Sin castigos de tienda</span>"
    )
    return (
        "<div class='matchup-summary'>"
        "<div class='matchup-summary-head'>"
        f"<div class='matchup-avatar'>{portrait_html}</div>"
        "<div class='matchup-summary-meta'>"
        f"<div class='matchup-player'>{escape(snapshot['player'])}</div>"
        f"<div class='matchup-division'>{escape(snapshot['division'])}</div>"
        f"<div class='matchup-save'>{escape(snapshot['save_name'])}</div>"
        f"<div class='matchup-status-row'>{status_chip}</div>"
        "</div>"
        "</div>"
        "<div class='matchup-metric-grid'>"
        f"<div class='matchup-metric'><span>Puntos</span><strong>{snapshot['points']:.1f}</strong></div>"
        f"<div class='matchup-metric'><span>Monedas</span><strong>{snapshot['coins']}</strong></div>"
        f"<div class='matchup-metric'><span>Medallas</span><strong>{snapshot['badges']}</strong></div>"
        f"<div class='matchup-metric'><span>Muertos</span><strong>{snapshot['dead_count']}</strong></div>"
        "</div>"
        "</div>"
    )


def _team_card_html(snapshot: dict) -> str:
    mons_html: list[str] = []
    team = list(snapshot.get("team") or [])[:6]
    for mon in team:
        species = str(mon.get("species_name") or mon.get("species") or "Pokemon")
        nickname = str(mon.get("nickname") or "").strip()
        title = nickname or species
        subtitle = species if nickname else f"Lv. {mon.get('level', '-')}"
        sprite = showdown_sprite_url(
            species_name=species,
            form_index=mon.get("form_index"),
            form_name=mon.get("form_name"),
            is_shiny=bool(mon.get("is_shiny")),
            gender=mon.get("gender"),
            prefer_animated=False,
        )
        item = _held_item_name(mon)
        moves = _move_names(mon)
        moves_html = "".join(
            f"<div class='matchup-move'>{escape(move)}</div>"
            for move in (moves or ["(sin movimientos visibles)"])
        )
        mons_html.append(
            "<div class='matchup-mon'>"
            "<div class='matchup-mon-head'>"
            f"<img class='matchup-sprite' src='{sprite}' alt='{escape(species)}'/>"
            "<div class='matchup-mon-meta'>"
            f"<div class='matchup-mon-title'>{escape(title)}</div>"
            f"<div class='matchup-mon-sub'>{escape(subtitle)}</div>"
            f"<div class='matchup-mon-extra matchup-mon-item'>Objeto: {escape(item)}</div>"
            "</div>"
            "</div>"
            "<div class='matchup-move-list'>"
            f"{moves_html}"
            "</div>"
            "</div>"
        )

    while len(mons_html) < 6:
        mons_html.append(
            "<div class='matchup-mon matchup-mon-empty'>"
            "<div class='matchup-mon-title'>Slot vacio</div>"
            "<div class='matchup-mon-sub'>Sin Pokemon detectado</div>"
            "</div>"
        )

    return (
        "<div class='matchup-team-grid'>"
        f"{''.join(mons_html)}"
        "</div>"
    )


def _ensure_matchup_css() -> None:
    st.markdown(
        """
        <style>
        .matchup-shell {
          display: inline-block;
          padding: 8px 10px;
          border: 1px solid var(--bw2-edge-strong);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
          margin-bottom: 10px;
        }
        .matchup-note {
          margin-bottom: 12px;
          padding: 10px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.2;
        }
        .matchup-summary {
          margin-bottom: 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 12px;
        }
        .matchup-summary-head {
          display: grid;
          grid-template-columns: 116px 1fr;
          gap: 12px;
          align-items: center;
        }
        .matchup-avatar {
          width: 116px;
          height: 116px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
          overflow: hidden;
        }
        .matchup-avatar img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          image-rendering: pixelated;
        }
        .matchup-avatar-fallback {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-align: center;
          line-height: 1.6;
        }
        .matchup-player {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 13px;
          text-transform: uppercase;
        }
        .matchup-division,
        .matchup-save {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.1;
        }
        .matchup-status-row {
          margin-top: 10px;
        }
        .matchup-ok,
        .matchup-alert {
          display: inline-block;
          padding: 4px 8px;
          border: 1px solid var(--bw2-edge);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .matchup-ok {
          background: linear-gradient(180deg, #58d18e 0%, #2a8d5c 100%);
          color: #ffffff;
        }
        .matchup-alert {
          background: linear-gradient(180deg, #ef5e68 0%, #962d37 100%);
          color: #ffffff;
        }
        .matchup-metric-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 8px;
          margin-top: 12px;
        }
        .matchup-metric {
          padding: 8px 10px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
        }
        .matchup-metric span {
          display: block;
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .matchup-metric strong {
          display: block;
          margin-top: 7px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 12px;
        }
        .matchup-team-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }
        .matchup-mon {
          min-height: 230px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 10px;
        }
        .matchup-mon-empty {
          display: flex;
          flex-direction: column;
          justify-content: center;
          text-align: center;
        }
        .matchup-mon-head {
          display: grid;
          grid-template-columns: 82px 1fr;
          gap: 10px;
          align-items: center;
        }
        .matchup-sprite {
          width: 82px;
          height: 82px;
          object-fit: contain;
          image-rendering: pixelated;
          filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
        }
        .matchup-mon-title {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          line-height: 1.45;
        }
        .matchup-mon-sub,
        .matchup-mon-extra {
          margin-top: 6px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.05;
        }
        .matchup-mon-item {
          overflow-wrap: anywhere;
        }
        .matchup-move-list {
          display: grid;
          gap: 6px;
          margin-top: 10px;
        }
        .matchup-move {
          padding: 7px 8px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.05;
        }
        .matchup-versus {
          margin-bottom: 12px;
          padding: 10px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .matchup-versus strong {
          font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_matchup_preview(players: list[str] | None = None) -> None:
    _ensure_matchup_css()
    st.markdown("<div class='matchup-shell'>Previa de enfrentamiento</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='matchup-note'>"
            "Selecciona dos entrenadores para ver, a la vez, sus datos de liga, "
            "el save detectado y los movimientos de todo el equipo actual."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if not try_auto_load_bridge():
        st.warning("No se ha podido cargar el Bridge para leer los saves. La previa necesita acceso al lector DS.")
        return

    available = [player for player in (players or list(USERS.keys())) if player in USERS]
    if len(available) < 2:
        st.info("No hay suficientes jugadores para generar una previa.")
        return

    current_user = st.session_state.get("user")
    left_default = current_user if current_user in available else available[0]
    right_default = next((player for player in available if player != left_default), available[1])

    col_left, col_right = st.columns(2)
    with col_left:
        left_player = st.selectbox(
            "Entrenador A",
            available,
            index=available.index(left_default),
            key="matchup_left_player",
        )
    right_choices = [player for player in available if player != left_player]
    with col_right:
        right_player = st.selectbox(
            "Entrenador B",
            right_choices,
            index=right_choices.index(right_default) if right_default in right_choices else 0,
            key="matchup_right_player",
        )

    left_snapshot = _summary_snapshot(left_player)
    right_snapshot = _summary_snapshot(right_player)
    wins_left, wins_right = _head_to_head(left_player, right_player)
    st.markdown(
        (
            "<div class='matchup-versus'>"
            f"<strong>{escape(left_player)}</strong> vs <strong>{escape(right_player)}</strong>"
            f" | Duelo directo en liga: {wins_left} - {wins_right}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    summary_left, summary_right = st.columns(2, gap="large")
    with summary_left:
        st.markdown(_summary_card_html(left_snapshot), unsafe_allow_html=True)
        st.markdown(_team_card_html(left_snapshot), unsafe_allow_html=True)
    with summary_right:
        st.markdown(_summary_card_html(right_snapshot), unsafe_allow_html=True)
        st.markdown(_team_card_html(right_snapshot), unsafe_allow_html=True)
