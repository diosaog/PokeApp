# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
import json
import streamlit as st

from utils import USERS, list_user_saves, ensure_user_dir
from storage import settings_get, settings_set, clear_purchases, add_purchase, get_current_save_for_user, load_save_bytes
from conex_pkhex import PKHeXRuntime, extract_box, has_pc_data, open_sav_cached


# ===== Estado y persistencia =====
def _sanitize_divisions(divs: dict) -> dict:
    players = list(USERS.keys())
    canon = {}
    for u in players:
        key = str(u).strip()
        if key and key not in canon:
            canon[key] = u

    def _norm_list(items: list) -> list[str]:
        out: list[str] = []
        for it in items or []:
            key = str(it).strip()
            if not key:
                continue
            val = canon.get(key)
            if val and val not in out:
                out.append(val)
        return out

    curA = _norm_list(divs.get("A", [])) if isinstance(divs, dict) else []
    curB = _norm_list(divs.get("B", [])) if isinstance(divs, dict) else []
    curB = [u for u in curB if u not in curA]
    return {"A": curA, "B": curB}

def _serialize_state() -> dict:
    S = st.session_state
    matches: Dict[str, Dict[str, list[dict]]] = {}
    for tramo, divs in (S.get("league_matches") or {}).items():
        tkey = str(tramo)
        out = {"A": [], "B": []}
        for d in ("A", "B"):
            for (p1, p2), w in divs.get(d, {}).items():
                out[d].append({"p1": p1, "p2": p2, "winner": w})
        matches[tkey] = out
    results = {u: {str(k): int(v) for k, v in mp.items()} for u, mp in (S.get("league_results") or {}).items()}
    return {
        "tramo": int(S.get("league_tramo", 1)),
        "active": bool(S.get("league_active", False)),
        "divisions": S.get("league_divisions", {"A": [], "B": []}),
        "matches": matches,
        "results": results,
        "movements": S.get("league_movements", {}),
    }


def _restore_state() -> None:
    try:
        raw = settings_get("league_state")
        if not raw:
            return
        obj = json.loads(raw)
        if "league_tramo" not in st.session_state:
            st.session_state.league_tramo = int(obj.get("tramo", 1))
        if "league_active" not in st.session_state:
            st.session_state.league_active = bool(obj.get("active", False))
        if "league_divisions" not in st.session_state:
            st.session_state.league_divisions = obj.get("divisions", {"A": [], "B": []})
        if "league_divisions" in st.session_state:
            st.session_state.league_divisions = _sanitize_divisions(st.session_state.league_divisions)
        if "league_results" not in st.session_state:
            res_in = obj.get("results", {})
            st.session_state.league_results = {u: {int(k): int(v) for k, v in mp.items()} for u, mp in res_in.items()}
        if "league_matches" not in st.session_state:
            mat_in = obj.get("matches", {})
            mat_out: Dict[int, Dict[str, Dict[tuple, str | None]]] = {}
            for tkey, divs in mat_in.items():
                t = int(tkey)
                mat_out[t] = {"A": {}, "B": {}}
                for d in ("A", "B"):
                    for m in divs.get(d, []) or []:
                        mat_out[t][d][(m.get("p1"), m.get("p2"))] = m.get("winner")
            st.session_state.league_matches = mat_out
        mov = obj.get("movements", {})
        if isinstance(mov, dict):
            st.session_state.league_movements = {int(k): v for k, v in mov.items()}
    except Exception:
        pass


def _persist():
    try:
        settings_set("league_state", json.dumps(_serialize_state(), ensure_ascii=False))
    except Exception:
        # Si falla persistencia, avisar
        try:
            st.error("No se pudo guardar el estado de la liga (settings).")
        except Exception:
            pass


# ===== Helpers de liga =====
MAX_JORNADAS = 4


def _ensure_state():
    if "league_tramo" not in st.session_state:
        st.session_state.league_tramo = 1
    if "league_active" not in st.session_state:
        st.session_state.league_active = False
    if "league_results" not in st.session_state:
        st.session_state.league_results = {}
    if "league_divisions" not in st.session_state:
        players = list(USERS.keys())
        st.session_state.league_divisions = {"A": players[:5], "B": players[5:10]}
    else:
        st.session_state.league_divisions = _sanitize_divisions(st.session_state.league_divisions)
    if "league_matches" not in st.session_state:
        st.session_state.league_matches = {}
    if "league_movements" not in st.session_state:
        st.session_state.league_movements = {}


def _gen_pairs(players: list[str]) -> list[tuple[str, str]]:
    res = []
    n = len(players)
    for i in range(n):
        for j in range(i + 1, n):
            res.append((players[i], players[j]))
    return res


def _get_matches_for(tramo: int) -> dict:
    if tramo not in st.session_state.league_matches:
        A = st.session_state.league_divisions["A"]
        B = st.session_state.league_divisions["B"]
        st.session_state.league_matches[tramo] = {
            "A": {pair: None for pair in _gen_pairs(A)},
            "B": {pair: None for pair in _gen_pairs(B)},
        }
    _persist()
    return st.session_state.league_matches[tramo]


def _latest_save_path(trainer: str) -> str | None:
    """Intenta obtener la ruta local del save más reciente, bajándolo de Supabase si falta."""
    try:
        saves = list_user_saves(trainer)
        if saves:
            return str(saves[0])

        cur = get_current_save_for_user(trainer)
        if cur:
            fname = cur[1]
            data = load_save_bytes(fname)
            if data:
                dest = ensure_user_dir(trainer) / fname
                dest.write_bytes(data)
                return str(dest)
    except Exception:
        pass
    return None


def _count_muertos_for_trainer(trainer: str) -> int:
    try:
        active_path = _latest_save_path(trainer)
        if not active_path:
            return 0
        sav_json = open_sav_cached(active_path)
        if not has_pc_data(sav_json):
            return 0
        muertos_list = extract_box(sav_json, 17)  # Caja 18
        muertos = len(muertos_list or [])
    except Exception:
        muertos = 0

    # Penalización extra por revivir tras wipe (guardado en settings)
    try:
        extra = settings_get(f"revived_after_wipe:{trainer}")
        revives = int(extra) if extra not in (None, "") else 0
        revives = max(revives, 0)
    except Exception:
        revives = 0

    # Cada revivido cuenta como 0.4 (equivalente a 2 muertes de 0.2)
    return muertos + 2 * revives


def _wins_losses(players: list[str], results: dict[tuple[str, str], str]) -> dict:
    table = {p: {"W": 0, "L": 0} for p in players}
    for (p1, p2), w in results.items():
        if w is None:
            continue
        loser = p2 if w == p1 else p1
        table[w]["W"] += 1
        table[loser]["L"] += 1
    return table


def _h2h(p1: str, p2: str, results: dict[tuple[str, str], str]) -> str | None:
    key = (p1, p2) if (p1, p2) in results else (p2, p1)
    if key in results and results[key] in (p1, p2):
        return results[key]
    return None


def _rank(players: list[str], results: dict[tuple[str, str], str]) -> list[str]:
    wl = _wins_losses(players, results)
    groups: Dict[int, list[str]] = {}
    for p in players:
        groups.setdefault(wl[p]["W"], []).append(p)
    ranking: list[str] = []
    for wins in sorted(groups.keys(), reverse=True):
        group = groups[wins]
        if len(group) == 1:
            ranking += group
            continue
        if len(group) == 2:
            p1, p2 = group
            h2h = _h2h(p1, p2, results)
            if h2h is not None:
                ranking += [h2h, p2 if h2h == p1 else p1]
            else:
                ranking += sorted(group)
        else:
            muertos = {p: _count_muertos_for_trainer(p) for p in group}
            group_sorted = sorted(group, key=lambda x: (muertos[x], x))
            ranking += group_sorted
    return ranking


def _all_filled(md: dict[tuple[str, str], str | None]) -> bool:
    return all(w is not None for w in md.values())


def _record_position(tramo: int, user: str, pos: int) -> None:
    st.session_state.league_results.setdefault(user, {})[tramo] = pos


def _finalize(tramo: int) -> None:
    data = _get_matches_for(tramo)
    A_players = st.session_state.league_divisions["A"]
    B_players = st.session_state.league_divisions["B"]
    if not _all_filled(data["A"]) or not _all_filled(data["B"]):
        raise ValueError("Faltan resultados por marcar en A o B.")
    rankA = _rank(A_players, data["A"])
    rankB = _rank(B_players, data["B"])
    start_b = len(A_players) + 1
    for i, u in enumerate(rankA, start=1):
        _record_position(tramo, u, i)
    for j, u in enumerate(rankB, start=start_b):
        _record_position(tramo, u, j)

    # Premio: Último de B recibe "Robar Pokémon"
    try:
        if rankB:
            last_user = rankB[-1]
            add_purchase(last_user, "Robar Pokemon", 0)
            try:
                st.toast(f"Comodin entregado a {last_user}: Robar Pokemon", icon="✅")
            except Exception:
                pass
    except Exception:
        pass

    # Ascensos/descensos (5 y 5): bajan 3 últimos de A, suben 3 primeros de B
    nueva_A = rankA[:2] + rankB[:3]
    nueva_B = rankA[2:5] + rankB[3:5]
    st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}
    try:
        st.session_state.league_movements[tramo] = {"up": [rankB[0], rankB[1]], "down": [rankA[2], rankA[3]]}
    except Exception:
        pass
    st.session_state.league_active = False
    st.session_state.league_tramo = tramo + 1
    _persist()


POINTS_BY_POSITION = {1: 9, 2: 8, 3: 7, 4: 6, 5: 5, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}


def points_from_league(user: str) -> int:
    lr = st.session_state.get("league_results", {})
    tramos = lr.get(user, {})
    total = 0
    for pos in tramos.values():
        total += POINTS_BY_POSITION.get(int(pos), 0)
    return total


def _one_decimal(x: float) -> float:
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(x)).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP))


def current_points_total(user: str) -> float:
    base = points_from_league(user)
    muertos = _count_muertos_for_trainer(user)
    total = base - 0.2 * muertos
    return _one_decimal(total)


def general_table_sorted() -> list[tuple[str, float]]:
    return sorted([(u, current_points_total(u)) for u in USERS.keys()], key=lambda x: x[1], reverse=True)


def page_tabla() -> None:
    _restore_state()
    _ensure_state()

    st.header("Liga A/B - Jornada")
    tramo = st.session_state.league_tramo
    liga_finalizada = tramo > MAX_JORNADAS

    colA, colB = st.columns([2, 2])
    with colA:
        estado = 'En edicion' if st.session_state.league_active else 'Cerrado'
        badge_cls = 'status-warn' if st.session_state.league_active else 'status-ok'
        st.markdown(
            f"Tramo actual: <strong>{tramo}</strong> "
            f"<span class='status-badge {badge_cls}'>{estado}</span>",
            unsafe_allow_html=True,
        )
    with colB:
        if st.session_state.league_active:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Finalizar jornada", use_container_width=True):
                    try:
                        _finalize(tramo)
                        st.success("Jornada cerrada: rankings calculados y ascensos/descensos aplicados.")
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Cancelar jornada", use_container_width=True):
                    st.session_state.league_active = False
                    if tramo in st.session_state.league_matches:
                        del st.session_state.league_matches[tramo]
                    _persist()
                    st.info("Edicion cancelada. No se guardara ningun resultado.")
        else:
            if liga_finalizada:
                st.info("La liga ha finalizado. No se pueden crear más jornadas.")
            else:
                if st.button("Editar jornada", use_container_width=True):
                    st.session_state.league_active = True
                    _get_matches_for(tramo)
                    _persist()

    st.markdown("---")
    st.subheader("Editar divisiones")
    with st.expander("Divisiones (5 y 5)", expanded=False):
        players = list(USERS.keys())
        cur_divs = st.session_state.league_divisions if isinstance(st.session_state.league_divisions, dict) else {"A": [], "B": []}
        default_A = [p for p in cur_divs.get("A", []) if p in players][:5]
        sel_A = st.multiselect("Liga A (5 jugadores)", players, default=default_A, max_selections=5)
        remaining = [p for p in players if p not in sel_A]
        default_B = [p for p in cur_divs.get("B", []) if p in remaining][:5]
        sel_B = st.multiselect("Liga B (5 jugadores)", remaining, default=default_B, max_selections=5)
        if st.button("Guardar divisiones"):
            if len(sel_A) == 5 and len(sel_B) == 5:
                st.session_state.league_divisions = {"A": sel_A, "B": sel_B}
                # Reiniciar jornadas/matches para evitar inconsistencias
                st.session_state.league_tramo = 1
                st.session_state.league_active = False
                st.session_state.league_matches = {}
                st.session_state.league_results = {}
                st.session_state.league_movements = {}
                st.success("Divisiones actualizadas.")
                _persist()
            else:
                st.error("Selecciona exactamente 5 en A y 5 en B.")

    st.markdown("---")
    A = st.session_state.league_divisions["A"]
    B = st.session_state.league_divisions["B"]
    pos_b_start = len(A) + 1
    pos_b_end = pos_b_start + len(B) - 1 if B else pos_b_start - 1

    if st.session_state.league_active:
        st.subheader("Resultados - marca el ganador de cada enfrentamiento")
        data = _get_matches_for(tramo)

        # Estado temporal para no forzar persistencia en cada selección (reduce lag)
        def _ensure_tmp_results():
            tmp = st.session_state.setdefault("league_tmp", {})
            divs = tmp.setdefault(tramo, {"A": {}, "B": {}})
            for div in ("A", "B"):
                for (p1, p2), winner in data[div].items():
                    key = f"{p1} vs {p2}"
                    divs[div].setdefault(key, winner)
            return divs

        tmp_divs = _ensure_tmp_results()

        with st.form(f"form_results_{tramo}"):
            cA, cB = st.columns(2)
            with cA:
                st.markdown("**Liga A (posiciones 1-5)**")
                for (p1, p2), winner in data["A"].items():
                    key = f"{p1} vs {p2}"
                    current = tmp_divs["A"].get(key)
                    opts = ["(sin marcar)", p1, p2]
                    try:
                        idx = opts.index(current) if current in opts else 0
                    except Exception:
                        idx = 0
                    pick = st.selectbox(key, opts, index=idx, key=f"A_{p1}_{p2}")
                    tmp_divs["A"][key] = None if pick == "(sin marcar)" else pick
            with cB:
                rango_b = f"{pos_b_start}-{pos_b_end}" if pos_b_start <= pos_b_end else f"{pos_b_start}-?"
                st.markdown(f"**Liga B (posiciones {rango_b})**")
                for (p1, p2), winner in data["B"].items():
                    key = f"{p1} vs {p2}"
                    current = tmp_divs["B"].get(key)
                    opts = ["(sin marcar)", p1, p2]
                    try:
                        idx = opts.index(current) if current in opts else 0
                    except Exception:
                        idx = 0
                    pick = st.selectbox(key, opts, index=idx, key=f"B_{p1}_{p2}")
                    tmp_divs["B"][key] = None if pick == "(sin marcar)" else pick

            submitted = st.form_submit_button("Guardar resultados de la jornada")
            if submitted:
                for (p1, p2) in list(data["A"].keys()):
                    k = f"{p1} vs {p2}"
                    data["A"][(p1, p2)] = tmp_divs["A"].get(k)
                for (p1, p2) in list(data["B"].keys()):
                    k = f"{p1} vs {p2}"
                    data["B"][(p1, p2)] = tmp_divs["B"].get(k)
                _persist()
                st.success("Resultados guardados.")

        if _all_filled(data["A"]) and _all_filled(data["B"]):
            st.markdown("---")
            st.subheader("Previa  ranking estimado")
            rankA = _rank(A, data["A"])
            rankB = _rank(B, data["B"])
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Liga A**")
                for i, u in enumerate(rankA, start=1):
                    st.write(f"{i}. {u}")
            with cb:
                st.markdown("**Liga B**")
                for j, u in enumerate(rankB, start=pos_b_start):
                    st.write(f"{j}. {u}")
    else:
        st.subheader("Divisiones actuales")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Liga A**")
            for i, u in enumerate(A, start=1):
                st.write(f"{i}. {u}")
        with c2:
            st.markdown("**Liga B**")
            for j, u in enumerate(B, start=pos_b_start):
                st.write(f"{j}. {u}")

    # Reiniciar Liga (al final)
    st.markdown("---")
    
    # Tabla general (puntos con penalización por muertos)
    st.markdown("---")
    st.subheader("Tabla general")
    tabla = general_table_sorted()
    st.dataframe(
        [{"Pos": i+1, "Jugador": u, "Puntos": pts} for i, (u, pts) in enumerate(tabla)],
        use_container_width=True,
    )

        # Historial por jornada: posiciones (Liga A y Liga B en tablas separadas)
    if st.session_state.get("league_movements") or st.session_state.get("league_results"):
        st.markdown("---")
        st.subheader("Historial")
        lr = st.session_state.get("league_results", {})
        tramos = set()
        for _u, mp in lr.items():
            try:
                tramos.update(int(k) for k in mp.keys())
            except Exception:
                tramos |= set(mp.keys())
        for t in sorted(tramos):
            st.markdown(f"**Tramo {t}**")
            mv = st.session_state.get("league_movements", {}).get(t, {})
            up_set = set(mv.get("up") or [])
            down_set = set(mv.get("down") or [])
            entries = []
            for u, mp in lr.items():
                try:
                    pos = mp.get(t)
                    if pos is not None:
                        entries.append((u, int(pos)))
                except Exception:
                    continue
            if not entries:
                continue
            entries.sort(key=lambda x: x[1])
            a_len = len(st.session_state.league_divisions.get("A", [])) if isinstance(st.session_state.league_divisions, dict) else 4
            if a_len <= 0:
                a_len = 4
            b_len = len(st.session_state.league_divisions.get("B", [])) if isinstance(st.session_state.league_divisions, dict) else 0
            b_start = a_len + 1
            b_end = b_start + b_len - 1 if b_len else b_start - 1
            rowsA, rowsB = [], []
            for u, pos in entries:
                tag = "⬆️ " if u in up_set else ("⬇️ " if u in down_set else "")
                row = {"Pos": pos, "Jugador": f"{tag}{u}"}
                if pos <= a_len:
                    rowsA.append(row)
                else:
                    rowsB.append(row)
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"Liga A (1-{a_len})")
                st.dataframe(rowsA or [], use_container_width=True)
            with c2:
                st.caption(f"Liga B ({b_start}-{b_end})")
                st.dataframe(rowsB or [], use_container_width=True)    # Reiniciar Liga (al final)
    st.markdown("---")
    st.subheader("Reiniciar Liga")
    confirm = st.selectbox("¿Estás seguro que quieres reiniciar la Liga?", ["No", "Sí"], key="reset_league_ligatabla")
    if st.button("Reiniciar liga", help="Borra jornadas, resultados y divisiones", key="btn_reset_league_ligatabla"):
        if confirm == "Sí":
            players = list(USERS.keys())
            st.session_state.league_tramo = 1
            st.session_state.league_active = False
            st.session_state.league_results = {}
            st.session_state.league_matches = {}
            st.session_state.league_temp_order = {"A": [], "B": []}
            st.session_state.league_divisions = {"A": players[:5], "B": players[5:10]}
            st.session_state.league_movements = {}
            try:
                clear_purchases()
            except Exception:
                pass
            _persist()
            st.success("Liga reiniciada.")
        else:
            st.info("Operación cancelada. La liga sigue igual.")






