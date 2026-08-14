from __future__ import annotations

import time
from typing import Any

from app.season.config import SeasonVersion, season_version_to_dict


SNAPSHOT_SCHEMA_VERSION = 1
ROUND_SNAPSHOTS_STATE_KEY = "league_round_snapshots"
ROUND_SNAPSHOTS_SERIALIZED_KEY = "round_snapshots"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _int_map(raw: Any) -> dict[int, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[int, int] = {}
    for key, value in raw.items():
        pos = _as_int(key, 0)
        if pos > 0:
            out[pos] = _as_int(value, 0)
    return out


def _config_snapshot(version: SeasonVersion | dict[str, Any]) -> dict[str, Any]:
    if isinstance(version, SeasonVersion):
        return season_version_to_dict(version)
    if not isinstance(version, dict):
        return {}
    return dict(version)


def _reward_from_config(config: dict[str, Any], field: str, position: int) -> int:
    rewards = _int_map(config.get(field))
    return int(rewards.get(int(position), 0))


def _clean_penalty(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    dead_count = max(_as_int(data.get("dead_count"), 0), 0)
    points_reduction = _as_float(data.get("points_reduction"), 0.0)
    coins_reduction = _as_int(data.get("coins_reduction"), 0)
    return {
        "dead_count": dead_count,
        "dead_points_penalty": round(0.2 * dead_count, 1),
        "points_reduction": points_reduction,
        "coins_reduction": coins_reduction,
        "store_blocked": bool(data.get("store_blocked")),
    }


def _standing_row(
    *,
    user: str,
    division: str,
    division_position: int,
    position: int,
    config: dict[str, Any],
    penalties: dict[str, Any],
) -> dict[str, Any]:
    points = _reward_from_config(config, "points_by_position", position)
    coins = _reward_from_config(config, "coins_by_position", position)
    return {
        "user": str(user),
        "division": str(division),
        "division_position": int(division_position),
        "position": int(position),
        "points_awarded": int(points),
        "coins_awarded": int(coins),
        "penalties": _clean_penalty(penalties),
    }


def build_matchday_snapshot(
    *,
    round_no: int,
    division_snapshot: dict[str, list[str]],
    rank_a: list[str],
    rank_b: list[str],
    season_version: SeasonVersion | dict[str, Any],
    penalties_by_user: dict[str, dict[str, Any]] | None = None,
    closed_at: int | None = None,
    previous_snapshot: dict[str, Any] | None = None,
    source: str = "finalize",
) -> dict[str, Any]:
    config = (
        _config_snapshot(previous_snapshot.get("season_config_version"))
        if isinstance(previous_snapshot, dict)
        and isinstance(previous_snapshot.get("season_config_version"), dict)
        else _config_snapshot(season_version)
    )
    penalties_by_user = penalties_by_user or {}
    closed_ts = int(closed_at if closed_at is not None else time.time())

    standings: list[dict[str, Any]] = []
    for idx, user in enumerate(rank_a, start=1):
        standings.append(
            _standing_row(
                user=user,
                division="A",
                division_position=idx,
                position=idx,
                config=config,
                penalties=penalties_by_user.get(user, {}),
            )
        )

    start_b = len(rank_a) + 1
    for idx, user in enumerate(rank_b, start=1):
        standings.append(
            _standing_row(
                user=user,
                division="B",
                division_position=idx,
                position=start_b + idx - 1,
                config=config,
                penalties=penalties_by_user.get(user, {}),
            )
        )

    points_awarded = {
        row["user"]: int(row["points_awarded"]) for row in standings
    }
    coins_awarded = {
        row["user"]: int(row["coins_awarded"]) for row in standings
    }
    penalties = {row["user"]: dict(row["penalties"]) for row in standings}

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "round_no": int(round_no),
        "closed_at": closed_ts,
        "season_config_version": config,
        "division_snapshot": {
            "A": [str(user) for user in division_snapshot.get("A", [])],
            "B": [str(user) for user in division_snapshot.get("B", [])],
        },
        "standings": standings,
        "points_awarded": points_awarded,
        "coins_awarded": coins_awarded,
        "penalties": penalties,
        "metadata": {
            "source": str(source or "finalize"),
            "config_version_id": str(config.get("id") or ""),
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        },
    }


def normalize_round_snapshots(raw: Any) -> dict[int, dict[str, Any]]:
    source = raw if isinstance(raw, dict) else {}
    out: dict[int, dict[str, Any]] = {}
    for raw_round, raw_snapshot in source.items():
        if not isinstance(raw_snapshot, dict):
            continue
        round_no = _as_int(raw_round or raw_snapshot.get("round_no"), 0)
        if round_no <= 0:
            continue
        snapshot = dict(raw_snapshot)
        snapshot["round_no"] = _as_int(snapshot.get("round_no"), round_no)
        snapshot["schema_version"] = _as_int(
            snapshot.get("schema_version"),
            SNAPSHOT_SCHEMA_VERSION,
        )
        snapshot["standings"] = [
            dict(row)
            for row in (snapshot.get("standings") or [])
            if isinstance(row, dict) and str(row.get("user") or "").strip()
        ]
        out[round_no] = snapshot
    return out


def serialize_round_snapshots(raw: Any) -> dict[str, dict[str, Any]]:
    return {
        str(round_no): snapshot
        for round_no, snapshot in sorted(normalize_round_snapshots(raw).items())
    }


def snapshot_for_round(
    round_snapshots: Any,
    round_no: int,
) -> dict[str, Any] | None:
    return normalize_round_snapshots(round_snapshots).get(int(round_no))


def snapshot_awards_for_user(
    round_snapshots: Any,
    user: str,
    field: str,
) -> dict[int, int]:
    key = str(user or "").strip()
    if not key:
        return {}
    out: dict[int, int] = {}
    for round_no, snapshot in normalize_round_snapshots(round_snapshots).items():
        awards = snapshot.get(field) if isinstance(snapshot.get(field), dict) else {}
        if key in awards:
            out[round_no] = _as_int(awards.get(key), 0)
            continue
        for row in snapshot.get("standings") or []:
            if not isinstance(row, dict) or str(row.get("user") or "") != key:
                continue
            award_key = "points_awarded" if field == "points_awarded" else "coins_awarded"
            out[round_no] = _as_int(row.get(award_key), 0)
            break
    return out


def snapshot_standings(
    round_snapshots: Any,
    round_no: int,
) -> list[dict[str, Any]]:
    snapshot = snapshot_for_round(round_snapshots, round_no)
    if not snapshot:
        return []
    rows = [
        dict(row)
        for row in snapshot.get("standings") or []
        if isinstance(row, dict) and str(row.get("user") or "").strip()
    ]
    return sorted(rows, key=lambda row: (_as_int(row.get("position"), 0), str(row.get("user") or "")))
