from __future__ import annotations

from datetime import datetime
import json

import streamlit as st

from app.liga.ranking import MAX_JORNADAS, final_podium, general_table_sorted
from app.liga.table_summary import coins_for_user, fmt_points, league_table_rows
from storage import settings_get, settings_set


_SEASON_ARCHIVE_KEY = "season_archive"


def _load_archive() -> list[dict]:
    try:
        raw = settings_get(_SEASON_ARCHIVE_KEY)
        if not raw:
            return []
        obj = json.loads(raw)
        if isinstance(obj, list):
            return [entry for entry in obj if isinstance(entry, dict)]
    except Exception:
        pass
    return []


def _save_archive(entries: list[dict]) -> None:
    settings_set(_SEASON_ARCHIVE_KEY, json.dumps(entries, ensure_ascii=False))


def _current_league_snapshot() -> dict:
    table = general_table_sorted()
    podium = final_podium()
    league_results = st.session_state.get("league_results") or {}
    movements = st.session_state.get("league_movements") or {}

    history: list[dict] = []
    tramos = set()
    for player_map in league_results.values():
        if not isinstance(player_map, dict):
            continue
        for tramo in player_map.keys():
            try:
                tramos.add(int(tramo))
            except Exception:
                continue

    for tramo in sorted(tramos):
        rows = []
        for player, player_map in league_results.items():
            try:
                position = player_map.get(tramo)
            except Exception:
                position = None
            if position is None:
                continue
            rows.append({"pos": int(position), "player": player})
        rows.sort(key=lambda row: row["pos"])
        history.append(
            {
                "tramo": tramo,
                "rows": rows,
                "up": list((movements.get(tramo) or {}).get("up") or []),
                "down": list((movements.get(tramo) or {}).get("down") or []),
            }
        )

    return {
        "tramo_actual": int(st.session_state.get("league_tramo", 1)),
        "activa": bool(st.session_state.get("league_active", False)),
        "finalizada": bool(int(st.session_state.get("league_tramo", 1)) > MAX_JORNADAS and not st.session_state.get("league_active", False)),
        "podium": [
            {"pos": idx, "player": player, "points": fmt_points(points), "coins": coins_for_user(player)}
            for idx, (player, points) in enumerate(podium, start=1)
        ],
        "table": league_table_rows(table, include_coins=True),
        "history": history,
    }


def _current_swiss_snapshot() -> dict:
    state = st.session_state.get("swiss")
    if not isinstance(state, dict):
        try:
            raw = settings_get("copa_swiss_state")
            state = json.loads(raw) if raw else {}
        except Exception:
            state = {}
    topcut = state.get("topcut") if isinstance(state, dict) else {}
    if not isinstance(topcut, dict):
        topcut = {}
    final_pair = list(topcut.get("final") or [])
    return {
        "configured": bool(state.get("configured")) if isinstance(state, dict) else False,
        "players": list(state.get("players") or []) if isinstance(state, dict) else [],
        "champion": str(topcut.get("champion") or ""),
        "final": final_pair[:2],
        "finalists": list(topcut.get("finalists") or [])[:4],
    }


def _current_doubles_snapshot() -> dict:
    state = st.session_state.get("copa_dobles")
    if not isinstance(state, dict):
        try:
            raw = settings_get("copa_dobles_state")
            state = json.loads(raw) if raw else {}
        except Exception:
            state = {}
    teams = {str(team.get("id")): dict(team) for team in list(state.get("teams") or []) if isinstance(team, dict)}
    final_data = dict(state.get("final") or {}) if isinstance(state, dict) else {}
    final_a = teams.get(str(final_data.get("team_a") or ""))
    final_b = teams.get(str(final_data.get("team_b") or ""))
    score_a = final_data.get("score_a")
    score_b = final_data.get("score_b")

    champion = ""
    if final_a and final_b:
        try:
            a_value = int(score_a)
            b_value = int(score_b)
            if (a_value, b_value) in {(2, 0), (2, 1), (1, 2), (0, 2)}:
                champion = str((final_a if a_value > b_value else final_b).get("name") or "")
        except Exception:
            champion = ""

    return {
        "configured": bool(state.get("configured")) if isinstance(state, dict) else False,
        "teams": [str(team.get("name") or "") for team in list(teams.values()) if str(team.get("name") or "").strip()],
        "final": [
            str((final_a or {}).get("name") or ""),
            str((final_b or {}).get("name") or ""),
        ],
        "champion": champion,
    }


def archive_current_season(name: str) -> dict:
    season_name = str(name or "").strip() or f"Temporada {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": season_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "league": _current_league_snapshot(),
        "swiss": _current_swiss_snapshot(),
        "doubles": _current_doubles_snapshot(),
    }
    archive = _load_archive()
    archive.insert(0, entry)
    _save_archive(archive)
    return entry


def _render_archive_entry(entry: dict) -> None:
    league = dict(entry.get("league") or {})
    swiss = dict(entry.get("swiss") or {})
    doubles = dict(entry.get("doubles") or {})

    st.caption(f"Archivado: {entry.get('created_at') or '-'}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Liga", "Finalizada" if league.get("finalizada") else "En curso", str(league.get("tramo_actual") or "-"))
    with c2:
        st.metric("Campeon Swiss", swiss.get("champion") or "-", f"{len(swiss.get('players') or [])} jugadores")
    with c3:
        st.metric("Campeon Dobles", doubles.get("champion") or "-", f"{len(doubles.get('teams') or [])} equipos")

    podium = list(league.get("podium") or [])
    if podium:
        st.markdown("**Podio de liga**")
        st.dataframe(podium, use_container_width=True, hide_index=True)

    table = list(league.get("table") or [])
    if table:
        st.markdown("**Tabla final / actual**")
        st.dataframe(table, use_container_width=True, hide_index=True)

    history = list(league.get("history") or [])
    if history:
        st.markdown("**Historial por tramo**")
        for tramo_data in history:
            st.caption(f"Tramo {tramo_data.get('tramo')}")
            st.dataframe(tramo_data.get("rows") or [], use_container_width=True, hide_index=True)
            up = list(tramo_data.get("up") or [])
            down = list(tramo_data.get("down") or [])
            if up or down:
                st.caption(
                    "Ascensos: "
                    + (", ".join(up) if up else "-")
                    + " | Descensos: "
                    + (", ".join(down) if down else "-")
                )

    swiss_final = [value for value in list(swiss.get("final") or []) if value]
    if swiss_final:
        st.caption("Final Swiss: " + " vs ".join(swiss_final))

    doubles_final = [value for value in list(doubles.get("final") or []) if value]
    if doubles_final:
        st.caption("Final Dobles: " + " vs ".join(doubles_final))


def render_season_archive_section() -> None:
    st.subheader("Archivo de temporada")
    st.caption("Guarda una fotografia persistente de la temporada actual antes de resetear o al cerrar el circuito.")

    default_name = st.session_state.get("season_archive_name") or f"Temporada {datetime.now().strftime('%Y-%m-%d')}"
    col_name, col_action = st.columns([2.2, 1])
    with col_name:
        season_name = st.text_input("Nombre del archivo", value=default_name, key="season_archive_name")
    with col_action:
        st.write("")
        st.write("")
        if st.button("Archivar temporada", use_container_width=True, key="season_archive_save"):
            entry = archive_current_season(season_name)
            st.success(f"Temporada archivada: {entry.get('name')}")
            st.rerun()

    archive = _load_archive()
    if not archive:
        st.info("Aun no hay temporadas archivadas.")
        return

    for entry in archive:
        title = str(entry.get("name") or "Temporada")
        with st.expander(title, expanded=False):
            _render_archive_entry(entry)
