from __future__ import annotations

from pathlib import Path
from typing import Dict
import streamlit as st

from app.entrenadores.constants import DEAD_BOX_INDEX
from app.entrenadores.cache import cached_dead_count
from app.juicios.penalties import get_user_penalties
from app.tienda.common import _eq_item
from storage import add_purchase, get_current_save_for_user, list_inventory, load_save_bytes, settings_get
from utils import USERS, ensure_user_dir, list_user_saves

MAX_JORNADAS = 5


def _cache_data(ttl: int = 20):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


def _gen_pairs(players: list[str]) -> list[tuple[str, str]]:
    res = []
    n = len(players)
    for i in range(n):
        for j in range(i + 1, n):
            res.append((players[i], players[j]))
    return res


def _players_from_matches(results: dict[tuple[str, str], str | None]) -> list[str]:
    players: list[str] = []
    for p1, p2 in results.keys():
        if p1 and p1 not in players:
            players.append(p1)
        if p2 and p2 not in players:
            players.append(p2)
    return players


def get_matches_for(tramo: int) -> dict:
    if tramo not in st.session_state.league_matches:
        A = st.session_state.league_divisions["A"]
        B = st.session_state.league_divisions["B"]
        st.session_state.league_matches[tramo] = {
            "A": {pair: None for pair in _gen_pairs(A)},
            "B": {pair: None for pair in _gen_pairs(B)},
        }
    return st.session_state.league_matches[tramo]


@_cache_data(ttl=15)
def _latest_save_path(trainer: str) -> str | None:
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


@_cache_data(ttl=180)
def _muertos_from_save(active_path: str, mtime: float) -> int:
    try:
        if not active_path:
            return 0
        return int(cached_dead_count(active_path, float(mtime), DEAD_BOX_INDEX))
    except Exception:
        return 0


def _count_muertos_for_trainer(trainer: str, *, raw_dead_count: int | None = None) -> int:
    if raw_dead_count is None:
        try:
            active_path = _latest_save_path(trainer)
            mtime = Path(active_path).stat().st_mtime if active_path else 0.0
            muertos = _muertos_from_save(active_path or "", float(mtime))
        except Exception:
            muertos = 0
    else:
        try:
            muertos = max(int(raw_dead_count), 0)
        except Exception:
            muertos = 0

    try:
        extra = settings_get(f"revived_after_wipe:{trainer}")
        revives = int(extra) if extra not in (None, "") else 0
        revives = max(revives, 0)
    except Exception:
        revives = 0

    revives_used = _used_revives_count(trainer)

    return muertos + revives_used + 2 * revives


@_cache_data(ttl=15)
def _used_revives_count(trainer: str) -> int:
    try:
        used_items = list_inventory(trainer, status="used", limit=300)
        return sum(1 for row in (used_items or []) if len(row) > 1 and _eq_item(row[1], "Revivir Pokemon"))
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


def all_filled(md: dict[tuple[str, str], str | None]) -> bool:
    return all(w is not None for w in md.values())


def _record_position(tramo: int, user: str, pos: int) -> None:
    st.session_state.league_results.setdefault(user, {})[tramo] = pos


def finalize(tramo: int) -> None:
    data = get_matches_for(tramo)
    A_players = st.session_state.league_divisions["A"]
    B_players = st.session_state.league_divisions["B"]
    if not all_filled(data["A"]) or not all_filled(data["B"]):
        raise ValueError("Faltan resultados por marcar en A o B.")
    rankA = _rank(A_players, data["A"])
    rankB = _rank(B_players, data["B"])
    start_b = len(A_players) + 1
    for i, u in enumerate(rankA, start=1):
        _record_position(tramo, u, i)
    for j, u in enumerate(rankB, start=start_b):
        _record_position(tramo, u, j)

    try:
        if rankB:
            last_user = rankB[-1]
            add_purchase(last_user, "Robar Pokemon", 0)
            try:
                st.toast(f"Comodin entregado a {last_user}: Robar Pokemon")
            except Exception:
                pass
    except Exception:
        pass

    if tramo < MAX_JORNADAS:
        nueva_A = rankA[:2] + rankB[:3]
        nueva_B = rankA[2:5] + rankB[3:5]
        st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}
        try:
            st.session_state.league_movements[tramo] = {"up": [rankB[0], rankB[1]], "down": [rankA[2], rankA[3]]}
        except Exception:
            pass
    else:
        try:
            st.session_state.setdefault("league_movements", {}).pop(tramo, None)
        except Exception:
            pass
    st.session_state.league_active = False
    st.session_state.league_tramo = tramo + 1
    persist_state()


def recompute_round(tramo: int, *, apply_divisions_from_round: bool = False) -> None:
    data = st.session_state.get("league_matches", {}).get(tramo)
    if not data:
        raise ValueError("No hay resultados guardados para esa jornada.")
    if not all_filled(data.get("A", {})) or not all_filled(data.get("B", {})):
        raise ValueError("La jornada anterior tiene enfrentamientos sin ganador.")

    A_results = data.get("A", {})
    B_results = data.get("B", {})
    A_players = _players_from_matches(A_results)
    B_players = _players_from_matches(B_results)
    if not A_players or not B_players:
        raise ValueError("No se pudieron reconstruir las divisiones de esa jornada.")

    rankA = _rank(A_players, A_results)
    rankB = _rank(B_players, B_results)
    start_b = len(rankA) + 1

    st.session_state.setdefault("league_results", {})
    for _u, mp in st.session_state.league_results.items():
        try:
            mp.pop(tramo, None)
        except Exception:
            continue

    for i, u in enumerate(rankA, start=1):
        _record_position(tramo, u, i)
    for j, u in enumerate(rankB, start=start_b):
        _record_position(tramo, u, j)

    if tramo < MAX_JORNADAS:
        try:
            st.session_state.setdefault("league_movements", {})
            st.session_state.league_movements[tramo] = {
                "up": [rankB[0], rankB[1]],
                "down": [rankA[2], rankA[3]],
            }
        except Exception:
            pass
    else:
        try:
            st.session_state.setdefault("league_movements", {}).pop(tramo, None)
        except Exception:
            pass

    if apply_divisions_from_round and tramo < MAX_JORNADAS:
        nueva_A = rankA[:2] + rankB[:3]
        nueva_B = rankA[2:5] + rankB[3:5]
        st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}

    persist_state()


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


def current_points_total(
    user: str,
    *,
    raw_dead_count: int | None = None,
    penalties: dict | None = None,
) -> float:
    base = points_from_league(user)
    muertos = _count_muertos_for_trainer(user, raw_dead_count=raw_dead_count)
    penalties = penalties if penalties is not None else get_user_penalties(user)
    points_reduction = float(penalties.get("points_reduction") or 0.0)
    total = base - 0.2 * muertos - points_reduction
    return _one_decimal(total)


def general_table_sorted() -> list[tuple[str, float]]:
    return sorted([(u, current_points_total(u)) for u in USERS.keys()], key=lambda x: (-x[1], x[0]))


def final_podium() -> list[tuple[str, float]]:
    return general_table_sorted()[:3]


def clear_ranking_caches() -> None:
    for func in (_latest_save_path, _muertos_from_save, _used_revives_count, cached_dead_count):
        try:
            func.clear()
        except Exception:
            continue
