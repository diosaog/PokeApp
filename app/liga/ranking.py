from __future__ import annotations

import json
import streamlit as st

from app.domain.services.league import (
    all_matches_filled as domain_all_matches_filled,
    generate_pairs,
    head_to_head,
    one_decimal,
    players_from_matches,
    rank_division,
    sync_match_map,
    total_points_with_penalties,
    wins_losses,
)
from app.entrenadores.constants import DEAD_BOX_INDEX
from app.entrenadores.cache import cached_dead_count
from app.entrenadores.snapshot import clear_trainer_snapshot_runtime_caches, get_trainer_snapshot
from app.liga.divisions import next_divisions_from_rankings
from app.juicios.penalties import get_user_penalties
from app.liga.eligibility import counts_for_league_reward
from app.liga.permissions import require_league_admin
from app.liga.rewards import (
    CURRENT_POINTS_BY_POSITION,
    points_for_league_position,
)
from app.liga.snapshots import (
    ROUND_SNAPSHOTS_STATE_KEY,
    build_matchday_snapshot,
    latest_snapshot_penalties_for_user,
    snapshot_awards_for_user,
    snapshot_for_round,
)
from app.season.config import current_season_version, season_rule_enabled
from app.season.config import DEFAULT_MAX_ROUNDS, max_rounds
from app.tienda.common import _eq_item
from app.entrenadores.trainer_flags import (
    retired_trainers,
    status_labels_for,
    trainer_status,
)
from storage import (
    add_purchase,
    get_current_save_for_user,
    list_inventory,
    list_redemptions,
    load_save_bytes,
    settings_get,
)
from utils import USERS, active_users, ensure_user_dir, list_user_saves

MAX_JORNADAS = DEFAULT_MAX_ROUNDS
POINTS_BY_POSITION = CURRENT_POINTS_BY_POSITION


def max_jornadas(round_no: int | None = None) -> int:
    return max_rounds(round_no)


def _visible_league_users() -> dict[str, str]:
    return active_users()


def _cache_data(ttl: int = 20):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


def _gen_pairs(players: list[str]) -> list[tuple[str, str]]:
    return generate_pairs(players)


def _sync_match_map(
    players: list[str],
    existing: dict[tuple[str, str], str | None] | None,
) -> dict[tuple[str, str], str | None]:
    return sync_match_map(players, existing)


def _players_from_matches(results: dict[tuple[str, str], str | None]) -> list[str]:
    return players_from_matches(results)


def get_matches_for(tramo: int) -> dict:
    A = st.session_state.league_divisions["A"]
    B = st.session_state.league_divisions["B"]
    current = st.session_state.league_matches.get(tramo, {})
    st.session_state.league_matches[tramo] = {
        "A": _sync_match_map(A, current.get("A", {})),
        "B": _sync_match_map(B, current.get("B", {})),
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
            snapshot = get_trainer_snapshot(trainer)
            muertos = max(int(snapshot.get("dead_count") or 0), 0)
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
    redemptions_count = _revive_redemptions_count(trainer)
    try:
        used_items = list_inventory(trainer, status="used", limit=300)
        inventory_count = sum(
            1
            for row in (used_items or [])
            if len(row) > 1 and _eq_item(row[1], "Revivir Pokemon")
        )
    except Exception:
        inventory_count = 0
    return max(redemptions_count, inventory_count)


@_cache_data(ttl=15)
def _revive_redemptions_count(trainer: str) -> int:
    try:
        redemptions = list_redemptions(trainer, limit=1000)
    except Exception:
        return 0

    total = 0
    for row in redemptions or []:
        item = str(row[3] if len(row) > 3 else "")
        payload_raw = row[4] if len(row) > 4 else None
        payload_type = ""
        if isinstance(payload_raw, str) and payload_raw.strip():
            try:
                payload = json.loads(payload_raw)
                if isinstance(payload, dict):
                    payload_type = str(payload.get("type") or "")
            except Exception:
                payload_type = ""
        if _eq_item(item, "Revivir Pokemon") or payload_type == "revive":
            total += 1
    return total


def _wins_losses(players: list[str], results: dict[tuple[str, str], str]) -> dict:
    records = wins_losses(players, results)
    return {player: {"W": record.wins, "L": record.losses} for player, record in records.items()}


def _h2h(p1: str, p2: str, results: dict[tuple[str, str], str]) -> str | None:
    return head_to_head(p1, p2, results)


def _rank(players: list[str], results: dict[tuple[str, str], str]) -> list[str]:
    dead_counts = {player: _count_muertos_for_trainer(player) for player in players}
    return rank_division(players, results, dead_counts=dead_counts)


def all_filled(md: dict[tuple[str, str], str | None]) -> bool:
    return domain_all_matches_filled(md)


def _record_position(tramo: int, user: str, pos: int) -> None:
    st.session_state.league_results.setdefault(user, {})[tramo] = pos


def _persist_state() -> None:
    from app.liga.state import persist_state

    persist_state()


def _current_actor(admin_user: str | None = None) -> str | None:
    if admin_user is not None:
        return admin_user
    try:
        return st.session_state.get("user")
    except Exception:
        return None


def _penalties_for_snapshot(players: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for player in players:
        try:
            dead_count = _count_muertos_for_trainer(player)
        except Exception:
            dead_count = 0
        try:
            penalties = get_user_penalties(player)
        except Exception:
            penalties = {}
        out[player] = {
            "dead_count": dead_count,
            "points_reduction": float(penalties.get("points_reduction") or 0.0),
            "coins_reduction": int(penalties.get("coins_reduction") or 0),
            "store_blocked": bool(penalties.get("store_blocked")),
            "trainer_status": trainer_status(player),
            "trainer_status_labels": status_labels_for(player),
        }
    return out


def _store_round_snapshot(
    *,
    tramo: int,
    division_snapshot: dict[str, list[str]],
    rank_a: list[str],
    rank_b: list[str],
    source: str,
    previous_snapshot: dict | None = None,
) -> dict:
    players = list(rank_a) + list(rank_b)
    snapshot = build_matchday_snapshot(
        round_no=int(tramo),
        division_snapshot=division_snapshot,
        rank_a=list(rank_a),
        rank_b=list(rank_b),
        season_version=current_season_version(int(tramo)),
        penalties_by_user=_penalties_for_snapshot(players),
        previous_snapshot=previous_snapshot,
        source=source,
    )
    snapshots = dict(st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {}) or {})
    snapshots[int(tramo)] = snapshot
    st.session_state[ROUND_SNAPSHOTS_STATE_KEY] = snapshots
    return snapshot


def _round_has_recorded_results(tramo: int) -> bool:
    for round_map in (st.session_state.get("league_results", {}) or {}).values():
        if not isinstance(round_map, dict):
            continue
        try:
            if int(tramo) in {int(key) for key in round_map.keys()}:
                return True
        except Exception:
            continue
    return False


def finalize(tramo: int, *, admin_user: str | None = None) -> None:
    require_league_admin(_current_actor(admin_user))
    if snapshot_for_round(st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {}), tramo):
        raise ValueError("Esta jornada ya tiene snapshot oficial cerrado.")
    if _round_has_recorded_results(int(tramo)):
        raise ValueError(
            "Esta jornada ya tiene resultados oficiales. Usa modificar jornada anterior."
        )
    data = get_matches_for(tramo)
    A_players = list(st.session_state.league_divisions["A"])
    B_players = list(st.session_state.league_divisions["B"])
    if not all_filled(data["A"]) or not all_filled(data["B"]):
        raise ValueError("Faltan resultados por marcar en A o B.")
    rankA = _rank(A_players, data["A"])
    rankB = _rank(B_players, data["B"])
    start_b = len(A_players) + 1
    for i, u in enumerate(rankA, start=1):
        _record_position(tramo, u, i)
    for j, u in enumerate(rankB, start=start_b):
        _record_position(tramo, u, j)

    _store_round_snapshot(
        tramo=int(tramo),
        division_snapshot={"A": A_players, "B": B_players},
        rank_a=rankA,
        rank_b=rankB,
        source="finalize",
    )

    try:
        if rankB and season_rule_enabled("last_b_gets_steal", int(tramo)):
            last_user = rankB[-1]
            add_purchase(last_user, "Robar Pokemon", 0)
            try:
                st.toast(f"Comodin entregado a {last_user}: Robar Pokemon")
            except Exception:
                pass
    except Exception:
        pass

    if tramo < max_jornadas(tramo):
        nueva_A, nueva_B, up, down = next_divisions_from_rankings(
            rankA,
            rankB,
            round_no=tramo,
        )
        st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}
        try:
            st.session_state.league_movements[tramo] = {"up": up, "down": down}
        except Exception:
            pass
    else:
        try:
            st.session_state.setdefault("league_movements", {}).pop(tramo, None)
        except Exception:
            pass
    st.session_state.league_active = False
    st.session_state.league_tramo = tramo + 1
    _persist_state()


def recompute_round(
    tramo: int,
    *,
    apply_divisions_from_round: bool = False,
    admin_user: str | None = None,
) -> None:
    require_league_admin(_current_actor(admin_user))
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

    previous_snapshot = snapshot_for_round(
        st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {}),
        int(tramo),
    )
    _store_round_snapshot(
        tramo=int(tramo),
        division_snapshot={"A": A_players, "B": B_players},
        rank_a=rankA,
        rank_b=rankB,
        source="recompute_round",
        previous_snapshot=previous_snapshot,
    )

    if tramo < max_jornadas(tramo):
        try:
            _nueva_A, _nueva_B, up, down = next_divisions_from_rankings(
                rankA,
                rankB,
                round_no=tramo,
            )
            st.session_state.setdefault("league_movements", {})
            st.session_state.league_movements[tramo] = {
                "up": up,
                "down": down,
            }
        except Exception:
            pass
    else:
        try:
            st.session_state.setdefault("league_movements", {}).pop(tramo, None)
        except Exception:
            pass

    if apply_divisions_from_round and tramo < max_jornadas(tramo):
        nueva_A, nueva_B, _up, _down = next_divisions_from_rankings(
            rankA,
            rankB,
            round_no=tramo,
        )
        st.session_state.league_divisions = {"A": nueva_A, "B": nueva_B}

    _persist_state()


def points_from_league(user: str) -> int:
    if user not in _visible_league_users():
        return 0
    lr = st.session_state.get("league_results", {})
    tramos = lr.get(user, {})
    total = 0
    snapshot_awards = snapshot_awards_for_user(
        st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {}),
        user,
        "points_awarded",
    )
    covered_rounds: set[int] = set()
    for tramo, points in snapshot_awards.items():
        if not counts_for_league_reward(user, int(tramo)):
            continue
        total += int(points)
        covered_rounds.add(int(tramo))
    for tramo, pos in tramos.items():
        if int(tramo) in covered_rounds:
            continue
        if not counts_for_league_reward(user, int(tramo)):
            continue
        total += points_for_league_position(int(tramo), int(pos))
    return total


def _one_decimal(x: float) -> float:
    return one_decimal(x)


def current_points_total(
    user: str,
    *,
    raw_dead_count: int | None = None,
    penalties: dict | None = None,
) -> float:
    if user not in _visible_league_users():
        return 0.0
    base = points_from_league(user)
    snapshot_penalties = latest_snapshot_penalties_for_user(
        st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {}),
        user,
    )
    if snapshot_penalties is not None:
        dead_points_penalty = float(snapshot_penalties.get("dead_points_penalty") or 0.0)
        points_reduction = float(snapshot_penalties.get("points_reduction") or 0.0)
        total = base - dead_points_penalty - points_reduction
        return _one_decimal(total)

    muertos = _count_muertos_for_trainer(user, raw_dead_count=raw_dead_count)
    penalties = penalties if penalties is not None else get_user_penalties(user)
    points_reduction = float(penalties.get("points_reduction") or 0.0)
    return total_points_with_penalties(
        base,
        dead_count=muertos,
        points_reduction=points_reduction,
    )


def general_table_sorted() -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    active_names = set(_visible_league_users().keys())
    for user in active_names:
        try:
            snapshot = get_trainer_snapshot(user)
            raw_dead_count = int(snapshot.get("dead_count") or 0)
        except Exception:
            raw_dead_count = None
        rows.append((user, current_points_total(user, raw_dead_count=raw_dead_count)))
    active_rows = sorted(rows, key=lambda x: (-x[1], x[0]))
    retired_rows = [
        (user, 0.0)
        for user in USERS.keys()
        if user not in active_names and user in retired_trainers()
    ]
    return active_rows + retired_rows


def final_podium() -> list[tuple[str, float]]:
    return general_table_sorted()[:3]


def clear_ranking_caches() -> None:
    for func in (
        _latest_save_path,
        _muertos_from_save,
        _used_revives_count,
        _revive_redemptions_count,
        cached_dead_count,
    ):
        try:
            func.clear()
        except Exception:
            continue
    clear_trainer_snapshot_runtime_caches()
