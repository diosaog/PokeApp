from __future__ import annotations

from typing import Any

from app.domain.activity import ActivityEvent, ActivityEventType
from app.domain.common import Visibility, epoch_to_utc_iso
from app.domain.league import LeagueStanding, MatchdaySnapshot, PenaltySummary
from app.domain.pokemon import PokemonMove, PrivatePokemon, PublicPokemon, StatSpread
from app.domain.saves import BoxSlot, PokemonBox
from app.domain.seasons import SeasonMetadata, SeasonRules, SeasonVersion
from app.domain.team_locks import TeamLock
from app.domain.trainers import TrainerStatus


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _stat_spread(raw: Any) -> StatSpread | None:
    if not isinstance(raw, dict):
        return None
    return StatSpread(
        hp=_int(raw.get("hp")),
        atk=_int(raw.get("atk")),
        defense=_int(raw.get("def") if "def" in raw else raw.get("defense")),
        spa=_int(raw.get("spa")),
        spd=_int(raw.get("spd")),
        spe=_int(raw.get("spe")),
    )


def pokemon_from_legacy(raw: dict[str, Any], *, private: bool = False) -> PublicPokemon:
    moves_raw = raw.get("moves_detail") if isinstance(raw.get("moves_detail"), list) else []
    if not moves_raw:
        moves_raw = raw.get("moves") if isinstance(raw.get("moves"), list) else []
    moves: list[PokemonMove] = []
    for move in moves_raw[:4]:
        if isinstance(move, dict):
            name = _text(move.get("name") or move.get("Name"))
            if name:
                moves.append(PokemonMove(name=name, move_id=move.get("id") or move.get("MoveId"), pp=move.get("pp") or move.get("PP")))
        else:
            name = _text(move)
            if name:
                moves.append(PokemonMove(name=name))

    base = {
        "id": _text(raw.get("fingerprint") or raw.get("id")),
        "species": _text(raw.get("species_name") or raw.get("species") or raw.get("name")),
        "nickname": _text(raw.get("nickname")),
        "level": _int(raw.get("level"), 0) if raw.get("level") not in (None, "") else None,
        "gender": _text(raw.get("gender")),
        "types": tuple(_text(t) for t in (raw.get("types") if isinstance(raw.get("types"), list) else []) if _text(t)),
        "item": _text(raw.get("held_item") or raw.get("item") or raw.get("Item")),
        "moves": tuple(moves),
        "form_name": _text(raw.get("form_name")),
        "form_index": raw.get("form_index"),
        "is_shiny": bool(raw.get("is_shiny")),
    }
    if not private:
        return PublicPokemon(**base)
    return PrivatePokemon(
        **base,
        ability=_text(raw.get("ability") or raw.get("Ability")),
        nature=_text(raw.get("nature") or raw.get("Nature")),
        ivs=_stat_spread(raw.get("ivs")),
        evs=_stat_spread(raw.get("evs")),
        original_trainer=_text(raw.get("ot_name") or raw.get("OT_Name")),
    )


def season_version_from_legacy(raw: dict[str, Any], *, season_id: str = "legacy-season") -> SeasonVersion:
    rules_raw = raw.get("rules") if isinstance(raw.get("rules"), dict) else {}
    return SeasonVersion(
        id=_text(raw.get("id")) or "legacy-version",
        season_id=season_id,
        name=_text(raw.get("name")) or "Temporada legacy",
        effective_matchday=max(1, _int(raw.get("effective_round"), 1)),
        max_matchdays=max(1, _int(raw.get("max_rounds"), 1)),
        participant_ids=tuple(_text(player) for player in raw.get("players", []) if _text(player)),
        division_sizes=tuple(_int(size) for size in raw.get("division_sizes", []) if _int(size) >= 0),
        promotion_relegation_count=max(0, _int(raw.get("movement_count"), 0)),
        points_by_position={_int(k): _int(v) for k, v in (raw.get("points_by_position") or {}).items() if _int(k) > 0},
        coins_by_position={_int(k): _int(v) for k, v in (raw.get("coins_by_position") or {}).items() if _int(k) > 0},
        rules=SeasonRules(
            team_lock_required=bool(rules_raw.get("team_lock_required", True)),
            last_b_gets_steal=bool(rules_raw.get("last_b_gets_steal", True)),
        ),
        metadata=SeasonMetadata(cup_is_separate=bool(rules_raw.get("cup_is_separate", True))),
    )


def trainer_status_from_legacy(value: Any) -> TrainerStatus:
    raw = _text(value).lower()
    aliases = {
        "active": TrainerStatus.ACTIVE,
        "retired": TrainerStatus.RETIRED,
        "abandoned": TrainerStatus.ABANDONED,
        "disqualified": TrainerStatus.DISQUALIFIED,
    }
    return aliases.get(raw, TrainerStatus.ACTIVE)


def activity_event_from_legacy(raw: dict[str, Any]) -> ActivityEvent:
    type_map = {
        "SAVE_UPLOADED": ActivityEventType.SAVE_UPLOADED,
        "PURCHASE_COMPLETED": ActivityEventType.PURCHASE_COMPLETED,
        "TEAM_LOCKED": ActivityEventType.TEAM_LOCKED,
    }
    visibility_map = {
        "public": Visibility.PUBLIC,
        "trainer-only": Visibility.OWNER,
        "admin-only": Visibility.ADMIN,
    }
    event_type = type_map.get(_text(raw.get("type")).upper(), ActivityEventType.SAVE_UPLOADED)
    return ActivityEvent(
        id=_text(raw.get("id")) or f"legacy:{_text(raw.get('dedupe_key'))}",
        type=event_type,
        created_at=epoch_to_utc_iso(raw.get("created_at")) or _text(raw.get("created_at")),
        actor_id=_text(raw.get("actor")),
        trainer_id=_text(raw.get("trainer")),
        context=dict(raw.get("context") or {}),
        payload=dict(raw.get("payload") or {}),
        visibility=visibility_map.get(_text(raw.get("visibility")), Visibility.PUBLIC),
        dedupe_key=_text(raw.get("dedupe_key")) or _text(raw.get("id")),
        schema_version=max(1, _int(raw.get("schema_version"), 1)),
    )


def box_from_legacy(
    *,
    box_number: int,
    name: str,
    pokemon_rows: list[dict[str, Any]],
    capacity: int = 30,
) -> PokemonBox:
    slots: list[BoxSlot | None] = [None] * capacity
    overflow: list[PrivatePokemon] = []
    for row in pokemon_rows:
        mon = pokemon_from_legacy(row, private=True)
        raw_slot = row.get("slot_index")
        if raw_slot is None:
            raw_slot = row.get("SlotIndex", row.get("slot", row.get("Slot")))
        slot_number = _int(raw_slot, 0) + 1
        if 1 <= slot_number <= capacity and slots[slot_number - 1] is None:
            slots[slot_number - 1] = BoxSlot(box_number=box_number, slot_number=slot_number, pokemon=mon)
        else:
            overflow.append(mon)
    for mon in overflow:
        for idx, slot in enumerate(slots):
            if slot is None:
                slots[idx] = BoxSlot(box_number=box_number, slot_number=idx + 1, pokemon=mon)
                break
    completed = [
        slot if slot is not None else BoxSlot(box_number=box_number, slot_number=idx + 1)
        for idx, slot in enumerate(slots)
    ]
    return PokemonBox(box_number=box_number, name=name, slots=tuple(completed), capacity=capacity)


def team_lock_from_legacy(
    raw: dict[str, Any],
    *,
    season_id: str = "legacy-season",
) -> TeamLock:
    matchday_number = max(1, _int(raw.get("jornada") or raw.get("matchday_number"), 1))
    trainer_id = _text(raw.get("user") or raw.get("trainer_id"))
    team = tuple(
        pokemon_from_legacy(item, private=False)
        for item in (raw.get("team") if isinstance(raw.get("team"), list) else [])
        if isinstance(item, dict)
    )
    return TeamLock(
        id=_text(raw.get("id")) or f"{season_id}:team-lock:{matchday_number}:{trainer_id}",
        season_id=season_id,
        trainer_id=trainer_id,
        locked_at=epoch_to_utc_iso(raw.get("locked_at")) or _text(raw.get("locked_at")),
        team=team,
        matchday_id=_text(raw.get("matchday_id")) or f"{season_id}:matchday:{matchday_number}",
        matchday_number=matchday_number,
        save_record_id=_text(raw.get("save_id") or raw.get("save_record_id")),
        save_sha256=_text(raw.get("save_sha256")),
        deadline_at=epoch_to_utc_iso(raw.get("deadline_at")) or _text(raw.get("deadline_at")),
        is_late=bool(raw.get("is_late")),
    )


def matchday_snapshot_from_legacy(
    raw: dict[str, Any],
    *,
    season_id: str = "legacy-season",
) -> MatchdaySnapshot:
    number = max(1, _int(raw.get("round_no"), 1))
    config = season_version_from_legacy(
        dict(raw.get("season_config_version") or {}),
        season_id=season_id,
    )
    matchday_id = f"{season_id}:matchday:{number}"
    standings: list[LeagueStanding] = []
    penalties: dict[str, PenaltySummary] = {}
    for row in raw.get("standings") or []:
        if not isinstance(row, dict):
            continue
        trainer_id = _text(row.get("user"))
        if not trainer_id:
            continue
        pen_raw = row.get("penalties") if isinstance(row.get("penalties"), dict) else {}
        penalty = PenaltySummary(
            dead_count=_int(pen_raw.get("dead_count")),
            dead_points_penalty=_float(pen_raw.get("dead_points_penalty")),
            points_reduction=_float(pen_raw.get("points_reduction")),
            coins_reduction=_int(pen_raw.get("coins_reduction")),
            store_blocked=bool(pen_raw.get("store_blocked")),
            trainer_status=trainer_status_from_legacy(pen_raw.get("trainer_status")),
            trainer_status_labels=tuple(_text(label) for label in pen_raw.get("trainer_status_labels", []) if _text(label)),
        )
        penalties[trainer_id] = penalty
        division_id = _text(row.get("division")) or "A"
        standings.append(
            LeagueStanding(
                matchday_id=matchday_id,
                trainer_id=trainer_id,
                division_id=division_id,
                position=max(1, _int(row.get("position"), 1)),
                division_position=max(1, _int(row.get("division_position"), 1)),
                points_awarded=max(0, _int(row.get("points_awarded"))),
                coins_awarded=max(0, _int(row.get("coins_awarded"))),
                penalties=penalty,
            )
        )
    composition = {
        _text(division): tuple(_text(player) for player in players if _text(player))
        for division, players in (raw.get("division_snapshot") or {}).items()
        if _text(division) and isinstance(players, list)
    }
    return MatchdaySnapshot(
        id=f"{matchday_id}:snapshot",
        schema_version=max(1, _int(raw.get("schema_version"), 1)),
        matchday_id=matchday_id,
        season_id=season_id,
        matchday_number=number,
        closed_at=epoch_to_utc_iso(raw.get("closed_at")) or _text(raw.get("closed_at")),
        season_version=config,
        division_composition=composition,
        standings=tuple(standings),
        points_awarded={_text(k): max(0, _int(v)) for k, v in (raw.get("points_awarded") or {}).items() if _text(k)},
        coins_awarded={_text(k): max(0, _int(v)) for k, v in (raw.get("coins_awarded") or {}).items() if _text(k)},
        penalties=penalties,
        metadata=dict(raw.get("metadata") or {}),
    )
