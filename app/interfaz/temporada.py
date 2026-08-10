from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st

from app.season.config import (
    SeasonVersion,
    current_season_version,
    load_season_document,
    save_season_version,
    season_version_for_round,
    season_version_to_dict,
)
from app.season.validation import (
    has_blocking_issues,
    season_version_changes,
    validate_season_version,
)
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
          position: relative;
          overflow: hidden;
          padding: 15px 16px;
          border: 1px solid var(--bw2-edge);
          border-left: 4px solid var(--accent);
          border-radius: 16px;
          background:
            linear-gradient(118deg, rgba(77,141,255,0.12) 0 32%, transparent 32% 100%),
            linear-gradient(180deg, rgba(18,30,49,0.96), rgba(8,14,26,0.98));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 30px rgba(0,0,0,0.2);
          margin-bottom: 12px;
        }
        .season-hero:after {
          content: "";
          position: absolute;
          right: -48px;
          top: -36px;
          width: 210px;
          height: 140px;
          background: linear-gradient(135deg, rgba(255,255,255,0.07), transparent 58%);
          transform: skewX(-24deg);
        }
        .season-kicker {
          color: var(--accent-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .season-title {
          margin-top: 8px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: clamp(22px, 2.1vw, 30px);
          line-height: 1.12;
          text-transform: uppercase;
        }
        .season-subtitle {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 14px;
          line-height: 1.3;
        }
        .season-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin: 14px 0;
        }
        .season-card {
          min-height: 106px;
          padding: 10px 12px;
          border: 1px solid rgba(216,223,232,0.2);
          border-radius: 12px;
          background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .season-label {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .season-value {
          margin-top: 8px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 15px;
          line-height: 1.24;
        }
        .season-detail {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 13px;
          line-height: 1.25;
          overflow-wrap: anywhere;
        }
        .season-section-title {
          margin: 18px 0 9px;
          padding: 9px 11px;
          border: 1px solid rgba(216,223,232,0.16);
          border-left: 4px solid var(--accent);
          border-radius: 12px;
          background: linear-gradient(180deg, var(--bw2-panel-3), var(--bw2-panel));
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 13px;
          text-transform: uppercase;
        }
        .season-split {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(280px, 0.72fr);
          gap: 10px;
          margin: 10px 0 14px;
        }
        .season-alert {
          min-height: 74px;
          padding: 10px 11px;
          margin-bottom: 8px;
          border: 1px solid rgba(216,223,232,0.18);
          border-radius: 12px;
          background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
        }
        .season-alert-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.15;
          text-transform: uppercase;
        }
        .season-alert-body {
          margin-top: 6px;
          color: var(--bw2-text-soft);
          font-size: 13px;
          line-height: 1.25;
        }
        .season-alert--error { border-left: 4px solid #ef5e68; }
        .season-alert--warn { border-left: 4px solid #efc257; }
        .season-alert--ok { border-left: 4px solid #58d18e; }
        .season-alert--info { border-left: 4px solid #6ea8ff; }
        .season-version-list {
          display: grid;
          gap: 8px;
          margin-top: 8px;
        }
        .season-version-row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
          padding: 10px 11px;
          border: 1px solid rgba(216,223,232,0.18);
          border-radius: 12px;
          background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
        }
        .season-version-name {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.15;
          text-transform: uppercase;
          overflow-wrap: anywhere;
        }
        .season-version-meta {
          margin-top: 5px;
          color: var(--bw2-text-soft);
          font-size: 13px;
          line-height: 1.25;
        }
        .season-pill {
          display: inline-flex;
          align-items: center;
          min-height: 26px;
          padding: 4px 8px;
          border: 1px solid rgba(216,223,232,0.2);
          border-radius: 999px;
          background: rgba(8,12,18,0.46);
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 8px;
          text-transform: uppercase;
          white-space: nowrap;
        }
        .season-table {
          width: 100%;
          border-collapse: collapse;
          background: #101720;
          border: 1px solid rgba(216,223,232,0.2);
          border-radius: 12px;
          overflow: hidden;
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
        div[data-testid="stForm"] {
          border: 1px solid rgba(216,223,232,0.16);
          border-radius: 14px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.045), transparent 42%),
            rgba(8,14,26,0.9);
          padding: 14px 14px 10px;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        @media (max-width: 980px) {
          .season-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .season-split { grid-template-columns: 1fr; }
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


def _version_for_current_round() -> tuple[dict[str, Any], SeasonVersion, int]:
    state = _league_state()
    tramo = max(int(state.get("tramo") or 1), 1)
    document = load_season_document(players=list(active_users().keys()))
    return document, season_version_for_round(document, tramo), tramo


def _reward_table_html(version: SeasonVersion) -> str:
    positions = sorted(
        set(version.points_by_position.keys()) | set(version.coins_by_position.keys())
    )
    rows = []
    for pos in positions:
        rows.append(
            "<tr>"
            f"<td>{pos}</td>"
            f"<td>{version.points_by_position.get(pos, 0)}</td>"
            f"<td>{version.coins_by_position.get(pos, 0)}</td>"
            "</tr>"
        )
    return (
        "<table class='season-table'>"
        "<thead><tr><th>Posicion</th><th>Puntos</th><th>Monedas</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _issues_html(issues: list[dict[str, str]]) -> str:
    rows: list[str] = []
    for issue in issues:
        level = str(issue.get("level") or "info")
        title = str(issue.get("title") or "Aviso")
        body = str(issue.get("body") or "")
        rows.append(
            f"<div class='season-alert season-alert--{escape(level)}'>"
            f"<div class='season-alert-title'>{escape(title)}</div>"
            f"<div class='season-alert-body'>{escape(body)}</div>"
            "</div>"
        )
    return "".join(rows)


def _changes_table_html(changes: list[tuple[str, str, str]]) -> str:
    if not changes:
        return (
            "<div class='season-alert season-alert--info'>"
            "<div class='season-alert-title'>Sin cambios</div>"
            "<div class='season-alert-body'>La version propuesta coincide con la activa.</div>"
            "</div>"
        )
    rows = []
    for label, before, after in changes:
        rows.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{escape(before)}</td>"
            f"<td>{escape(after)}</td>"
            "</tr>"
        )
    return (
        "<table class='season-table'>"
        "<thead><tr><th>Campo</th><th>Actual</th><th>Nuevo</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _versions_from_document(document: dict[str, Any]) -> list[SeasonVersion]:
    return [
        season_version_for_round({"versions": [item], "active_version_id": item.get("id")})
        for item in document.get("versions", [])
        if isinstance(item, dict)
    ]


def _version_history_html(document: dict[str, Any]) -> str:
    versions = _versions_from_document(document)
    if not versions:
        return (
            "<div class='season-alert season-alert--info'>"
            "<div class='season-alert-title'>Sin historial</div>"
            "<div class='season-alert-body'>Todavia no hay versiones guardadas.</div>"
            "</div>"
        )
    active_id = str(document.get("active_version_id") or "")
    rows: list[str] = []
    for version in sorted(versions, key=lambda item: (item.effective_round, item.id), reverse=True):
        active = "Activa" if version.id == active_id else "Archivada"
        rows.append(
            "<div class='season-version-row'>"
            "<div>"
            f"<div class='season-version-name'>{escape(version.name)}</div>"
            "<div class='season-version-meta'>"
            f"Desde tramo {int(version.effective_round)} - "
            f"{int(version.max_rounds)} jornadas - "
            f"{len(version.players)} jugadores - "
            f"divisiones {' / '.join(str(size) for size in version.division_sizes)}"
            "</div>"
            "</div>"
            f"<span class='season-pill'>{escape(active)}</span>"
            "</div>"
        )
    return "<div class='season-version-list'>" + "".join(rows) + "</div>"


def _division_label(players: list[str]) -> str:
    return ", ".join(str(player) for player in players) if players else "-"


def _format_reward_lines(values: dict[int, int]) -> str:
    return "\n".join(f"{pos}={values[pos]}" for pos in sorted(values))


def _parse_reward_lines(raw: str, fallback: dict[int, int]) -> dict[int, int]:
    parsed: dict[int, int] = {}
    for line in str(raw or "").replace(",", "\n").splitlines():
        text = line.strip()
        if not text:
            continue
        if "=" in text:
            left, right = text.split("=", 1)
        elif ":" in text:
            left, right = text.split(":", 1)
        else:
            parts = text.split()
            if len(parts) != 2:
                continue
            left, right = parts
        try:
            pos = int(left.strip())
            value = int(right.strip())
        except Exception:
            continue
        if pos > 0:
            parsed[pos] = max(0, value)
    return dict(sorted((parsed or fallback).items()))


def _parse_division_sizes(raw: str, fallback: list[int], division_count: int) -> list[int]:
    numbers: list[int] = []
    for chunk in str(raw or "").replace("\n", ",").split(","):
        try:
            value = int(chunk.strip())
        except Exception:
            continue
        numbers.append(max(0, value))
    if not numbers:
        numbers = list(fallback)
    if len(numbers) < division_count:
        numbers += [0] * (division_count - len(numbers))
    return numbers[:division_count]


def _render_current_config() -> None:
    _document, version, tramo = _version_for_current_round()
    state = _league_state()
    users = list(active_users().keys())
    divisions = state.get("divisions") if isinstance(state.get("divisions"), dict) else {}
    div_a = list((divisions or {}).get("A") or users[: version.division_sizes[0]])
    div_b = list((divisions or {}).get("B") or users[len(div_a) :])
    active = bool(state.get("active"))

    st.markdown(
        (
            "<div class='season-grid'>"
            + _card("Jornada actual", f"Tramo {tramo}/{version.max_rounds}", "En edicion" if active else "Cerrada")
            + _card("Jugadores activos", str(len(users)), _division_label(users))
            + _card("Divisiones", f"{version.division_count} liga(s)", " / ".join(str(v) for v in version.division_sizes))
            + _card("Version reglas", version.name, f"Desde tramo {version.effective_round}")
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

    st.markdown("<div class='season-section-title'>Recompensas de esta version</div>", unsafe_allow_html=True)
    st.markdown(_reward_table_html(version), unsafe_allow_html=True)


def _render_config_editor() -> None:
    document, version, tramo = _version_for_current_round()
    players_default = version.players or list(active_users().keys())
    st.markdown("<div class='season-section-title'>Guardar version de reglas</div>", unsafe_allow_html=True)
    with st.form("season_config_editor"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Nombre temporada", value=version.name)
            effective_round = st.number_input(
                "Aplicar desde tramo",
                min_value=tramo,
                max_value=12,
                value=tramo,
                step=1,
            )
            rounds = st.number_input(
                "Jornadas",
                min_value=1,
                max_value=12,
                value=int(version.max_rounds),
                step=1,
            )
        with c2:
            division_count = st.number_input(
                "Divisiones",
                min_value=2,
                max_value=2,
                value=2,
                step=1,
                disabled=True,
            )
            division_sizes_text = st.text_input(
                "Jugadores por liga",
                value=", ".join(str(v) for v in version.division_sizes),
            )
            movement = st.number_input(
                "Ascensos/descensos",
                min_value=0,
                max_value=10,
                value=int(version.movement_count),
                step=1,
            )
        with c3:
            players_text = st.text_area(
                "Jugadores",
                value="\n".join(players_default),
                height=126,
            )

        r1, r2 = st.columns(2)
        with r1:
            points_text = st.text_area(
                "Puntos por posicion",
                value=_format_reward_lines(version.points_by_position),
                height=150,
            )
        with r2:
            coins_text = st.text_area(
                "Monedas por posicion",
                value=_format_reward_lines(version.coins_by_position),
                height=150,
            )

        submitted = st.form_submit_button("Guardar configuracion", use_container_width=True)

    players = [line.strip() for line in players_text.splitlines() if line.strip()]
    division_count_i = int(division_count)
    proposed_version = SeasonVersion(
        id=version.id,
        name=name.strip() or "Temporada",
        effective_round=int(effective_round),
        max_rounds=int(rounds),
        players=players,
        division_count=division_count_i,
        division_sizes=_parse_division_sizes(
            division_sizes_text,
            version.division_sizes,
            division_count_i,
        ),
        movement_count=int(movement),
        points_by_position=_parse_reward_lines(points_text, version.points_by_position),
        coins_by_position=_parse_reward_lines(coins_text, version.coins_by_position),
        rules=dict(version.rules),
    )
    issues = validate_season_version(proposed_version)
    changes = season_version_changes(version, proposed_version)

    st.markdown("<div class='season-section-title'>Revision antes de guardar</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='season-split'>"
            f"<div>{_issues_html(issues)}</div>"
            f"<div>{_changes_table_html(changes)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if submitted:
        if has_blocking_issues(issues):
            st.error("No se ha guardado: hay errores de configuracion que corregir.")
            return
        saved = save_season_version(proposed_version, effective_round=int(effective_round))
        try:
            from app.liga.ranking import clear_ranking_caches
            from app.tienda.money import clear_money_caches

            clear_money_caches()
            clear_ranking_caches()
        except Exception:
            pass
        st.success("Configuracion guardada.")
        st.session_state["season_last_saved_v2"] = saved
        document = saved

    if isinstance(st.session_state.get("season_last_saved_v2"), dict):
        with st.expander("Ultima configuracion guardada", expanded=False):
            st.json(st.session_state["season_last_saved_v2"])
    else:
        with st.expander("Documento de temporada actual", expanded=False):
            st.json(document)

    st.markdown("<div class='season-section-title'>Historial de versiones</div>", unsafe_allow_html=True)
    st.markdown(_version_history_html(document), unsafe_allow_html=True)


def render_temporada() -> None:
    current_user = str(st.session_state.get("user") or "")
    if current_user.lower() != "anto":
        st.error("Solo Anto puede abrir la configuracion de temporada.")
        return

    _render_css()
    current_version = current_season_version()
    st.markdown(
        (
            "<div class='season-hero'>"
            "<div class='season-kicker'>Panel Admin</div>"
            "<div class='season-title'>Temporada</div>"
            "<div class='season-subtitle'>Configuracion activa, recompensas y versiones de reglas.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='season-section-title'>Estado actual</div>", unsafe_allow_html=True)
    _render_current_config()
    st.markdown("<div class='season-section-title'>Editor</div>", unsafe_allow_html=True)
    _render_config_editor()
    with st.expander("Version activa en bruto", expanded=False):
        st.json(season_version_to_dict(current_version))
