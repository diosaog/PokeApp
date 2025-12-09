# -*- coding: utf-8 -*-
from __future__ import annotations
import random
import streamlit as st
from utils import USERS


# ---------- Estado y helpers ----------
def _ensure_swiss_state():
    if "swiss" not in st.session_state:
        st.session_state.swiss = {
            "players": [],
            "round": 1,
            "max_rounds": 7,
            "wins": {},
            "losses": {},
            "byes": {},
            "history": [],
            "results": {},
            "qualified": {},
            "eliminated": set(),
            "current": {"pairs": [], "bye": None},
            "manual": False,
            "topcut": None,
            "configured": False,
        }


def _swiss_buchholz(S) -> dict:
    wins = S["wins"]
    bh = {p: 0 for p in S["players"]}
    for _, lst in S.get("results", {}).items():
        for m in lst:
            p1, p2 = m["p1"], m["p2"]
            if p2:
                bh[p1] += wins[p2]
                bh[p2] += wins[p1]
    return bh


def _already_played(S, a, b) -> bool:
    for _, lst in S.get("results", {}).items():
        for m in lst:
            if {m["p1"], m["p2"]} == {a, b}:
                return True
    return False


def _eligible_players(S) -> list[str]:
    return [p for p in S["players"] if p not in S["eliminated"] and p not in S["qualified"]]


def _choose_bye(S, players: list[str]) -> str | None:
    """Selecciona el bye de forma aleatoria entre jugadores que no hayan recibido bye aún.
    Si no hay ninguno disponible (caso extremo), avisa y elige aleatorio entre todos.
    """
    if len(players) % 2 == 0:
        return None
    byes = S["byes"]
    candidates = [p for p in players if byes.get(p, 0) == 0]
    if not candidates:
        try:
            st.error("No quedan jugadores sin bye. Revisa la configuracin o el número de rondas.")
        except Exception:
            pass
        candidates = list(players)
    return random.choice(candidates)


def _swiss_generate_pairings(S) -> tuple[list[tuple[str, str]], str | None]:
    """Emparejamientos aleatorios por brackets (mismo récord o similar)."""
    players = _eligible_players(S)
    if not players:
        return [], None

    bye = _choose_bye(S, players)
    pool = [p for p in players if p != bye]

    wins = S["wins"]
    groups: dict[int, list[str]] = {}
    for p in pool:
        groups.setdefault(int(wins[p]), []).append(p)
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
    byes = S["byes"]
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
        byes[bye_player] += 1
        res_list.append({"p1": bye_player, "p2": None, "winner": bye_player})
    S["results"].setdefault(rnd, res_list)
    S["history"].append(pairs)
    for p in S["players"]:
        if p not in S["qualified"] and wins[p] >= 4:
            S["qualified"][p] = rnd
        if p not in S["eliminated"] and losses[p] >= 3:
            S["eliminated"].add(p)
    S["round"] += 1
    S["current"] = {"pairs": [], "bye": None}


def _resolve_ties_last_slot(S, tied: list[str]) -> list[str]:
    if len(tied) == 2:
        a, b = tied
        for _, lst in S.get("results", {}).items():
            for m in lst:
                if {m["p1"], m["p2"]} == {a, b}:
                    return [m["winner"], (b if m["winner"] == a else a)]
    bh = _swiss_buchholz(S)
    return sorted(tied, key=lambda p: (bh[p], p), reverse=True)


def _build_topcut(S):
    q = sorted(S["qualified"].items(), key=lambda kv: (kv[1], kv[0]))
    finalists = [p for p, _ in q]
    if len(finalists) < 4:
        wins = S["wins"]
        bh = _swiss_buchholz(S)
        cand = [p for p in S["players"] if p not in finalists]
        cand.sort(key=lambda p: (wins[p], bh[p], p), reverse=True)
        for p in cand:
            if len(finalists) >= 4:
                break
            finalists.append(p)
    finalists = finalists[:4]
    if len(finalists) < 4:
        return
    S["topcut"] = {
        "finalists": finalists,
        "semis": [(finalists[0], finalists[3]), (finalists[1], finalists[2])],
        "semi_winners": [],
        "final": None,
        "champion": None,
    }


# ---------- Pokepaste (solo lectura desde Entrenadores) ----------
def _get_pokepaste(player: str) -> dict | None:
    return st.session_state.get("pokepastes", {}).get(player)


def _view_paste_card(player: str) -> None:
    st.markdown(f"**{player}**")
    paste = _get_pokepaste(player or "")
    if not paste or not paste.get("team"):
        st.caption("Sin Pokepaste guardado.")
        return
    st.caption(f"URL: {paste.get('url')}")
    try:
        from entrenadores import _sanitize_mon  # reuse sanitizer
    except Exception:
        def _sanitize_mon(mon): return mon
    team = [_sanitize_mon(m) for m in paste.get("team", [])]
    team = [m for m in team if m.get("species")]
    for mon in team:
        sp = mon.get("species") or "Pokemon"
        title = mon.get("title") or sp
        item = mon.get("item")
        ability = mon.get("ability")
        moves = mon.get("moves") or []
        try:
            from showdown_sprites import showdown_sprite_url  # lazy import to avoid circulars
            img = showdown_sprite_url(species_name=str(sp), prefer_animated=False)
        except Exception:
            img = None
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                if img:
                    st.image(img, width=64)
            with cols[1]:
                st.markdown(f"**{title}** {f'@ {item}' if item else ''}")
                if ability:
                    st.caption(f"Habilidad: {ability}")
                if moves:
                    st.markdown("\n".join([f"- {m}" for m in moves]))


def _render_matchups_tab(S) -> None:
    st.subheader("Enfrentamientos y equipos")
    history = []
    for rnd, matches in sorted(S.get("results", {}).items()):
        history.append((f"Ronda {rnd}", matches))
    if S.get("current", {}).get("pairs"):
        cur_pairs = [{"p1": a, "p2": b, "winner": None} for (a, b) in S["current"]["pairs"]]
        history.append((f"Ronda {S['round']} (en juego)", cur_pairs))

    if not history:
        st.info("Aún no hay enfrentamientos registrados.")
        return

    for title, matches in history:
        st.markdown(f"### {title}")
        for mi, m in enumerate(matches):
            a, b = m.get("p1"), m.get("p2")
            if not a and not b:
                continue
            cols = st.columns(2)
            with cols[0]:
                _view_paste_card(a or "BYE")
            with cols[1]:
                if b:
                    _view_paste_card(b)
                else:
                    st.caption("BYE")
            st.markdown("---")


# ---------- Página ----------
def page_copa() -> None:
    _ensure_swiss_state()
    st.header("Copa")
    S = st.session_state.swiss

    # Configuración inicial (elegir cantidad y jugadores registrados)
    if not S.get("configured"):
        st.subheader("Configurar Copa (Liga suiza)")
        all_players = list(USERS.keys())
        if not all_players:
            st.error("No hay jugadores registrados.")
            return
        num = st.number_input(
            "Jugadores",
            min_value=2,
            max_value=len(all_players),
            value=min(8, len(all_players)),
            step=1,
        )
        # Propuesta por defecto
        default_sel = (S.get("players") or all_players)[: int(num)]
        sel = st.multiselect("Participantes", all_players, default=default_sel)
        if st.button("Crear Copa", type="primary"):
            if len(sel) != int(num):
                st.error(f"Selecciona exactamente {int(num)} jugadores.")
            else:
                S["players"] = list(sel)
                S["wins"] = {p: 0 for p in sel}
                S["losses"] = {p: 0 for p in sel}
                S["byes"] = {p: 0 for p in sel}
                S["round"] = 1
                S["history"] = []
                S["results"] = {}
                S["qualified"] = {}
                S["eliminated"] = set()
                S["current"] = {"pairs": [], "bye": None}
                S["topcut"] = None
                S["configured"] = True
                st.success("Copa creada.")
                st.rerun()
        return

    colA, colB, colC, colD = st.columns(4)
    with colA:
        if st.button("Resetear copa"):
            del st.session_state.swiss
            _ensure_swiss_state()
            st.success("Copa reiniciada.")
            st.rerun()
    with colB:
        S["manual"] = st.toggle("Edición manual", value=S.get("manual", False))
    with colC:
        st.write(f"Ronda actual: {S['round']} / {S['max_rounds']}")
    with colD:
        st.write(f"Clasificados: {len(S['qualified'])}/4")

    wins, losses = S["wins"], S["losses"]
    bh = _swiss_buchholz(S)
    tabla = sorted(S["players"], key=lambda p: (wins[p], bh[p], p), reverse=True)
    rows = [{
        "Jugador": p,
        "W": wins[p],
        "L": losses[p],
        "Buchholz": bh[p],
        "Estado": ("Clasificado" if p in S["qualified"] else ("Eliminado" if p in S["eliminated"] else "Activo")),
    } for p in tabla]
    st.dataframe(rows, use_container_width=True)

    st.subheader("Emparejamientos de la ronda")
    if not S["current"]["pairs"] and (S.get("topcut") is None) and S["round"] <= S["max_rounds"] and len(S["qualified"]) < 4:
        pairs, bye = _swiss_generate_pairings(S)
        S["current"] = {"pairs": pairs, "bye": bye}

    cur = S["current"]
    if cur["pairs"]:
        winners = []
        for idx, (a, b) in enumerate(cur["pairs"], start=1):
            with st.container(border=True):
                st.markdown(f"<div class='vs-card'><div class='p'>{a}</div><div class='vs'>VS</div><div class='p'>{b}</div></div>", unsafe_allow_html=True)
                pick = st.radio("Ganador", options=[a, b], horizontal=True, key=f"swiss_pick_{S['round']}_{idx}")
                winners.append(pick)
        if cur["bye"]:
            st.info(f"Bye: {cur['bye']}")
        if st.button("Finalizar ronda"):
            if len(winners) == len(cur["pairs"]):
                _apply_round_results(S, cur["pairs"], winners, cur["bye"])
                if len(S["qualified"]) >= 4 or S["round"] > S["max_rounds"]:
                    _build_topcut(S)
                st.rerun()
            else:
                st.error("Marca el ganador en todos los enfrentamientos.")
    else:
        st.caption("Sin emparejamientos activos.")

    st.markdown("---")
    _render_matchups_tab(S)

    if S["manual"]:
        st.markdown("---")
        st.subheader("Edición manual")
        players_all = list(USERS.keys())
        sel = st.multiselect("Jugadores participantes", players_all, default=S["players"]) 
        if st.button("Aplicar jugadores"):
            S["players"] = sel
            for p in sel:
                S["wins"].setdefault(p, 0)
                S["losses"].setdefault(p, 0)
                S["byes"].setdefault(p, 0)
            st.rerun()

        with st.form("swiss_edit_record"):
            cols = st.columns(3)
            with cols[0]:
                st.write("Jugador")
            with cols[1]:
                st.write("W")
            with cols[2]:
                st.write("L")
            edits = []
            for p in S["players"]:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.write(p)
                with c2:
                    w = st.number_input(" ", key=f"w_{p}", value=int(S["wins"].get(p, 0)), min_value=0)
                with c3:
                    losses = st.number_input("  ", key=f"l_{p}", value=int(S["losses"].get(p, 0)), min_value=0)
                edits.append((p, w, losses))
            submitted = st.form_submit_button("Aplicar rcord")
            if submitted:
                for p, w, losses in edits:
                    S["wins"][p] = int(w)
                    S["losses"][p] = int(losses)
                S["qualified"] = {p: S.get("round", 1) for p in S["players"] if S["wins"][p] >= 4}
                S["eliminated"] = {p for p in S["players"] if S["losses"][p] >= 3}
                st.success("Record actualizado.")

        st.markdown("Emparejamientos manuales (formato: 'JugadorA - JugadorB' por lnea; 'bye: JugadorX')")
        txt = st.text_area("Definir emparejamientos", value="", height=120, placeholder="Anto - Victor\nRober - Samu\nbye: Iker")
        if st.button("Aplicar emparejamientos manuales"):
            pairs = []
            bye = None
            for line in txt.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.lower().startswith("bye:"):
                    bye = line.split(":", 1)[1].strip()
                    continue
                if "-" in line:
                    a, b = [x.strip() for x in line.split("-", 1)]
                    if a and b and a in S["players"] and b in S["players"]:
                        pairs.append((a, b))
            S["current"] = {"pairs": pairs, "bye": bye}
            st.success("Emparejamientos manuales aplicados.")

    if S.get("topcut"):
        st.markdown("---")
        st.subheader("Top Cut (Semifinales y Final)")
        tc = S["topcut"]
        if not tc["semi_winners"] and tc["semis"]:
            a1, b1 = tc['semis'][0]
            st.markdown(f"<div class='vs-card'><div class='p'>{a1}</div><div class='vs'>VS</div><div class='p'>{b1}</div></div>", unsafe_allow_html=True)
            w1 = st.radio("Semifinal 1 - ganador", options=[a1, b1], horizontal=True)
            a2, b2 = tc['semis'][1]
            st.markdown(f"<div class='vs-card'><div class='p'>{a2}</div><div class='vs'>VS</div><div class='p'>{b2}</div></div>", unsafe_allow_html=True)
            w2 = st.radio("Semifinal 2 - ganador", options=[a2, b2], horizontal=True)
            if st.button("Registrar semifinales"):
                tc["semi_winners"] = [w1, w2]
                tc["final"] = (w1, w2)
                st.rerun()
        elif tc["final"] and not tc.get("champion"):
            a, b = tc["final"]
            st.markdown(f"<div class='vs-card'><div class='p'>{a}</div><div class='vs'>VS</div><div class='p'>{b}</div></div>", unsafe_allow_html=True)
            champ = st.radio("Final - campen", options=[a, b], horizontal=True)
            if st.button("Registrar campen"):
                tc["champion"] = champ
                st.success(f"Campen: {champ}")
        elif tc.get("champion"):
            st.success(f"Campen: {tc['champion']}")

    # Historial Top Cut
    if S.get("topcut"):
        tc = S["topcut"]
        st.markdown("---")
        st.subheader("Historial Top Cut")
        with st.container(border=True):
            if tc.get("semis"):
                sw = tc.get("semi_winners") or []
                for i, (a, b) in enumerate(tc["semis"], start=1):
                    ganador = sw[i - 1] if i - 1 < len(sw) else ""
                    st.markdown(f"<div class='vs-card'><div class='p'>Semifinal {i}</div><div class='vs'>VS</div><div class='p'></div></div>", unsafe_allow_html=True)
                    st.write(f"{a} vs {b}   Ganador: {ganador}")
            if tc.get("final"):
                a, b = tc["final"]
                champ = tc.get("champion") or ""
                st.markdown("<div class='vs-card'><div class='p'>Final</div><div class='vs'>VS</div><div class='p'></div></div>", unsafe_allow_html=True)
                st.write(f"{a} vs {b}   Ganador: {champ}")
            if tc.get("champion"):
                st.success(f"Campen: {tc['champion']}")

    # Historial de rondas al final
    if S.get("results"):
        st.markdown("---")
        st.subheader("Historial de rondas")
        for rnd in sorted(S["results"].keys()):
            with st.container(border=True):
                st.markdown(f"**Ronda {rnd}**")
                for m in S["results"][rnd]:
                    p1 = m.get("p1")
                    p2 = m.get("p2")
                    w = m.get("winner")
                    if p2 is None:
                        st.write(f"Bye: {p1} (victoria automtica)")
                    else:
                        ganador = w if w in (p1, p2) else "-->"
                        st.write(f"{p1} vs {p2} --> Ganador: {ganador}")

