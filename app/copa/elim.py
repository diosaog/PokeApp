from __future__ import annotations

import html as _html
import json
import random
import time
from typing import List, Optional

import streamlit as st

from app.copa.styles import render_copa_metrics, render_copa_section, render_copa_styles
from utils import active_users, users_with_retired_last
from storage import settings_get, settings_set


def _next_pow2(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def _seed_players(players: List[str], *, shuffle: bool = True) -> List[Optional[str]]:
    pool = list(players)
    if shuffle:
        random.shuffle(pool)
    size = _next_pow2(len(pool))
    while len(pool) < size:
        pool.append(None)
    return pool


def _round_from_players(players: List[Optional[str]]) -> List[dict]:
    matches = []
    for i in range(0, len(players), 2):
        a = players[i]
        b = players[i + 1] if i + 1 < len(players) else None
        m = {"p1": a, "p2": b, "winner": None, "score": None}
        if a is None and b is not None:
            m["winner"] = b
            m["score"] = "BYE"
        elif b is None and a is not None:
            m["winner"] = a
            m["score"] = "BYE"
        matches.append(m)
    return matches


def _advance_players(prev_round: List[dict]) -> List[Optional[str]]:
    out: List[Optional[str]] = []
    for m in prev_round:
        w = m.get("winner")
        out.append(w)
    return out


def _ensure_elim_state() -> None:
    if "elim" not in st.session_state:
        st.session_state.elim = {
            "players": [],
            "rounds": [],
            "current_round": 0,
            "hall_run_id": None,
        }
    st.session_state.elim.setdefault("hall_run_id", None)


def _persist_elim_state() -> None:
    try:
        S = st.session_state.get("elim")
        if not S:
            return
        data = {
            "players": S.get("players", []),
            "rounds": S.get("rounds", []),
            "current_round": S.get("current_round", 0),
            "hall_run_id": S.get("hall_run_id"),
        }
        settings_set("copa_elim_state", json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def _restore_elim_state() -> None:
    try:
        raw = settings_get("copa_elim_state")
        if not raw:
            return
        obj = json.loads(raw)
        st.session_state.elim = {
            "players": obj.get("players", []),
            "rounds": obj.get("rounds", []),
            "current_round": obj.get("current_round", 0),
            "hall_run_id": obj.get("hall_run_id"),
        }
    except Exception:
        pass


def _new_hall_run_id() -> str:
    return f"elim:{int(time.time() * 1000)}"


def _sync_hall_of_fame_silent() -> None:
    try:
        from app.interfaz.hall_of_fame import sync_hall_of_fame_from_sources

        sync_hall_of_fame_from_sources()
    except Exception:
        pass


def _player_row_html(player: str, score: str, *, winner: bool) -> str:
    cls = "cup-player is-winner" if winner else "cup-player"
    return (
        f"<div class='{cls}'>"
        f"<span>{_html.escape(str(player or '-'))}</span>"
        f"<span class='cup-score'>{_html.escape(str(score or ''))}</span>"
        "</div>"
    )


def _render_bracket(state) -> None:
    rounds: List[List[dict]] = state.get("rounds", [])
    if not rounds:
        return

    cols = st.columns(len(rounds))
    for idx, col in enumerate(cols):
        with col:
            title = {0: "Octavos", 1: "Cuartos", 2: "Semifinal", 3: "Final"}.get(idx, f"Ronda {idx+1}")
            safe_title = _html.escape(title)
            st.markdown(f"<div class='cup-round-title'>{safe_title}</div>", unsafe_allow_html=True)
            st.markdown("<div class='cup-round-col'>", unsafe_allow_html=True)
            for mi, m in enumerate(rounds[idx]):
                p1 = m.get("p1") or "-"
                p2 = m.get("p2") or "-"
                w = m.get("winner")
                score = m.get("score") or ""
                st.markdown("<div class='cup-match'>", unsafe_allow_html=True)
                st.markdown(
                    _player_row_html(p1, score if w == p1 else "", winner=w == p1),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    _player_row_html(p2, score if w == p2 else "", winner=w == p2),
                    unsafe_allow_html=True,
                )
                if (m.get("p1") and m.get("p2")):
                    with st.expander("Registrar/editar resultado", expanded=False):
                        s1, s2 = 0, 0
                        try:
                            if isinstance(score, str) and "-" in score:
                                a, b = score.split("-", 1)
                                s1, s2 = int(a.strip()), int(b.strip())
                        except Exception:
                            s1, s2 = 0, 0
                        c1, c2, c3 = st.columns([1, 1, 1])
                        with c1:
                            v1 = st.number_input(f"{p1}", min_value=0, max_value=99, step=1, value=int(s1), key=f"sc_{idx}_{mi}_a")
                        with c2:
                            v2 = st.number_input(f"{p2}", min_value=0, max_value=99, step=1, value=int(s2), key=f"sc_{idx}_{mi}_b")
                        with c3:
                            if st.button("Guardar", key=f"save_{idx}_{mi}"):
                                if int(v1) == int(v2):
                                    st.warning("Empate no valido; ajusta los marcadores.")
                                else:
                                    m["score"] = f"{int(v1)}-{int(v2)}"
                                    m["winner"] = p1 if int(v1) > int(v2) else p2
                                    st.success("Resultado guardado.")
                                    st.rerun()
                            if st.button("Limpiar", key=f"clear_{idx}_{mi}"):
                                m["score"] = None
                                m["winner"] = None
                                st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


def _all_reported(round_matches: List[dict]) -> bool:
    for m in round_matches:
        a, b = m.get("p1"), m.get("p2")
        if a and b and not m.get("winner"):
            return False
    return True


def page_copa() -> None:
    render_copa_styles()
    render_copa_section("Eliminatoria Bo3", "Bracket directo con resultados editables y avance por ronda.")
    _restore_elim_state()
    _ensure_elim_state()
    S = st.session_state.elim

    if not S.get("rounds"):
        render_copa_section("Configurar torneo", "Selecciona participantes y crea el bracket.")
        all_players = users_with_retired_last(active_users())
        default_sel = all_players[:8] if len(all_players) >= 8 else all_players
        sel = st.multiselect("Participantes", all_players, default=default_sel)
        shuffle = st.toggle("Sorteo aleatorio", value=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Crear bracket", type="primary", use_container_width=True):
                if len(sel) < 2:
                    st.error("Selecciona al menos 2 jugadores.")
                else:
                    seeded = _seed_players(sel, shuffle=shuffle)
                    first_round = _round_from_players(seeded)
                    S["players"] = sel
                    S["rounds"] = [first_round]
                    S["current_round"] = 0
                    S["hall_run_id"] = _new_hall_run_id()
                    _persist_elim_state()
                    st.success("Bracket creado.")
                    st.rerun()
        with c2:
            if st.button("Resetear configuracion"):
                st.session_state.elim = {
                    "players": [],
                    "rounds": [],
                    "current_round": 0,
                    "hall_run_id": None,
                }
                _persist_elim_state()
                st.rerun()
        return

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Resetear torneo"):
            st.session_state.elim = {
                "players": [],
                "rounds": [],
                "current_round": 0,
                "hall_run_id": None,
            }
            _persist_elim_state()
            st.success("Torneo reiniciado.")
            st.rerun()
    with colB:
        st.caption(f"Rondas: {len(S['rounds'])}")

    render_copa_metrics(
        [
            ("Participantes", str(len(S.get("players") or [])), None),
            ("Rondas", str(len(S.get("rounds") or [])), None),
            ("Ronda activa", str(int(S.get("current_round", 0)) + 1), None),
            ("Formato", "Bo3", None),
        ]
    )

    _render_bracket(S)

    rnd_idx = int(S.get("current_round", 0))
    rounds: List[List[dict]] = S.get("rounds", [])
    if rnd_idx >= len(rounds):
        last = rounds[-1]
        if last and last[0].get("winner"):
            st.success(f"Campeon: {last[0]['winner']}")
        return

    cur = rounds[rnd_idx]
    any_open = any((m.get("p1") and m.get("p2")) for m in cur)
    if any_open and st.button("Cerrar ronda y avanzar", type="primary"):
        if not _all_reported(cur):
            st.error("Faltan resultados por registrar.")
        else:
            next_players = _advance_players(cur)
            remaining = [p for p in next_players if p]
            if len(remaining) <= 1:
                S["current_round"] = rnd_idx + 1
                _persist_elim_state()
                _sync_hall_of_fame_silent()
                st.rerun()
            else:
                nxt = _round_from_players(next_players)
                if rnd_idx + 1 < len(S["rounds"]):
                    S["rounds"][rnd_idx + 1] = nxt
                else:
                    S["rounds"].append(nxt)
                S["current_round"] = rnd_idx + 1
                _persist_elim_state()
                st.rerun()
