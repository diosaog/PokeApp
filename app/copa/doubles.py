from __future__ import annotations

import base64
import json
import mimetypes
import unicodedata
from pathlib import Path

import streamlit as st

from storage import settings_get, settings_set
from utils import USERS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGO_DIR_REL = Path("assets") / "copa_dobles" / "team_logos"
LOGO_DIR = PROJECT_ROOT / LOGO_DIR_REL
LOGO_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg")
RESULT_LABELS = {
    "Sin jugar": (None, None),
    "2-0": (2, 0),
    "2-1": (2, 1),
    "1-2": (1, 2),
    "0-2": (0, 2),
}


def _ensure_logo_dir() -> None:
    try:
        LOGO_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _slug(text: str) -> str:
    t = unicodedata.normalize("NFD", str(text or "").strip().lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    out: list[str] = []
    prev_dash = False
    for ch in t:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def _logo_for_team(team_name: str) -> str | None:
    _ensure_logo_dir()
    slug = _slug(team_name)
    if not slug:
        return None
    for ext in LOGO_EXTS:
        candidate = LOGO_DIR / f"{slug}{ext}"
        if candidate.exists():
            return str(candidate)
    try:
        for candidate in LOGO_DIR.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in LOGO_EXTS and _slug(candidate.stem) == slug:
                return str(candidate)
    except Exception:
        pass
    return None


def _logo_bytes_for_team(team_name: str) -> bytes | None:
    logo_path = _logo_for_team(team_name)
    if not logo_path:
        return None
    try:
        return Path(logo_path).read_bytes()
    except Exception:
        return None


def _logo_data_uri_for_team(team_name: str) -> str | None:
    logo_path = _logo_for_team(team_name)
    logo_bytes = _logo_bytes_for_team(team_name)
    if not logo_path or not logo_bytes:
        return None
    try:
        mime = mimetypes.guess_type(logo_path)[0] or "image/png"
        encoded = base64.b64encode(logo_bytes).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


def _empty_state() -> dict:
    return {
        "configured": False,
        "team_count": 0,
        "teams": [],
        "rounds": [],
        "final": {"team_a": None, "team_b": None, "score_a": None, "score_b": None},
    }


def _ensure_state() -> None:
    if "copa_dobles" not in st.session_state or not isinstance(st.session_state.copa_dobles, dict):
        st.session_state.copa_dobles = _empty_state()
    S = st.session_state.copa_dobles
    S.setdefault("configured", False)
    S.setdefault("team_count", 0)
    S.setdefault("teams", [])
    S.setdefault("rounds", [])
    S.setdefault("final", {"team_a": None, "team_b": None, "score_a": None, "score_b": None})


def _persist_state() -> None:
    try:
        settings_set("copa_dobles_state", json.dumps(st.session_state.get("copa_dobles", _empty_state()), ensure_ascii=False))
    except Exception:
        pass


def _restore_state() -> None:
    try:
        raw = settings_get("copa_dobles_state")
        if not raw:
            return
        obj = json.loads(raw)
        if isinstance(obj, dict):
            st.session_state.copa_dobles = obj
    except Exception:
        pass


def _team_map(S: dict) -> dict[str, dict]:
    return {str(team.get("id")): team for team in S.get("teams", []) if team.get("id")}


def _generate_round_robin(team_ids: list[str]) -> list[dict]:
    if len(team_ids) < 2:
        return []
    rotation: list[str | None] = list(team_ids)
    if len(rotation) % 2 == 1:
        rotation.append(None)
    total = len(rotation)
    rounds: list[dict] = []
    for round_idx in range(total - 1):
        matches: list[dict] = []
        half = total // 2
        for idx in range(half):
            a = rotation[idx]
            b = rotation[total - 1 - idx]
            if a is None or b is None:
                continue
            if round_idx % 2 == 1:
                a, b = b, a
            matches.append({"team_a": a, "team_b": b, "score_a": None, "score_b": None})
        rounds.append({"round": round_idx + 1, "matches": matches})
        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
    return rounds


def _valid_bo3(score_a, score_b) -> bool:
    try:
        a = int(score_a)
        b = int(score_b)
    except Exception:
        return False
    return (a, b) in {(2, 0), (2, 1), (1, 2), (0, 2)}


def _label_for_score(score_a, score_b) -> str:
    for label, pair in RESULT_LABELS.items():
        if pair == (score_a, score_b):
            return label
    return "Sin jugar"


def _head_to_head_winner(S: dict, team_a: str, team_b: str) -> str | None:
    for round_data in S.get("rounds", []):
        for match in round_data.get("matches", []):
            a = match.get("team_a")
            b = match.get("team_b")
            if {a, b} != {team_a, team_b}:
                continue
            score_a = match.get("score_a")
            score_b = match.get("score_b")
            if not _valid_bo3(score_a, score_b):
                return None
            return a if int(score_a) > int(score_b) else b
    return None


def _standings(S: dict) -> list[dict]:
    teams = S.get("teams", [])
    rows: dict[str, dict] = {}
    for team in teams:
        team_id = str(team.get("id"))
        rows[team_id] = {
            "id": team_id,
            "team": team.get("name") or team_id,
            "members": list(team.get("members") or []),
            "played": 0,
            "series_wins": 0,
            "series_losses": 0,
            "game_wins": 0,
            "game_losses": 0,
            "game_diff": 0,
        }

    for round_data in S.get("rounds", []):
        for match in round_data.get("matches", []):
            team_a = str(match.get("team_a"))
            team_b = str(match.get("team_b"))
            score_a = match.get("score_a")
            score_b = match.get("score_b")
            if not _valid_bo3(score_a, score_b):
                continue
            a = rows.get(team_a)
            b = rows.get(team_b)
            if not a or not b:
                continue
            score_a = int(score_a)
            score_b = int(score_b)
            a["played"] += 1
            b["played"] += 1
            a["game_wins"] += score_a
            a["game_losses"] += score_b
            b["game_wins"] += score_b
            b["game_losses"] += score_a
            if score_a > score_b:
                a["series_wins"] += 1
                b["series_losses"] += 1
            else:
                b["series_wins"] += 1
                a["series_losses"] += 1

    for row in rows.values():
        row["game_diff"] = int(row["game_wins"]) - int(row["game_losses"])

    ordered = sorted(
        rows.values(),
        key=lambda row: (-row["series_wins"], -row["game_diff"], -row["game_wins"], row["team"].lower()),
    )

    ranking: list[dict] = []
    idx = 0
    while idx < len(ordered):
        current = ordered[idx]
        group = [current]
        idx += 1
        while idx < len(ordered):
            other = ordered[idx]
            same_key = (
                other["series_wins"] == current["series_wins"]
                and other["game_diff"] == current["game_diff"]
                and other["game_wins"] == current["game_wins"]
            )
            if not same_key:
                break
            group.append(other)
            idx += 1
        if len(group) == 2:
            winner = _head_to_head_winner(S, group[0]["id"], group[1]["id"])
            if winner == group[1]["id"]:
                group.reverse()
        elif len(group) > 2:
            group = sorted(group, key=lambda row: row["team"].lower())
        ranking.extend(group)
    return ranking


def _league_complete(S: dict) -> bool:
    rounds = S.get("rounds", [])
    if not rounds:
        return False
    for round_data in rounds:
        for match in round_data.get("matches", []):
            if not _valid_bo3(match.get("score_a"), match.get("score_b")):
                return False
    return True


def _sync_final(S: dict) -> bool:
    standings = _standings(S)
    final = S.setdefault("final", {"team_a": None, "team_b": None, "score_a": None, "score_b": None})
    if len(standings) < 2 or not _league_complete(S):
        changed = any(final.get(k) is not None for k in ("team_a", "team_b", "score_a", "score_b"))
        S["final"] = {"team_a": None, "team_b": None, "score_a": None, "score_b": None}
        return changed
    team_a = standings[0]["id"]
    team_b = standings[1]["id"]
    if final.get("team_a") != team_a or final.get("team_b") != team_b:
        S["final"] = {"team_a": team_a, "team_b": team_b, "score_a": None, "score_b": None}
        return True
    return False


def _ensure_doubles_css() -> None:
    st.markdown(
        """
        <style>
        .doubles-logo-wrap {
          width: 170px;
          height: 170px;
          display:flex;
          align-items:center;
          justify-content:center;
          margin: 0 auto;
          border-radius: 14px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
          padding: 12px;
        }
        .doubles-logo-wrap.compact {
          width: 118px;
          height: 118px;
          padding: 10px;
          border-radius: 12px;
        }
        .doubles-logo-img {
          max-width: 100%;
          max-height: 100%;
          width: auto;
          height: auto;
          object-fit: contain;
          display: block;
          image-rendering: -webkit-optimize-contrast;
          filter: drop-shadow(0 3px 10px rgba(0,0,0,0.28));
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_team_card(team: dict, *, compact: bool = False) -> None:
    name = team.get("name") or "-"
    members = list(team.get("members") or [])
    logo = _logo_for_team(name)
    logo_uri = _logo_data_uri_for_team(name)
    if compact:
        if logo_uri:
            st.markdown(
                (
                    "<div class='doubles-logo-wrap compact'>"
                    f"<img class='doubles-logo-img' src='{logo_uri}' alt='logo {name}'/>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        st.markdown(f"**{name}**")
        st.caption(" / ".join(members) if members else "Sin miembros")
        return
    with st.container(border=True):
        cols = st.columns([1, 2])
        with cols[0]:
            if logo_uri:
                st.markdown(
                    (
                        "<div class='doubles-logo-wrap'>"
                        f"<img class='doubles-logo-img' src='{logo_uri}' alt='logo {name}'/>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Sin logo")
        with cols[1]:
            st.markdown(f"**{name}**")
            st.caption(" + ".join(members) if members else "Sin miembros")
            slug = _slug(name)
            if slug:
                st.caption(f"Logo: `{slug}.png/.jpg/.jpeg/.webp/.svg`")


def _render_configurator(S: dict) -> None:
    all_players = list(USERS.keys())
    max_teams = max(2, len(all_players) // 2)
    current_count = int(S.get("team_count") or min(5, max_teams))
    current_count = max(2, min(current_count, max_teams))

    st.info("Crea equipos de 2 jugadores. El logo se carga automaticamente desde la carpeta de logos segun el nombre del equipo.")
    st.caption(f"Carpeta de logos: `{LOGO_DIR_REL}`")

    with st.form("copa_dobles_setup"):
        team_count = int(
            st.number_input(
                "Numero de equipos",
                min_value=2,
                max_value=max_teams,
                value=current_count,
                step=1,
            )
        )
        existing = list(S.get("teams") or [])
        team_rows: list[dict] = []
        for idx in range(team_count):
            default_name = existing[idx].get("name") if idx < len(existing) else f"Equipo {idx + 1}"
            default_members = list(existing[idx].get("members") or []) if idx < len(existing) else all_players[idx * 2: idx * 2 + 2]
            st.markdown(f"**Equipo {idx + 1}**")
            name = st.text_input("Nombre del equipo", value=default_name, key=f"doubles_team_name_{idx}")
            members = st.multiselect(
                "Entrenadores",
                all_players,
                default=default_members,
                max_selections=2,
                key=f"doubles_team_members_{idx}",
            )
            team_rows.append({"id": f"team_{idx + 1}", "name": name, "members": members})

        submitted = st.form_submit_button("Crear Copa Dobles", type="primary")
        if submitted:
            errors: list[str] = []
            seen_players: dict[str, str] = {}
            seen_names: set[str] = set()
            for team in team_rows:
                name = str(team.get("name") or "").strip()
                members = list(team.get("members") or [])
                if not name:
                    errors.append("Todos los equipos deben tener nombre.")
                name_key = name.lower()
                if name_key in seen_names:
                    errors.append("Los nombres de equipo deben ser unicos.")
                seen_names.add(name_key)
                if len(members) != 2:
                    errors.append(f"El equipo '{name or '-'}' debe tener exactamente 2 entrenadores.")
                if len(set(members)) != len(members):
                    errors.append(f"El equipo '{name or '-'}' no puede repetir entrenador.")
                for member in members:
                    if member in seen_players:
                        errors.append(f"El entrenador {member} esta repetido entre '{seen_players[member]}' y '{name or '-'}'.")
                    else:
                        seen_players[member] = name or f"Equipo {team.get('id')}"

            if errors:
                for error in dict.fromkeys(errors):
                    st.error(error)
                return

            team_ids = [str(team["id"]) for team in team_rows]
            S["configured"] = True
            S["team_count"] = team_count
            S["teams"] = [{"id": team["id"], "name": str(team["name"]).strip(), "members": list(team["members"])} for team in team_rows]
            S["rounds"] = _generate_round_robin(team_ids)
            S["final"] = {"team_a": None, "team_b": None, "score_a": None, "score_b": None}
            _persist_state()
            st.success("Copa Dobles creada.")
            st.rerun()


def page_copa() -> None:
    _ensure_logo_dir()
    _restore_state()
    _ensure_state()
    _ensure_doubles_css()
    S = st.session_state.copa_dobles

    st.subheader("Copa Dobles")
    st.caption("Liga todos contra todos entre equipos de 2 jugadores, con final entre los 2 mejores.")

    if not S.get("configured"):
        _render_configurator(S)
        return

    changed = _sync_final(S)
    if changed:
        _persist_state()

    teams_by_id = _team_map(S)
    standings = _standings(S)
    complete = _league_complete(S)

    top_a, top_b = st.columns([3, 1])
    with top_a:
        st.info(f"Carpeta de logos: `{LOGO_DIR_REL}`")
    with top_b:
        if st.button("Resetear Copa Dobles", use_container_width=True):
            st.session_state.copa_dobles = _empty_state()
            _persist_state()
            st.success("Copa Dobles reiniciada.")
            st.rerun()

    st.markdown("---")
    st.subheader("Equipos")
    team_cols = st.columns(min(2, max(1, len(S.get("teams", [])))))
    for idx, team in enumerate(S.get("teams", [])):
        with team_cols[idx % len(team_cols)]:
            _render_team_card(team)

    st.markdown("---")
    st.subheader("Liga Regular")
    st.caption("Resultados validos de Bo3: `2-0`, `2-1`, `1-2` o `0-2`.")
    for round_data in S.get("rounds", []):
        round_no = int(round_data.get("round") or 0)
        with st.form(f"copa_dobles_round_{round_no}"):
            st.markdown(f"**Jornada {round_no}**")
            if not round_data.get("matches"):
                st.caption("Sin enfrentamientos en esta jornada.")
            for match_idx, match in enumerate(round_data.get("matches", [])):
                team_a = teams_by_id.get(str(match.get("team_a")), {"name": match.get("team_a")})
                team_b = teams_by_id.get(str(match.get("team_b")), {"name": match.get("team_b")})
                current_label = _label_for_score(match.get("score_a"), match.get("score_b"))
                cols = st.columns([2, 1, 2])
                with cols[0]:
                    st.markdown(f"**{team_a.get('name') or '-'}**")
                    st.caption(" + ".join(team_a.get("members") or []))
                with cols[1]:
                    choice = st.selectbox(
                        "Resultado",
                        list(RESULT_LABELS.keys()),
                        index=list(RESULT_LABELS.keys()).index(current_label),
                        key=f"doubles_result_{round_no}_{match_idx}",
                        label_visibility="collapsed",
                    )
                with cols[2]:
                    st.markdown(f"**{team_b.get('name') or '-'}**")
                    st.caption(" + ".join(team_b.get("members") or []))
            if st.form_submit_button(f"Guardar jornada {round_no}"):
                for match_idx, match in enumerate(round_data.get("matches", [])):
                    score_a, score_b = RESULT_LABELS[st.session_state[f"doubles_result_{round_no}_{match_idx}"]]
                    match["score_a"] = score_a
                    match["score_b"] = score_b
                _persist_state()
                st.success(f"Jornada {round_no} guardada.")
                st.rerun()

    st.markdown("---")
    st.subheader("Clasificacion")
    st.caption("Desempates actuales: series ganadas, diferencia de juegos, juegos ganados y directo si el empate exacto es entre 2 equipos.")
    if standings:
        rows = []
        for pos, row in enumerate(standings, start=1):
            rows.append(
                {
                    "Pos": pos,
                    "Equipo": row["team"],
                    "Entrenadores": " + ".join(row["members"]),
                    "PJ": row["played"],
                    "Series": f"{row['series_wins']}-{row['series_losses']}",
                    "Juegos": f"{row['game_wins']}-{row['game_losses']}",
                    "Diff": row["game_diff"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("Aun no hay equipos configurados.")

    if standings:
        st.markdown("---")
        st.subheader("Top 2")
        finalist_cols = st.columns(2)
        for idx, finalist in enumerate(standings[:2]):
            with finalist_cols[idx]:
                _render_team_card(teams_by_id.get(finalist["id"], {}), compact=True)
                st.caption(f"Posicion actual: {idx + 1}")

    st.markdown("---")
    st.subheader("Final")
    if not complete:
        st.caption("La final se desbloquea cuando toda la liga regular tenga resultados.")
        return

    final = S.get("final", {})
    final_a = teams_by_id.get(str(final.get("team_a")))
    final_b = teams_by_id.get(str(final.get("team_b")))
    if not final_a or not final_b:
        st.caption("No se han podido determinar los finalistas.")
        return

    cols = st.columns([2, 1, 2])
    with cols[0]:
        _render_team_card(final_a, compact=True)
    with cols[1]:
        st.markdown("### VS")
    with cols[2]:
        _render_team_card(final_b, compact=True)

    with st.form("copa_dobles_final"):
        final_label = _label_for_score(final.get("score_a"), final.get("score_b"))
        choice = st.selectbox("Resultado de la final", list(RESULT_LABELS.keys()), index=list(RESULT_LABELS.keys()).index(final_label))
        if st.form_submit_button("Guardar final", type="primary"):
            score_a, score_b = RESULT_LABELS[choice]
            S["final"]["score_a"] = score_a
            S["final"]["score_b"] = score_b
            _persist_state()
            st.success("Final guardada.")
            st.rerun()

    if _valid_bo3(final.get("score_a"), final.get("score_b")):
        champion = final_a if int(final["score_a"]) > int(final["score_b"]) else final_b
        st.success(f"Campeon de la Copa Dobles: {champion.get('name')}")
