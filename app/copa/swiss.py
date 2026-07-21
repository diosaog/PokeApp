from __future__ import annotations

import html as _html
import json
import random

import streamlit as st

from app.copa.styles import (
    render_copa_metrics,
    render_copa_section,
    render_copa_styles,
    render_vs_card,
)
from utils import active_users, users_with_retired_last
from storage import settings_get, settings_set
from dexdata import item_name_es


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


def _persist_swiss_state():
    try:
        S = st.session_state.get("swiss")
        if not S:
            return
        def _serial_pairs(pairs):
            return [[a, b] for a, b in pairs]
        data = {
            "players": S.get("players", []),
            "round": S.get("round", 1),
            "max_rounds": S.get("max_rounds", 7),
            "wins": S.get("wins", {}),
            "losses": S.get("losses", {}),
            "byes": S.get("byes", {}),
            "history": [_serial_pairs(h) for h in S.get("history", [])],
            "results": {int(r): m for r, m in S.get("results", {}).items()},
            "qualified": S.get("qualified", {}),
            "eliminated": list(S.get("eliminated", set())),
            "current": {
                "pairs": _serial_pairs(S.get("current", {}).get("pairs", [])),
                "bye": S.get("current", {}).get("bye"),
            },
            "manual": bool(S.get("manual", False)),
            "topcut": S.get("topcut"),
            "configured": bool(S.get("configured", False)),
        }
        settings_set("copa_swiss_state", json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def _restore_swiss_state():
    try:
        raw = settings_get("copa_swiss_state")
        if not raw:
            return
        obj = json.loads(raw)
        def _pairs(lst):
            out = []
            for item in lst or []:
                if isinstance(item, list) and len(item) == 2:
                    out.append((item[0], item[1]))
            return out
        S = {
            "players": obj.get("players", []),
            "round": obj.get("round", 1),
            "max_rounds": obj.get("max_rounds", 7),
            "wins": obj.get("wins", {}),
            "losses": obj.get("losses", {}),
            "byes": obj.get("byes", {}),
            "history": [_pairs(h) for h in obj.get("history", [])],
            "results": obj.get("results", {}),
            "qualified": obj.get("qualified", {}),
            "eliminated": set(obj.get("eliminated", [])),
            "current": {"pairs": _pairs(obj.get("current", {}).get("pairs", [])), "bye": obj.get("current", {}).get("bye")},
            "manual": bool(obj.get("manual", False)),
            "topcut": obj.get("topcut"),
            "configured": bool(obj.get("configured", False)),
        }
        st.session_state.swiss = S
    except Exception:
        pass


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
    if len(players) % 2 == 0:
        return None
    byes = S["byes"]
    candidates = [p for p in players if byes.get(p, 0) == 0]
    if not candidates:
        try:
            st.error("No quedan jugadores sin bye. Revisa la configuracion o el numero de rondas.")
        except Exception:
            pass
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


def _get_pokepaste(player: str) -> dict | None:
    return st.session_state.get("pokepastes", {}).get(player)


def _display_item_name(item: str | None) -> str:
    if not item:
        return ""
    item_txt = str(item).strip()
    if not item_txt:
        return ""
    item_id = item_txt.lstrip("#")
    if item_id.isdigit():
        resolved = item_name_es(item_id)
        if resolved and resolved != "-":
            return resolved
        return "Objeto desconocido"
    return item_txt


def _view_paste_card(player: str) -> None:
    safe_player = _html.escape(str(player or "-"))
    st.markdown(f"<div class='cup-paste-name'>{safe_player}</div>", unsafe_allow_html=True)
    paste = _get_pokepaste(player or "")
    if not paste or not paste.get("team"):
        st.markdown("<div class='cup-paste-meta'>Sin Pokepaste guardado.</div>", unsafe_allow_html=True)
        return
    paste_url = _html.escape(str(paste.get("url") or ""))
    st.markdown(f"<div class='cup-paste-meta'>URL: {paste_url}</div>", unsafe_allow_html=True)
    try:
        from app.entrenadores.pokepaste import sanitize_mon
    except Exception:
        def sanitize_mon(mon):
            return mon
    team = [sanitize_mon(m) for m in paste.get("team", [])]
    team = [m for m in team if m.get("species")]
    for mon in team:
        sp = mon.get("species") or "Pokemon"
        title = mon.get("title") or sp
        item = _display_item_name(mon.get("item"))
        moves = mon.get("moves") or []
        try:
            from showdown_sprites import showdown_sprite_url
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
                if moves:
                    st.markdown("\n".join([f"- {m}" for m in moves]))


def _render_matchups_tab(S) -> None:
    render_copa_section("Enfrentamientos y equipos", "Consulta pairings anteriores y equipos guardados.")
    history = []
    for rnd, matches in sorted(S.get("results", {}).items()):
        history.append((f"Ronda {rnd}", matches))
    if S.get("current", {}).get("pairs"):
        cur_pairs = [{"p1": a, "p2": b, "winner": None} for (a, b) in S["current"]["pairs"]]
        history.append((f"Ronda {S['round']} (en juego)", cur_pairs))

    if not history:
        st.info("Aun no hay enfrentamientos registrados.")
        return

    for title, matches in history:
        render_copa_section(title)
        for m in matches:
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


def page_copa() -> None:
    render_copa_styles()
    _restore_swiss_state()
    _ensure_swiss_state()
    render_copa_section("Liga suiza", "Rondas suizas con clasificacion, eliminados y top cut final.")
    S = st.session_state.swiss

    if not S.get("configured"):
        render_copa_section("Configurar Copa", "Elige participantes y arranca la liga suiza.")
        all_players = users_with_retired_last(active_users())
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
                _persist_swiss_state()
                st.success("Copa creada.")
                st.rerun()
        return

    render_copa_metrics(
        [
            ("Ronda actual", f"{S['round']} / {S['max_rounds']}", None),
            ("Clasificados", f"{len(S['qualified'])}/4", None),
            ("Participantes", str(len(S.get("players") or [])), None),
            ("Modo manual", "Activo" if S.get("manual", False) else "Cerrado", None),
        ]
    )

    colA, colB = st.columns(2)
    with colA:
        if st.button("Resetear copa"):
            del st.session_state.swiss
            _ensure_swiss_state()
            _persist_swiss_state()
            st.success("Copa reiniciada.")
            st.rerun()
    with colB:
        S["manual"] = st.toggle("Edicion manual", value=S.get("manual", False))

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

    render_copa_section("Emparejamientos de la ronda")
    if not S["current"]["pairs"] and (S.get("topcut") is None) and S["round"] <= S["max_rounds"] and len(S["qualified"]) < 4:
        pairs, bye = _swiss_generate_pairings(S)
        S["current"] = {"pairs": pairs, "bye": bye}
        _persist_swiss_state()

    cur = S["current"]
    if cur["pairs"]:
        winners = []
        for idx, (a, b) in enumerate(cur["pairs"], start=1):
            with st.container(border=True):
                render_vs_card(a, b)
                pick = st.radio("Ganador", options=[a, b], horizontal=True, key=f"swiss_pick_{S['round']}_{idx}")
                winners.append(pick)
        if cur["bye"]:
            st.info(f"Bye: {cur['bye']}")
        if st.button("Finalizar ronda"):
            if len(winners) == len(cur["pairs"]):
                _apply_round_results(S, cur["pairs"], winners, cur["bye"])
                if len(S["qualified"]) >= 4 or S["round"] > S["max_rounds"]:
                    _build_topcut(S)
                _persist_swiss_state()
                st.rerun()
            else:
                st.error("Marca el ganador en todos los enfrentamientos.")
    else:
        st.caption("Sin emparejamientos activos.")

    st.markdown("---")
    _render_matchups_tab(S)

    if S["manual"]:
        st.markdown("---")
        render_copa_section("Edicion manual")
        players_all = users_with_retired_last(active_users())
        sel = st.multiselect("Jugadores participantes", players_all, default=S["players"])
        if st.button("Aplicar jugadores"):
            S["players"] = sel
            for p in sel:
                S["wins"].setdefault(p, 0)
                S["losses"].setdefault(p, 0)
                S["byes"].setdefault(p, 0)
            _persist_swiss_state()
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
            submitted = st.form_submit_button("Aplicar record")
            if submitted:
                for p, w, losses in edits:
                    S["wins"][p] = int(w)
                    S["losses"][p] = int(losses)
                S["qualified"] = {p: S.get("round", 1) for p in S["players"] if S["wins"][p] >= 4}
                S["eliminated"] = {p for p in S["players"] if S["losses"][p] >= 3}
                _persist_swiss_state()
                st.success("Record actualizado.")

        st.markdown("Emparejamientos manuales (formato: 'JugadorA - JugadorB' por linea; 'bye: JugadorX')")
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
            _persist_swiss_state()
            st.success("Emparejamientos manuales aplicados.")

    if S.get("topcut"):
        st.markdown("---")
        render_copa_section("Top Cut", "Semifinales y final de la Copa.")
        tc = S["topcut"]
        if not tc["semi_winners"] and tc["semis"]:
            a1, b1 = tc["semis"][0]
            render_vs_card(a1, b1)
            w1 = st.radio("Semifinal 1 - ganador", options=[a1, b1], horizontal=True)
            a2, b2 = tc["semis"][1]
            render_vs_card(a2, b2)
            w2 = st.radio("Semifinal 2 - ganador", options=[a2, b2], horizontal=True)
            if st.button("Registrar semifinales"):
                tc["semi_winners"] = [w1, w2]
                tc["final"] = (w1, w2)
                _persist_swiss_state()
                st.rerun()
        elif tc["final"] and not tc.get("champion"):
            a, b = tc["final"]
            render_vs_card(a, b)
            champ = st.radio("Final - campeon", options=[a, b], horizontal=True)
            if st.button("Registrar campeon"):
                tc["champion"] = champ
                st.success(f"Campeon: {champ}")
                _persist_swiss_state()
        elif tc.get("champion"):
            st.success(f"Campeon: {tc['champion']}")

    if S.get("topcut"):
        tc = S["topcut"]
        st.markdown("---")
        render_copa_section("Historial Top Cut")
        with st.container(border=True):
            if tc.get("semis"):
                sw = tc.get("semi_winners") or []
                for i, (a, b) in enumerate(tc["semis"], start=1):
                    ganador = sw[i - 1] if i - 1 < len(sw) else ""
                    render_vs_card(f"Semifinal {i}", "")
                    st.write(f"{a} vs {b}   Ganador: {ganador}")
            if tc.get("final"):
                a, b = tc["final"]
                champ = tc.get("champion") or ""
                render_vs_card("Final", "")
                st.write(f"{a} vs {b}   Ganador: {champ}")
            if tc.get("champion"):
                st.success(f"Campeon: {tc['champion']}")

    if S.get("results"):
        st.markdown("---")
        render_copa_section("Historial de rondas")
        for rnd in sorted(S["results"].keys()):
            with st.container(border=True):
                st.markdown(f"**Ronda {rnd}**")
                for m in S["results"][rnd]:
                    p1 = m.get("p1")
                    p2 = m.get("p2")
                    w = m.get("winner")
                    if p2 is None:
                        st.write(f"Bye: {p1} (victoria automatica)")
                    else:
                        ganador = w if w in (p1, p2) else "--"
                        st.write(f"{p1} vs {p2} --> Ganador: {ganador}")
