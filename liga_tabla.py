# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict
from functools import lru_cache
import json
import streamlit as st

from utils import USERS, list_user_saves
from storage import settings_get, settings_set, clear_purchases, add_purchase
from conex_pkhex import PKHeXRuntime, extract_box, has_pc_data


# ===== Estado y persistencia =====
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
        st.session_state.league_tramo = int(obj.get("tramo", 1))
        st.session_state.league_active = bool(obj.get("active", False))
        st.session_state.league_divisions = obj.get("divisions", {"A": [], "B": []})
        res_in = obj.get("results", {})
        st.session_state.league_results = {u: {int(k): int(v) for k, v in mp.items()} for u, mp in res_in.items()}
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
        st.session_state.league_divisions = {"A": players[:4], "B": players[4:9]}
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


@lru_cache(maxsize=64)
def _count_muertos_for_trainer(trainer: str) -> int:
    try:
        saves = list_user_saves(trainer)
        if not saves:
            return 0
        active_path = str(saves[0])
        sav_json = PKHeXRuntime.open_sav(active_path)
        if not has_pc_data(sav_json):
            return 0
        muertos_list = extract_box(sav_json, 17)  # Caja 18
        return len(muertos_list or [])
    except Exception:
        return 0


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
    for i, u in enumerate(rankA, start=1):
        _record_position(tramo, u, i)
    for j, u in enumerate(rankB, start=5):
        _record_position(tramo, u, j)

    # Premio: Último de B recibe "Robar Pokémon"
    try:
        if rankB:
            last_user = rankB[-1]
            add_purchase(last_user, "Robar Pokemon", 0)
            try:
                st.toast(f"Comodin entregado a {last_user}: Robar Pokemon", icon="")
            except Exception:
                pass
    except Exception:
        pass

    # Ascensos/descensos
    nueva_A = [rankA[0], rankA[1], rankB[0], rankB[1]]
    nueva_B = [rankA[2], rankA[3]] + rankB[2:5]
    st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}
    try:
        st.session_state.league_movements[tramo] = {"up": [rankB[0], rankB[1]], "down": [rankA[2], rankA[3]]}
    except Exception:
        pass
    st.session_state.league_active = False
    st.session_state.league_tramo = tramo + 1
    _persist()


def points_from_league(user: str) -> int:
    lr = st.session_state.get("league_results", {})
    tramos = lr.get(user, {})
    return sum(10 - pos for pos in tramos.values())


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
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Cancelar jornada", use_container_width=True):
                    st.session_state.league_active = False
                    if tramo in st.session_state.league_matches:
                        del st.session_state.league_matches[tramo]
                    _persist()
                    st.info("Edicion cancelada. No se guardara ningun resultado.")
                    st.rerun()
        else:
            if liga_finalizada:
                st.info("La liga ha finalizado. No se pueden crear más jornadas.")
            else:
                if st.button("Editar jornada", use_container_width=True):
                    st.session_state.league_active = True
                    _get_matches_for(tramo)
                    _persist()
                    st.rerun()

    st.markdown("---")
    A = st.session_state.league_divisions["A"]
    B = st.session_state.league_divisions["B"]

    if st.session_state.league_active:
        st.subheader("Resultados - marca el ganador de cada enfrentamiento")
        data = _get_matches_for(tramo)
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**Liga A (posiciones 1-4)**")
            for (p1, p2), winner in data["A"].items():
                idx = (0 if winner == p1 else 1 if winner == p2 else 0)
                pick = st.radio(f"{p1} vs {p2}", options=[p1, p2], index=idx, horizontal=True, key=f"A_{p1}_{p2}")
                data["A"][(p1, p2)] = pick
                _persist()
        with cB:
            st.markdown("**Liga B (posiciones 5-9)**")
            for (p1, p2), winner in data["B"].items():
                idx = (0 if winner == p1 else 1 if winner == p2 else 0)
                pick = st.radio(f"{p1} vs {p2}", options=[p1, p2], index=idx, horizontal=True, key=f"B_{p1}_{p2}")
                data["B"][(p1, p2)] = pick
                _persist()

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
                for j, u in enumerate(rankB, start=5):
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
            for j, u in enumerate(B, start=5):
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
            rowsA, rowsB = [], []
            for u, pos in entries:
                tag = "⬆️ " if u in up_set else ("⬇️ " if u in down_set else "")
                row = {"Pos": pos, "Jugador": f"{tag}{u}"}
                if pos <= 4:
                    rowsA.append(row)
                else:
                    rowsB.append(row)
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Liga A (1–4)")
                st.dataframe(rowsA or [], use_container_width=True)
            with c2:
                st.caption("Liga B (5–9)")
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
            st.session_state.league_divisions = {"A": players[:4], "B": players[4:9]}
            st.session_state.league_movements = {}
            try:
                clear_purchases()
            except Exception:
                pass
            _persist()
            st.success("Liga reiniciada.")
            st.rerun()
        else:
            st.info("Operación cancelada. La liga sigue igual.")






