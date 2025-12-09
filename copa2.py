from __future__ import annotations
from typing import List, Optional
import random
import streamlit as st
from utils import USERS


# ===========================
# Eliminación directa (Bo3)
# ===========================

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
        pool.append(None)  # bye
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
        }


def _render_bracket(state) -> None:
    rounds: List[List[dict]] = state.get("rounds", [])
    if not rounds:
        return
    css = """
    <style>
    .bracket { display:flex; gap:22px; align-items:flex-start; overflow-x:auto; padding: 6px 0 2px; }
    .round-col { display:flex; flex-direction:column; gap:18px; }
    .round-title { font-weight:700; opacity:.95; margin: 4px 0 6px; }
    .match { width: 260px; padding:10px 12px; border-radius:12px; border:1px solid rgba(255,255,255,0.12);
             background: rgba(255,255,255,0.03); position:relative; }
    .player { display:flex; justify-content:space-between; align-items:center; padding:4px 0; }
    .player.w { font-weight:700; color:#e6edf3; }
    .score { opacity:.8; font-variant-numeric: tabular-nums; }
    /* Conector horizontal sencillo */
    .match:after { content:""; position:absolute; right:-22px; top:50%; width:22px; height:2px; background: rgba(255,255,255,0.2); }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    cols = st.columns(len(rounds))
    for idx, col in enumerate(cols):
        with col:
            title = {0: "Octavos", 1: "Cuartos", 2: "Semifinal", 3: "Final"}.get(idx, f"Ronda {idx+1}")
            st.markdown(f"<div class='round-title'>{title}</div>", unsafe_allow_html=True)
            st.markdown("<div class='round-col'>", unsafe_allow_html=True)
            for mi, m in enumerate(rounds[idx]):
                p1 = m.get("p1") or "-"
                p2 = m.get("p2") or "-"
                w = m.get("winner")
                score = m.get("score") or ""
                st.markdown("<div class='match'>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='player {'w' if w == p1 else ''}'><span>{p1}</span><span class='score'>{(score if w==p1 else '')}</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='player {'w' if w == p2 else ''}'><span>{p2}</span><span class='score'>{(score if w==p2 else '')}</span></div>",
                    unsafe_allow_html=True,
                )
                if (m.get('p1') and m.get('p2')):
                    with st.expander("Registrar/editar resultado", expanded=False):
                        s1, s2 = 0, 0
                        try:
                            if isinstance(score, str) and '-' in score:
                                a, b = score.split('-', 1)
                                s1, s2 = int(a.strip()), int(b.strip())
                        except Exception:
                            s1, s2 = 0, 0
                        c1, c2, c3 = st.columns([1,1,1])
                        with c1:
                            v1 = st.number_input(f"{p1}", min_value=0, max_value=99, step=1, value=int(s1), key=f"sc_{idx}_{mi}_a")
                        with c2:
                            v2 = st.number_input(f"{p2}", min_value=0, max_value=99, step=1, value=int(s2), key=f"sc_{idx}_{mi}_b")
                        with c3:
                            if st.button("Guardar", key=f"save_{idx}_{mi}"):
                                if int(v1) == int(v2):
                                    st.warning("Empate no vlido; ajusta los marcadores.")
                                else:
                                    m['score'] = f"{int(v1)}-{int(v2)}"
                                    m['winner'] = p1 if int(v1) > int(v2) else p2
                                    st.success("Resultado guardado.")
                                    st.rerun()
                            if st.button("Limpiar", key=f"clear_{idx}_{mi}"):
                                m['score'] = None
                                m['winner'] = None
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
    st.header("Copa - Torneo (Bo3)")
    _ensure_elim_state()
    S = st.session_state.elim

    # Setup inicial
    if not S.get("rounds"):
        st.subheader("Configurar torneo")
        all_players = list(USERS.keys())
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
                    st.success("Bracket creado.")
                    st.rerun()
        with c2:
            if st.button("Resetear configuración"):
                st.session_state.pop("elim")
                st.rerun()
        return

    # Controles superiores
    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Resetear torneo"):
            st.session_state.pop("elim")
            st.success("Torneo reiniciado.")
            st.rerun()
    with colB:
        st.caption(f"Rondas: {len(S['rounds'])}")

    # Mostrar bracket
    _render_bracket(S)

    # Ronda actual
    rnd_idx = int(S.get("current_round", 0))
    rounds: List[List[dict]] = S.get("rounds", [])
    if rnd_idx >= len(rounds):
        last = rounds[-1]
        if last and last[0].get("winner"):
            st.success(f"Campeón: {last[0]['winner']}")
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
                st.rerun()
            else:
                nxt = _round_from_players(next_players)
                if rnd_idx + 1 < len(S["rounds"]):
                    S["rounds"][rnd_idx + 1] = nxt
                else:
                    S["rounds"].append(nxt)
                S["current_round"] = rnd_idx + 1
                st.rerun()

