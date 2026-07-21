from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from typing import Any

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

from storage import settings_get, settings_set

SEASON_CONFIG_KEY = "season_config_v2"
DEFAULT_SEASON_NAME = "Temporada actual"
DEFAULT_MAX_ROUNDS = 4
DEFAULT_DIVISION_COUNT = 2
DEFAULT_DIVISION_SIZES = [5, 5]
DEFAULT_MOVEMENT_COUNT = 3

DEFAULT_POINTS_BY_POSITION = {
    1: 9,
    2: 8,
    3: 7,
    4: 6,
    5: 5,
    6: 5,
    7: 4,
    8: 3,
    9: 2,
    10: 1,
}

DEFAULT_COINS_BY_POSITION = {
    1: 15,
    2: 14,
    3: 12,
    4: 11,
    5: 10,
    6: 11,
    7: 9,
    8: 8,
    9: 6,
    10: 4,
}


@dataclass(frozen=True)
class SeasonVersion:
    id: str
    name: str
    effective_round: int
    max_rounds: int
    players: list[str]
    division_count: int
    division_sizes: list[int]
    movement_count: int
    points_by_position: dict[int, int]
    coins_by_position: dict[int, int]
    rules: dict[str, Any]


def _cache_data(ttl: int = 10):
    if st is None:
        return lambda f: f
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clean_players(values: Any, fallback: list[str] | tuple[str, ...] | None = None) -> list[str]:
    out: list[str] = []
    source = values if isinstance(values, list) else list(fallback or [])
    for value in source:
        name = str(value or "").strip()
        if name and name not in out:
            out.append(name)
    return out


def _clean_int_map(values: Any, fallback: dict[int, int]) -> dict[int, int]:
    source = values if isinstance(values, dict) else fallback
    out: dict[int, int] = {}
    for key, value in source.items():
        pos = _as_int(key, 0)
        if pos <= 0:
            continue
        out[pos] = max(0, _as_int(value, 0))
    if not out:
        out = dict(fallback)
    return dict(sorted(out.items()))


def _clean_int_list(values: Any, fallback: list[int]) -> list[int]:
    source = values if isinstance(values, list) else fallback
    out = [max(0, _as_int(value, 0)) for value in source]
    return out or list(fallback)


def default_season_version(
    *,
    players: list[str] | tuple[str, ...] | None = None,
    effective_round: int = 1,
) -> SeasonVersion:
    return SeasonVersion(
        id="default",
        name=DEFAULT_SEASON_NAME,
        effective_round=max(1, int(effective_round or 1)),
        max_rounds=DEFAULT_MAX_ROUNDS,
        players=_clean_players(players),
        division_count=DEFAULT_DIVISION_COUNT,
        division_sizes=list(DEFAULT_DIVISION_SIZES),
        movement_count=DEFAULT_MOVEMENT_COUNT,
        points_by_position=dict(DEFAULT_POINTS_BY_POSITION),
        coins_by_position=dict(DEFAULT_COINS_BY_POSITION),
        rules={
            "team_lock_required": True,
            "last_b_gets_steal": True,
            "cup_is_separate": True,
        },
    )


def _season_version_from_mapping(
    raw: Any,
    *,
    fallback_players: list[str] | tuple[str, ...] | None = None,
) -> SeasonVersion:
    fallback = default_season_version(players=fallback_players)
    data = raw if isinstance(raw, dict) else {}
    division_count = max(1, _as_int(data.get("division_count"), fallback.division_count))
    division_sizes = _clean_int_list(data.get("division_sizes"), fallback.division_sizes)
    if len(division_sizes) < division_count:
        division_sizes = division_sizes + [0] * (division_count - len(division_sizes))
    rules = data.get("rules") if isinstance(data.get("rules"), dict) else fallback.rules
    return SeasonVersion(
        id=str(data.get("id") or fallback.id),
        name=str(data.get("name") or fallback.name),
        effective_round=max(1, _as_int(data.get("effective_round"), fallback.effective_round)),
        max_rounds=max(1, _as_int(data.get("max_rounds"), fallback.max_rounds)),
        players=_clean_players(data.get("players"), fallback.players),
        division_count=division_count,
        division_sizes=division_sizes[:division_count],
        movement_count=max(0, _as_int(data.get("movement_count"), fallback.movement_count)),
        points_by_position=_clean_int_map(
            data.get("points_by_position"),
            fallback.points_by_position,
        ),
        coins_by_position=_clean_int_map(
            data.get("coins_by_position"),
            fallback.coins_by_position,
        ),
        rules=dict(rules),
    )


def season_version_to_dict(version: SeasonVersion) -> dict[str, Any]:
    data = asdict(version)
    data["points_by_position"] = {
        str(key): int(value) for key, value in version.points_by_position.items()
    }
    data["coins_by_position"] = {
        str(key): int(value) for key, value in version.coins_by_position.items()
    }
    return data


def default_season_document(
    *,
    players: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    version = default_season_version(players=players)
    return {
        "schema_version": 1,
        "active_version_id": version.id,
        "versions": [season_version_to_dict(version)],
    }


def coerce_season_document(
    raw: Any,
    *,
    fallback_players: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    raw_versions = data.get("versions") if isinstance(data.get("versions"), list) else []
    versions = [
        _season_version_from_mapping(version, fallback_players=fallback_players)
        for version in raw_versions
    ]
    if not versions:
        versions = [default_season_version(players=fallback_players)]
    versions = sorted(versions, key=lambda version: (version.effective_round, version.id))
    active_id = str(data.get("active_version_id") or versions[-1].id)
    if active_id not in {version.id for version in versions}:
        active_id = versions[-1].id
    return {
        "schema_version": 1,
        "active_version_id": active_id,
        "versions": [season_version_to_dict(version) for version in versions],
    }


def _parse_raw_document(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


@_cache_data(ttl=10)
def _load_season_document_cached(raw: str | None, players_key: str) -> dict[str, Any]:
    fallback_players = [player for player in players_key.split("\n") if player]
    return coerce_season_document(
        _parse_raw_document(raw),
        fallback_players=fallback_players,
    )


def load_season_document(
    *,
    players: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    try:
        raw = settings_get(SEASON_CONFIG_KEY)
    except Exception:
        raw = None
    players_key = "\n".join(_clean_players(players))
    return _load_season_document_cached(raw, players_key)


def _versions_from_document(document: dict[str, Any]) -> list[SeasonVersion]:
    return [
        _season_version_from_mapping(version)
        for version in document.get("versions", [])
        if isinstance(version, dict)
    ]


def season_version_for_round(
    document: dict[str, Any],
    round_no: int | None = None,
) -> SeasonVersion:
    versions = _versions_from_document(document)
    if not versions:
        return default_season_version()
    versions = sorted(versions, key=lambda version: (version.effective_round, version.id))
    if round_no is None:
        active_id = str(document.get("active_version_id") or "")
        for version in reversed(versions):
            if version.id == active_id:
                return version
        return versions[-1]
    round_i = max(1, int(round_no or 1))
    selected = versions[0]
    for version in versions:
        if version.effective_round <= round_i:
            selected = version
        else:
            break
    return selected


def current_season_version(round_no: int | None = None) -> SeasonVersion:
    return season_version_for_round(load_season_document(), round_no)


def max_rounds(round_no: int | None = None) -> int:
    return int(current_season_version(round_no).max_rounds)


def division_a_size(player_count: int, round_no: int | None = None) -> int:
    total = max(0, int(player_count or 0))
    if total <= 0:
        return 0
    version = current_season_version(round_no)
    first_size = version.division_sizes[0] if version.division_sizes else DEFAULT_DIVISION_SIZES[0]
    return min(max(0, int(first_size)), total)


def movement_count(a_size: int, b_size: int, round_no: int | None = None) -> int:
    if a_size <= 0 or b_size <= 0:
        return 0
    count = int(current_season_version(round_no).movement_count)
    return min(max(0, count), int(a_size), int(b_size))


def points_for_position(round_no: int, pos: int) -> int:
    return current_season_version(round_no).points_by_position.get(int(pos), 0)


def coins_for_position(round_no: int, pos: int) -> int:
    return current_season_version(round_no).coins_by_position.get(int(pos), 0)


def save_season_version(
    version: SeasonVersion,
    *,
    effective_round: int,
) -> dict[str, Any]:
    document = load_season_document(players=version.players)
    version_data = season_version_to_dict(
        SeasonVersion(
            **{
                **asdict(version),
                "id": f"v{int(time.time() * 1000)}",
                "effective_round": max(1, int(effective_round or 1)),
            }
        )
    )
    existing_versions = [
        item for item in document.get("versions", []) if isinstance(item, dict)
    ]
    existing_versions.append(version_data)
    saved = coerce_season_document(
        {
            "schema_version": 1,
            "active_version_id": version_data["id"],
            "versions": existing_versions,
        },
        fallback_players=version.players,
    )
    settings_set(SEASON_CONFIG_KEY, json.dumps(saved, ensure_ascii=False))
    clear_season_config_cache()
    return saved


def clear_season_config_cache() -> None:
    try:
        _load_season_document_cached.clear()
    except Exception:
        pass
