from __future__ import annotations
import random
import streamlit as st
from utils import USERS


def _ensure_swiss_state():
    if "swiss" not in st.session_state:
        players = list(USERS.keys())
        st.session_state.swiss = {
            "players": players[:8],
            "round": 1,
            "max_rounds": 7,
            "wins": {p: 0 for p in players[:8]},
            "losses": {p: 0 for p in players[:8]},
            "byes": {p: 0 for p in players[:8]},
            "results": {},
            "current": {"pairs": [], "bye": None},
        }


def _already_played(S, a, b) -> bool:
    for _, lst in S.get("results", {}).items():
        for m in lst:
            if {m.get("p1"), m.get("p2")} == {a, b}:
                return True
    return False


def _eligible_players(S) -> list[str]:
    return list(S.get("players", []))


def _choose_bye(S, players: list[str]) -> str | None:
    if len(players) % 2 == 0:
        return None
    byes = S["byes"]
    candidates = [p for p in players if byes.get(p, 0) == 0]
    if not candidates:
        candidates = list(players)
    return random.choice(candidates)


def _swiss_generate_pairings(S) -> tuple[list[tuple[str, str]], str | None]:
    players = _eligible_players(S)
    if not players:
        return [], None
    bye = _choose_bye(S, players)
    pool = [p for p in players if p != bye]

    wins = S["wins"]
    groups: dict[int, list[str]] = {}
    for p in pool:
        groups.setdefault(int(wins.get(p, 0)), []).append(p)
    for g in groups.values():
        random.shuffle(g)

    pairs: list[tuple[str, str]] = []
    carry: list[str] = []
    for w in sorted(groups.keys(), reverse=True):
        bucket = carry + groups[w]
        carry = []
        while len(bucket) >= 2:
            a = bucket.pop(0)
            idx = None
            for i, b in enumerate(bucket):
                if not _already_played(S, a, b):
                    idx = i
                    break
            b = bucket.pop(0) if idx is None else bucket.pop(idx)
            pairs.append((a, b))
        if bucket:
            carry = bucket
    if carry:
        last = carry[0]
        if pairs:
            a, b = pairs.pop()
            pairs.append((a, last))
            bye = bye or b
        else:
            bye = bye or last
    return pairs, bye


def _apply_round_results(S, pairs, winners, bye_player):
    rnd = S["round"]
    wins = S["wins"]
    losses = S["losses"]
    res_list = []
    for (a, b), w in zip(pairs, winners):
        if w == a:
            wins[a] += 1
            losses[b] += 1
        else:
            wins[b] += 1
            losses[a] += 1
        res_list.append({"p1": a, "p2": b, "winner": w})
    if bye_player:
        wins[bye_player] += 1
        res_list.append({"p1": bye_player, "p2": None, "winner": bye_player})
    S["results"].setdefault(rnd, res_list)
    S["round"] += 1
    S["current"] = {"pairs": [], "bye": None}


def page_copa() -> None:
    _ensure_swiss_state()
    st.subheader("Sistema suizo")
    S = st.session_state.swiss

    # Configuración
    with st.expander("Configurar", expanded=False):
        all_players = list(USERS.keys())
        sel = st.multiselect("Jugadores", all_players, default=S.get("players", []))
        if st.button("Aplicar jugadores"):
            S["players"] = sel
            for p in sel:
                S["wins"].setdefault(p, 0)
                S["losses"].setdefault(p, 0)
            st.rerun()

    # Tabla
    wins, losses = S["wins"], S["losses"]
    tabla = sorted(S["players"], key=lambda p: (wins.get(p, 0), p), reverse=True)
    rows = [{"Jugador": p, "W": wins.get(p, 0), "L": losses.get(p, 0)} for p in tabla]
    st.dataframe(rows, use_container_width=True)

    # Emparejamientos
    st.markdown("---")
    st.subheader(f"Ronda {S['round']}")
    if not S["current"]["pairs"]:
        pairs, bye = _swiss_generate_pairings(S)
        S["current"] = {"pairs": pairs, "bye": bye}

    cur = S["current"]
    if cur["pairs"]:
        winners = []
        for idx, (a, b) in enumerate(cur["pairs"], start=1):
            pick = st.radio(f"{a} vs {b}", options=[a, b], horizontal=True, key=f"swiss_pick_{S['round']}_{idx}")
            winners.append(pick)
        if cur["bye"]:
            st.info(f"Bye: {cur['bye']}")
        if st.button("Finalizar ronda"):
            if len(winners) == len(cur["pairs"]):
                _apply_round_results(S, cur["pairs"], winners, cur["bye"])
                st.rerun()
            else:
                st.error("Marca el ganador en todos los enfrentamientos.")
    else:
        st.caption("Sin emparejamientos activos.")

