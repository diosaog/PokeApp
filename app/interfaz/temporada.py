from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st

from app.admin.actions import (
    SEASON_DISCARD_CONFIRMATION,
    SEASON_DISCARD_DECISION,
    discard_active_season,
)
from app.entrenadores.trainer_flags import (
    INACTIVE_TRAINER_STATUSES,
    TRAINER_STATUS_ABANDONED,
    TRAINER_STATUS_ACTIVE,
    TRAINER_STATUS_DISQUALIFIED,
    TRAINER_STATUS_LABELS,
    TRAINER_STATUS_RETIRED,
    all_trainer_flags,
    is_trainer_robbed,
    set_trainer_status,
    status_labels_for,
    trainer_status,
)
from app.season.config import (
    RULE_DEFINITIONS,
    SeasonVersion,
    SUPPORTED_DIVISION_COUNT,
    current_season_version,
    latest_closed_round_from_league_state,
    load_season_document,
    save_season_version,
    season_version_for_round,
    season_version_to_dict,
)
from app.season.archive import (
    SEASON_STATE_ACTIVE,
    SEASON_STATE_ARCHIVED,
    SEASON_STATE_DISCARDED,
    SEASON_STATE_FINISHED,
    archive_current_season,
    finish_active_season,
    load_season_archives,
    load_season_lifecycle,
    prepare_new_active_season,
)
from app.season.validation import (
    has_blocking_issues,
    season_version_changes,
    validate_season_version,
)
from storage import clear_all_pokemon_flags, clear_pokemon_flags_for_owner, settings_get
from utils import USERS, active_users, users_with_retired_last


_PRIVATE_NEXT_LOCKE_PROMPT = """PokeApp 2.0 - notas privadas de temporada

La temporada actual nace limpia con 10 jugadores activos, dos divisiones de 5 y reglas
definitivas desde la jornada 1.

MONEDAS: 1=15, 2=14, 3=12, 4=11, 5=10, 6=11, 7=9, 8=8, 9=6, 10=4.
PUNTOS: 1=9, 2=8, 3=7, 4=6, 5=5, 6=5, 7=4, 8=3, 9=2, 10=1.

Siguiente objetivo grande:
- Crear sistema de temporadas configurable solo para Anto.
- Permitir configurar jugadores, numero de jornadas, divisiones, ascensos, descensos,
  puntos y monedas.
- Aplicar cambios de configuracion solo desde el momento en que se guardan.
- Enviar aviso de Aaron cuando se publique o modifique la configuracion de temporada.
- Rework visual 2.0: menu principal, login premium ligero, entrenadores, tienda, copa,
  juicios simplificados, Hall of Fame y panel admin.
- Optimizar al final: snapshots, caches, menos recalculos y consultas mas concretas."""


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
        .season-admin-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 8px 0 12px;
        }
        .season-status-token {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          min-height: 28px;
          padding: 5px 9px;
          border: 1px solid rgba(216,223,232,0.2);
          border-radius: 999px;
          background: rgba(8,12,18,0.5);
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 8px;
          text-transform: uppercase;
        }
        .season-status-token.is-active { border-color: rgba(88,209,142,0.55); }
        .season-status-token.is-inactive { border-color: rgba(239,94,104,0.58); }
        .season-status-token.is-flag { border-color: rgba(239,194,87,0.62); }
        .season-danger-panel {
          padding: 12px;
          border: 1px solid rgba(239,94,104,0.42);
          border-left: 4px solid #ef5e68;
          border-radius: 14px;
          background:
            linear-gradient(135deg, rgba(239,94,104,0.12), transparent 45%),
            rgba(8,14,26,0.94);
        }
        .season-danger-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 12px;
          text-transform: uppercase;
        }
        .season-danger-body {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 13px;
          line-height: 1.35;
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


def _rules_summary_html(version: SeasonVersion) -> str:
    rows: list[str] = []
    rules = version.rules if isinstance(version.rules, dict) else {}
    for rule_id, definition in RULE_DEFINITIONS.items():
        enabled = bool(rules.get(rule_id))
        functional = bool(definition.get("functional"))
        state = "Activa" if enabled else "Inactiva"
        kind = "Funcional" if functional else "Normativa"
        rows.append(
            "<div class='season-alert season-alert--info'>"
            f"<div class='season-alert-title'>{escape(str(definition.get('label') or rule_id))}</div>"
            f"<div class='season-alert-body'>{state} - {kind}</div>"
            "</div>"
        )
    return "".join(rows)


def _fmt_ts(value: Any) -> str:
    try:
        ts = int(value or 0)
    except Exception:
        ts = 0
    if ts <= 0:
        return "-"
    try:
        from datetime import datetime

        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def _lifecycle_label(state: str) -> str:
    return {
        SEASON_STATE_ACTIVE: "ACTIVE",
        SEASON_STATE_FINISHED: "FINISHED",
        SEASON_STATE_ARCHIVED: "ARCHIVED",
        SEASON_STATE_DISCARDED: "DISCARDED",
    }.get(str(state or "").lower(), str(state or "ACTIVE").upper())


def _render_lifecycle_panel(current_user: str) -> None:
    lifecycle = load_season_lifecycle()
    state = str(lifecycle.get("state") or SEASON_STATE_ACTIVE).lower()
    archives = load_season_archives()
    latest_archive = archives[0] if archives else {}
    st.markdown("<div class='season-section-title'>Ciclo de temporada</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='season-grid'>"
            + _card("Estado", _lifecycle_label(state), f"Actualizado: {_fmt_ts(lifecycle.get('updated_at'))}")
            + _card("Finalizada", _fmt_ts(lifecycle.get("finished_at")), "Revision antes de archivar")
            + _card("Archivada", _fmt_ts(lifecycle.get("archived_at")), str(lifecycle.get("archive_id") or "-"))
            + _card("Archivos", str(len(archives)), str(latest_archive.get("label") or "Sin historial"))
            + "</div>"
        ),
        unsafe_allow_html=True,
    )

    if state == SEASON_STATE_ACTIVE:
        st.info("Finalizar congela la temporada para revision. No borra datos.")
        if st.button("Finalizar temporada", use_container_width=True, key="season_finish_button"):
            try:
                finish_active_season(admin_user=current_user)
                st.success("Temporada finalizada. Revisa los datos antes de archivar.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif state == SEASON_STATE_FINISHED:
        st.info("La temporada esta finalizada. Puedes revisar Liga/Hall y archivarla cuando este todo correcto.")
        label = st.text_input(
            "Nombre del archivo",
            value=current_season_version().name,
            key="season_archive_label",
        )
        if st.button("Archivar temporada", use_container_width=True, key="season_archive_button"):
            try:
                archive = archive_current_season(admin_user=current_user, label=label)
                st.success(f"Temporada archivada: {archive.get('id')}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif state == SEASON_STATE_ARCHIVED:
        st.success("Temporada archivada. El historial y Hall of Fame ya pueden leerse sin datos vivos.")
        if st.button("Preparar nueva temporada", use_container_width=True, key="season_prepare_new_button"):
            try:
                report = prepare_new_active_season(admin_user=current_user)
                if report.get("ok"):
                    st.success("Nueva temporada preparada.")
                    st.rerun()
                else:
                    st.error("No se pudo preparar la nueva temporada.")
                    for err in report.get("errors") or []:
                        st.caption(f"- {err}")
            except Exception as exc:
                st.error(str(exc))
    elif state == SEASON_STATE_DISCARDED:
        st.warning("La temporada activa fue descartada sin archivo.")
        if st.button("Preparar nueva temporada", use_container_width=True, key="season_prepare_after_discard_button"):
            try:
                report = prepare_new_active_season(admin_user=current_user)
                if report.get("ok"):
                    st.success("Nueva temporada preparada.")
                    st.rerun()
                else:
                    st.error("No se pudo preparar la nueva temporada.")
                    for err in report.get("errors") or []:
                        st.caption(f"- {err}")
            except Exception as exc:
                st.error(str(exc))


def _rule_editor_fields(version: SeasonVersion) -> dict[str, Any]:
    current_rules = version.rules if isinstance(version.rules, dict) else {}
    next_rules = dict(current_rules)
    st.markdown("<div class='season-section-title'>Reglas funcionales</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (rule_id, definition) in enumerate(RULE_DEFINITIONS.items()):
        with cols[idx % 3]:
            next_rules[rule_id] = st.checkbox(
                str(definition.get("label") or rule_id),
                value=bool(current_rules.get(rule_id)),
                help=str(definition.get("description") or ""),
                key=f"season_rule_{rule_id}",
            )
    return next_rules


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
    st.markdown("<div class='season-section-title'>Reglas activas</div>", unsafe_allow_html=True)
    st.markdown(_rules_summary_html(version), unsafe_allow_html=True)


def _render_config_editor() -> None:
    document, version, tramo = _version_for_current_round()
    players_default = version.players or list(active_users().keys())
    closed_round = latest_closed_round_from_league_state()
    state = _league_state()
    min_active_round = int(tramo) + 1 if bool(state.get("active")) else int(tramo)
    min_effective_round = max(min_active_round, int(closed_round) + 1, 1)
    max_effective_round = max(12, min_effective_round)
    current_user = str(st.session_state.get("user") or "")
    st.markdown("<div class='season-section-title'>Guardar version de reglas</div>", unsafe_allow_html=True)
    with st.form("season_config_editor"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Nombre temporada", value=version.name)
            effective_round = st.number_input(
                "Aplicar desde tramo",
                min_value=min_effective_round,
                max_value=max_effective_round,
                value=min_effective_round,
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
                min_value=SUPPORTED_DIVISION_COUNT,
                max_value=SUPPORTED_DIVISION_COUNT,
                value=SUPPORTED_DIVISION_COUNT,
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

        rules = _rule_editor_fields(version)

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
        rules=rules,
    )
    issues = validate_season_version(proposed_version, known_players=list(USERS.keys()))
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
        try:
            saved = save_season_version(
                proposed_version,
                effective_round=int(effective_round),
                admin_user=current_user,
            )
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
        except Exception as exc:
            st.error(str(exc))

    if isinstance(st.session_state.get("season_last_saved_v2"), dict):
        with st.expander("Ultima configuracion guardada", expanded=False):
            st.json(st.session_state["season_last_saved_v2"])
    else:
        with st.expander("Documento de temporada actual", expanded=False):
            st.json(document)

    st.markdown("<div class='season-section-title'>Historial de versiones</div>", unsafe_allow_html=True)
    st.markdown(_version_history_html(document), unsafe_allow_html=True)


def _status_tokens_html(trainer: str) -> str:
    status = trainer_status(trainer)
    status_label = TRAINER_STATUS_LABELS.get(status, "Activo")
    status_class = "is-active" if status == TRAINER_STATUS_ACTIVE else "is-inactive"
    tokens = [
        f"<span class='season-status-token {status_class}'>{escape(status_label)}</span>"
    ]
    if is_trainer_robbed(trainer) and status == TRAINER_STATUS_ACTIVE:
        tokens.append("<span class='season-status-token is-flag'>Robado</span>")
    return "<div class='season-admin-strip'>" + "".join(tokens) + "</div>"


def _trainer_status_rows_html() -> str:
    rows: list[str] = []
    flags = all_trainer_flags()
    for trainer in users_with_retired_last(USERS):
        status = trainer_status(trainer)
        labels = status_labels_for(trainer)
        raw_flags = flags.get(trainer, {})
        rows.append(
            "<tr>"
            f"<td>{escape(str(trainer))}</td>"
            f"<td>{escape(TRAINER_STATUS_LABELS.get(status, 'Activo'))}</td>"
            f"<td>{escape(', '.join(labels) if labels else '-')}</td>"
            f"<td>{escape(str(raw_flags.get('inactive_by') or raw_flags.get('retired_by') or '-'))}</td>"
            "</tr>"
        )
    return (
        "<table class='season-table'>"
        "<thead><tr><th>Entrenador</th><th>Status</th><th>Flags visibles</th><th>Admin</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _clear_runtime_after_season_discard(current_user: str | None) -> None:
    auth_ok = bool(st.session_state.get("auth_ok"))
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    st.session_state["auth_ok"] = auth_ok
    st.session_state["user"] = current_user
    st.session_state["selected_section"] = "Inicio"
    st.session_state["_season_discard_done"] = True


def _render_trainer_management(current_user: str) -> None:
    st.markdown("<div class='season-section-title'>Estado oficial de entrenadores</div>", unsafe_allow_html=True)
    st.markdown(_trainer_status_rows_html(), unsafe_allow_html=True)

    league_active = bool(_league_state().get("active"))
    if league_active:
        st.warning("Hay una jornada abierta. Cierra o cancela la jornada antes de cambiar estados.")

    options = users_with_retired_last(USERS)
    if not options:
        st.info("No hay entrenadores configurados.")
        return

    with st.form("season_trainer_status_form"):
        target = st.selectbox(
            "Entrenador",
            options,
            format_func=lambda name: f"{name} - {TRAINER_STATUS_LABELS.get(trainer_status(name), 'Activo')}",
        )
        status = trainer_status(str(target))
        st.markdown(_status_tokens_html(str(target)), unsafe_allow_html=True)

        if status in INACTIVE_TRAINER_STATUSES:
            st.info("No hay reactivacion automatica: los estados inactivos son permanentes en las reglas actuales.")
            action = ""
        else:
            action = st.radio(
                "Nuevo estado",
                ["Abandono", "Retirado", "Descalificado"],
                horizontal=True,
            )
        note = st.text_input("Nota interna", value="")
        confirm = st.text_input("Escribe el nombre exacto del entrenador")
        submitted = st.form_submit_button(
            "Aplicar estado oficial",
            disabled=league_active or status in INACTIVE_TRAINER_STATUSES,
            use_container_width=True,
        )

    if not submitted:
        return
    if confirm.strip() != str(target):
        st.error("La confirmacion no coincide con el entrenador seleccionado.")
        return
    status_map = {
        "Abandono": TRAINER_STATUS_ABANDONED,
        "Retirado": TRAINER_STATUS_RETIRED,
        "Descalificado": TRAINER_STATUS_DISQUALIFIED,
    }
    try:
        set_trainer_status(
            str(target),
            status_map.get(action, TRAINER_STATUS_ABANDONED),
            by_user=current_user,
            note=note.strip() or None,
        )
        try:
            from app.liga.ranking import clear_ranking_caches
            from app.tienda.money import clear_money_caches

            clear_money_caches()
            clear_ranking_caches()
        except Exception:
            pass
        st.success(f"Estado actualizado para {target}.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def _render_competition_management() -> None:
    st.markdown("<div class='season-section-title'>Consola oficial de Liga</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='season-alert season-alert--info'>"
            "<div class='season-alert-title'>Mutaciones oficiales centralizadas</div>"
            "<div class='season-alert-body'>Abrir jornadas, guardar resultados, modificar cierres y reiniciar Liga se gestionan desde aqui.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    open_console = st.toggle(
        "Abrir consola de Liga",
        value=False,
        key="season_open_league_admin_console",
    )
    if not open_console:
        return
    try:
        from app.liga.ui import page_tabla as render_league_admin

        render_league_admin(admin_mode=True)
    except Exception as exc:
        st.error(f"No se pudo cargar la consola de Liga: {exc}")


def _render_history_placeholder() -> None:
    st.markdown("<div class='season-section-title'>Historial de temporadas</div>", unsafe_allow_html=True)
    archives = load_season_archives()
    if not archives:
        st.markdown(
            (
                "<div class='season-alert season-alert--info'>"
                "<div class='season-alert-title'>Sin archivos</div>"
                "<div class='season-alert-body'>Cuando archives una temporada aparecera aqui como snapshot historico independiente del estado vivo.</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return
    rows: list[str] = []
    for archive in archives:
        league = archive.get("league") if isinstance(archive.get("league"), dict) else {}
        participants = archive.get("participants") if isinstance(archive.get("participants"), list) else []
        rows.append(
            "<tr>"
            f"<td>{escape(str(archive.get('label') or archive.get('id') or '-'))}</td>"
            f"<td>{escape(_fmt_ts(archive.get('archived_at')))}</td>"
            f"<td>{escape(str(league.get('champion') or '-'))}</td>"
            f"<td>{len(participants)}</td>"
            f"<td>{escape(str(league.get('final_round') or 0))}</td>"
            f"<td>{escape(str(archive.get('state') or '-'))}</td>"
            "</tr>"
        )
    st.markdown(
        (
            "<table class='season-table'>"
            "<thead><tr><th>Temporada</th><th>Archivada</th><th>Campeon Liga</th><th>Jugadores</th><th>Jornadas</th><th>Estado</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        ),
        unsafe_allow_html=True,
    )
    selected = st.selectbox(
        "Abrir resumen",
        archives,
        format_func=lambda archive: str(archive.get("label") or archive.get("id") or "-"),
        key="season_archive_detail_select",
    )
    if isinstance(selected, dict):
        league = selected.get("league") if isinstance(selected.get("league"), dict) else {}
        hall_entries = selected.get("hall_entries") if isinstance(selected.get("hall_entries"), list) else []
        st.markdown(
            (
                "<div class='season-split'>"
                + _card("Campeon Liga", str(league.get("champion") or "-"), f"Finalista: {league.get('runner_up') or '-'}")
                + _card("Hall entries", str(len(hall_entries)), "Entradas derivadas del archivo")
                + "</div>"
            ),
            unsafe_allow_html=True,
        )
        with st.expander("Archivo en bruto", expanded=False):
            st.json(selected)


def _render_pokemon_flags_maintenance() -> None:
    st.markdown("<div class='season-section-title'>Mantenimiento de flags Pokemon</div>", unsafe_allow_html=True)
    with st.form("season_pokemon_flags_reset_form"):
        scope = st.radio(
            "Alcance",
            ["Un entrenador", "Todos"],
            horizontal=True,
            key="season_flags_reset_scope",
        )
        target = None
        if scope == "Un entrenador":
            target = st.selectbox(
                "Entrenador",
                users_with_retired_last(USERS),
                key="season_flags_reset_target",
            )
            expected = str(target or "")
        else:
            expected = "RESET FLAGS"
        confirm = st.text_input(f"Escribe {expected} para confirmar")
        submitted = st.form_submit_button(
            "Reiniciar flags",
            disabled=confirm.strip() != expected,
            use_container_width=True,
        )
    if not submitted:
        return
    try:
        if scope == "Todos":
            clear_all_pokemon_flags()
            st.success("Todos los flags de Pokemon se han reiniciado.")
        else:
            clear_pokemon_flags_for_owner(str(target or ""))
            st.success(f"Flags de Pokemon reiniciados para {target}.")
    except Exception as exc:
        st.error(str(exc))


def _render_risk_zone(current_user: str) -> None:
    st.markdown("<div class='season-section-title'>Zona de riesgo</div>", unsafe_allow_html=True)
    _render_pokemon_flags_maintenance()
    st.markdown(
        (
            "<div class='season-danger-panel'>"
            "<div class='season-danger-title'>Descartar temporada</div>"
            "<div class='season-danger-body'>Descartar no crea archivo historico ni Hall. Para guardar la temporada usa Ciclo de temporada: Finalizar y Archivar.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.warning("Descartar borra datos activos de temporada. No crea archivo historico.")
    confirm = st.text_input(
        f"Escribe {SEASON_DISCARD_CONFIRMATION} para confirmar",
        key="season_discard_confirm",
    )
    if st.button(
        "Descartar temporada activa",
        type="primary",
        disabled=confirm.strip() != SEASON_DISCARD_CONFIRMATION,
        use_container_width=True,
        key="season_discard_button",
    ):
        try:
            report = discard_active_season(
                admin_user=current_user,
                decision=SEASON_DISCARD_DECISION,
                confirmation=confirm,
            )
            if report.get("ok"):
                _clear_runtime_after_season_discard(current_user)
                st.rerun()
            else:
                st.error("Descarte incompleto.")
                for err in report.get("errors") or []:
                    st.caption(f"- {err}")
        except Exception as exc:
            st.error(str(exc))


def _render_private_notes() -> None:
    st.markdown("<div class='season-section-title'>Notas privadas de temporada</div>", unsafe_allow_html=True)
    st.code(_PRIVATE_NEXT_LOCKE_PROMPT, language="text")


def render_temporada() -> None:
    current_user = str(st.session_state.get("user") or "")
    if current_user.lower() != "anto":
        st.error("Solo Anto puede abrir la configuracion de temporada.")
        return

    _render_css()
    current_version = current_season_version()
    if st.session_state.pop("_season_discard_done", False):
        st.success("Temporada descartada.")
    st.markdown(
        (
            "<div class='season-hero'>"
            "<div class='season-kicker'>Panel Admin</div>"
            "<div class='season-title'>Temporada</div>"
            "<div class='season-subtitle'>Back office oficial: estado, reglas, entrenadores, Liga y acciones de riesgo.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            "Estado",
            "Configuracion",
            "Entrenadores",
            "Competicion",
            "Historial",
            "Riesgo",
        ]
    )
    with tabs[0]:
        _render_lifecycle_panel(current_user)
        st.markdown("<div class='season-section-title'>Estado actual</div>", unsafe_allow_html=True)
        _render_current_config()
    with tabs[1]:
        st.markdown("<div class='season-section-title'>Editor</div>", unsafe_allow_html=True)
        _render_config_editor()
        with st.expander("Version activa en bruto", expanded=False):
            st.json(season_version_to_dict(current_version))
    with tabs[2]:
        _render_trainer_management(current_user)
    with tabs[3]:
        _render_competition_management()
    with tabs[4]:
        _render_history_placeholder()
        _render_private_notes()
    with tabs[5]:
        _render_risk_zone(current_user)
