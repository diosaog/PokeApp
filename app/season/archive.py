from __future__ import annotations

import hashlib
import json
import time
from typing import Any

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

from app.entrenadores.trainer_flags import (
    TRAINER_STATUS_ACTIVE,
    all_trainer_flags,
)
from app.liga.permissions import require_league_admin
from app.liga.snapshots import normalize_round_snapshots, snapshot_standings
from app.season.config import (
    default_season_document,
    load_season_document,
    season_version_for_round,
)
from storage import list_team_locks, settings_get, settings_set
from utils import USERS


SEASON_ARCHIVES_KEY = "season_archives_v1"
SEASON_LIFECYCLE_KEY = "season_lifecycle_v1"

SEASON_STATE_DRAFT = "draft"
SEASON_STATE_ACTIVE = "active"
SEASON_STATE_FINISHED = "finished"
SEASON_STATE_ARCHIVED = "archived"
SEASON_STATE_DISCARDED = "discarded"

ARCHIVE_SCHEMA_VERSION = 1

EMPTY_LEAGUE_STATE = json.dumps(
    {
        "tramo": 1,
        "active": False,
        "divisions": {"A": [], "B": []},
        "matches": {},
        "results": {},
        "movements": {},
        "round_snapshots": {},
    },
    ensure_ascii=False,
    sort_keys=True,
)

ACTIVE_SEASON_SETTING_DEFAULTS = {
    "league_state": EMPTY_LEAGUE_STATE,
    "trainer_flags": "{}",
    "trainer_robbed_history_watermark": "0",
    "copa_swiss_state": "{}",
    "copa_elim_state": "{}",
    "copa_dobles_state": "{}",
}


def _now() -> int:
    return int(time.time())


def _json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        parsed = json.loads(raw)
    except Exception:
        return fallback
    return parsed


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _stable_digest(value: Any, *, length: int = 14) -> str:
    raw = _json_dumps(value)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


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


def load_season_lifecycle() -> dict[str, Any]:
    raw = _json_loads(settings_get(SEASON_LIFECYCLE_KEY), {})
    data = raw if isinstance(raw, dict) else {}
    state = str(data.get("state") or SEASON_STATE_ACTIVE).strip().lower()
    if state not in {
        SEASON_STATE_DRAFT,
        SEASON_STATE_ACTIVE,
        SEASON_STATE_FINISHED,
        SEASON_STATE_ARCHIVED,
        SEASON_STATE_DISCARDED,
    }:
        state = SEASON_STATE_ACTIVE
    return {
        "schema_version": 1,
        "state": state,
        "started_at": _as_int(data.get("started_at"), 0),
        "finished_at": _as_int(data.get("finished_at"), 0),
        "archived_at": _as_int(data.get("archived_at"), 0),
        "archive_id": _clean_text(data.get("archive_id")),
        "updated_at": _as_int(data.get("updated_at"), 0),
    }


def save_season_lifecycle(lifecycle: dict[str, Any]) -> dict[str, Any]:
    data = load_season_lifecycle()
    data.update(lifecycle if isinstance(lifecycle, dict) else {})
    data["updated_at"] = _now()
    settings_set(SEASON_LIFECYCLE_KEY, json.dumps(data, ensure_ascii=False))
    return data


def load_season_archives() -> list[dict[str, Any]]:
    raw = _json_loads(settings_get(SEASON_ARCHIVES_KEY), [])
    entries = raw if isinstance(raw, list) else []
    clean = [
        dict(entry)
        for entry in entries
        if isinstance(entry, dict) and _clean_text(entry.get("id"))
    ]
    return sorted(clean, key=lambda item: _as_int(item.get("archived_at"), 0), reverse=True)


def _save_season_archives(archives: list[dict[str, Any]]) -> None:
    by_id: dict[str, dict[str, Any]] = {}
    for archive in archives:
        archive_id = _clean_text(archive.get("id"))
        if archive_id:
            by_id[archive_id] = dict(archive)
    out = sorted(by_id.values(), key=lambda item: _as_int(item.get("archived_at"), 0), reverse=True)
    settings_set(SEASON_ARCHIVES_KEY, json.dumps(out, ensure_ascii=False))


def _league_state_from_settings() -> dict[str, Any]:
    data = _json_loads(settings_get("league_state"), {})
    if isinstance(data, dict):
        return dict(data)
    return {}


def _round_snapshots_from_state(league_state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return normalize_round_snapshots(
        league_state.get("round_snapshots")
        or league_state.get("league_round_snapshots")
        or {}
    )


def latest_closed_round(league_state: dict[str, Any] | None = None) -> int:
    state = league_state if isinstance(league_state, dict) else _league_state_from_settings()
    snapshots = _round_snapshots_from_state(state)
    if snapshots:
        return max(int(round_no) for round_no in snapshots)
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    rounds: set[int] = set()
    for round_map in results.values():
        if isinstance(round_map, dict):
            for raw_round in round_map:
                round_no = _as_int(raw_round, 0)
                if round_no > 0:
                    rounds.add(round_no)
    return max(rounds) if rounds else 0


def _participants_from_sources(
    *,
    season_document: dict[str, Any],
    round_no: int,
    snapshots: dict[int, dict[str, Any]],
) -> list[str]:
    version = season_version_for_round(season_document, max(1, int(round_no or 1)))
    participants = []
    for value in version.players or list(USERS.keys()):
        name = _clean_text(value)
        if name and name not in participants:
            participants.append(name)
    for snapshot in snapshots.values():
        for row in snapshot.get("standings") or []:
            if isinstance(row, dict):
                name = _clean_text(row.get("user"))
                if name and name not in participants:
                    participants.append(name)
    return participants


def _trainer_status_archive(participants: list[str]) -> dict[str, dict[str, Any]]:
    flags = all_trainer_flags()
    out: dict[str, dict[str, Any]] = {}
    for trainer in participants:
        data = flags.get(trainer, {}) if isinstance(flags.get(trainer), dict) else {}
        status = str(data.get("status") or data.get("inactive_reason") or "").strip().lower()
        if not status:
            if data.get("abandoned"):
                status = "abandoned"
            elif data.get("disqualified"):
                status = "disqualified"
            elif data.get("retired"):
                status = "retired"
            else:
                status = TRAINER_STATUS_ACTIVE
        out[trainer] = {
            "status": status,
            "inactive_reason": _clean_text(data.get("inactive_reason")),
            "robbed": bool(data.get("robbed")) and status == TRAINER_STATUS_ACTIVE,
        }
    return out


def public_pokemon_snapshot(mon: Any) -> dict[str, Any]:
    data = mon if isinstance(mon, dict) else {}
    moves_source = data.get("moves") if isinstance(data.get("moves"), list) else []
    moves: list[str] = []
    for move in moves_source:
        if isinstance(move, dict):
            name = _clean_text(move.get("name") or move.get("move") or move.get("id"))
        else:
            name = _clean_text(move)
        if name and name not in moves:
            moves.append(name)
    types = [
        _clean_text(value)
        for value in (data.get("types") if isinstance(data.get("types"), list) else [])
        if _clean_text(value)
    ]
    return {
        "species": _clean_text(
            data.get("species_name")
            or data.get("species")
            or data.get("name")
            or data.get("display_name")
        ),
        "nickname": _clean_text(data.get("nickname")),
        "level": _as_int(data.get("level"), 0),
        "gender": _clean_text(data.get("gender")),
        "item": _clean_text(data.get("item")),
        "types": types[:2],
        "moves": moves[:4],
    }


def public_team_snapshot(team: Any) -> list[dict[str, Any]]:
    source = team if isinstance(team, list) else []
    out = [public_pokemon_snapshot(mon) for mon in source[:6]]
    return [mon for mon in out if mon.get("species")]


def _legacy_current_team_snapshot(user: str) -> list[dict[str, Any]]:
    try:
        from app.entrenadores.snapshot import get_trainer_snapshot

        snapshot = get_trainer_snapshot(user, allow_rebuild=False)
    except Exception:
        snapshot = {}
    return public_team_snapshot((snapshot or {}).get("team") or [])


def _team_snapshot_for(
    user: str,
    *,
    final_round: int,
    locks_by_round: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], str]:
    if final_round > 0:
        for lock in locks_by_round.get(int(final_round), []):
            if _clean_text(lock.get("user")) == user and lock.get("team"):
                return public_team_snapshot(lock.get("team")), f"team_lock:{final_round}"
    for round_no in sorted(locks_by_round, reverse=True):
        for lock in locks_by_round.get(round_no, []):
            if _clean_text(lock.get("user")) == user and lock.get("team"):
                return public_team_snapshot(lock.get("team")), f"team_lock:{round_no}"
    team = _legacy_current_team_snapshot(user)
    return team, "trainer_snapshot_legacy" if team else ""


def _collect_team_locks(final_round: int) -> dict[int, list[dict[str, Any]]]:
    locks: dict[int, list[dict[str, Any]]] = {}
    for round_no in range(1, max(0, int(final_round)) + 1):
        try:
            locks[round_no] = [dict(lock) for lock in list_team_locks(round_no)]
        except Exception:
            locks[round_no] = []
    return locks


def _league_summary(
    *,
    league_state: dict[str, Any],
    snapshots: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    awarded_points: dict[str, float] = {}
    coins: dict[str, int] = {}
    round_positions: dict[str, dict[str, int]] = {}
    latest_penalties: dict[str, dict[str, Any]] = {}
    for round_no, snapshot in sorted(snapshots.items()):
        for row in snapshot_standings(snapshots, int(round_no)):
            user = _clean_text(row.get("user"))
            if not user:
                continue
            awarded_points[user] = awarded_points.get(user, 0.0) + _as_float(row.get("points_awarded"), 0.0)
            coins[user] = coins.get(user, 0) + _as_int(row.get("coins_awarded"), 0)
            round_positions.setdefault(user, {})[str(round_no)] = _as_int(row.get("position"), 0)
            if isinstance(row.get("penalties"), dict):
                latest_penalties[user] = dict(row["penalties"])

    def final_points_for(user: str) -> float:
        penalties = latest_penalties.get(user, {})
        return (
            awarded_points.get(user, 0.0)
            - _as_float(penalties.get("dead_points_penalty"), 0.0)
            - _as_float(penalties.get("points_reduction"), 0.0)
        )

    final_points = {user: final_points_for(user) for user in awarded_points}
    standings = [
        {
            "position": idx,
            "user": user,
            "points": round(float(score), 1),
            "coins_awarded": int(coins.get(user, 0)),
            "round_positions": round_positions.get(user, {}),
            "latest_penalties": latest_penalties.get(user, {}),
        }
        for idx, (user, score) in enumerate(
            sorted(final_points.items(), key=lambda item: (-float(item[1]), item[0])),
            start=1,
        )
    ]
    champion = standings[0]["user"] if standings else ""
    runner_up = standings[1]["user"] if len(standings) > 1 else ""
    return {
        "tramo": _as_int(league_state.get("tramo"), 1),
        "active": bool(league_state.get("active")),
        "final_round": latest_closed_round(league_state),
        "divisions": league_state.get("divisions") if isinstance(league_state.get("divisions"), dict) else {},
        "matches": league_state.get("matches") if isinstance(league_state.get("matches"), dict) else {},
        "results": league_state.get("results") if isinstance(league_state.get("results"), dict) else {},
        "movements": league_state.get("movements") if isinstance(league_state.get("movements"), dict) else {},
        "round_snapshots": {str(round_no): snapshot for round_no, snapshot in sorted(snapshots.items())},
        "standings": standings,
        "points_final": {row["user"]: row["points"] for row in standings},
        "coins_awarded": {row["user"]: row["coins_awarded"] for row in standings},
        "champion": champion,
        "runner_up": runner_up,
    }


def _cup_states_from_settings() -> dict[str, Any]:
    keys = {
        "copa_swiss_state": "Copa",
        "copa_elim_state": "Torneo",
        "copa_dobles_state": "Copa Dobles",
    }
    out: dict[str, Any] = {}
    for key, label in keys.items():
        data = _json_loads(settings_get(key), None)
        if isinstance(data, dict) and data:
            out[label] = data
    return out


def _valid_bo3(score_a: Any, score_b: Any) -> bool:
    try:
        return (int(score_a), int(score_b)) in {(2, 0), (2, 1), (1, 2), (0, 2)}
    except Exception:
        return False


def _cup_hall_entries(cup_states: dict[str, Any], *, season_name: str, archived_at: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    swiss = cup_states.get("Copa") if isinstance(cup_states.get("Copa"), dict) else {}
    topcut = swiss.get("topcut") if isinstance(swiss.get("topcut"), dict) else {}
    champion = _clean_text(topcut.get("champion"))
    if champion:
        final = topcut.get("final") if isinstance(topcut.get("final"), list) else []
        runner = ""
        if len(final) == 2 and champion in final:
            runner = str(final[1] if champion == final[0] else final[0])
        source = _clean_text(swiss.get("hall_run_id")) or _stable_digest({"players": swiss.get("players"), "max_rounds": swiss.get("max_rounds")})
        entries.append({
            "id": f"auto:copa-swiss:{source}",
            "competition": "Copa",
            "title": "Copa Suiza",
            "season": season_name,
            "champion": champion,
            "runner_up": runner,
            "team": [],
            "team_snapshot": [],
            "notes": "Campeon del top cut.",
            "created_at": archived_at,
        })

    elim = cup_states.get("Torneo") if isinstance(cup_states.get("Torneo"), dict) else {}
    rounds = elim.get("rounds") if isinstance(elim.get("rounds"), list) else []
    if rounds:
        last_round = rounds[-1] if isinstance(rounds[-1], list) else []
        final = last_round[0] if len(last_round) == 1 and isinstance(last_round[0], dict) else {}
        champion = _clean_text(final.get("winner"))
        if champion:
            p1 = _clean_text(final.get("p1"))
            p2 = _clean_text(final.get("p2"))
            runner = p2 if champion == p1 else p1
            source = _clean_text(elim.get("hall_run_id")) or _stable_digest({"players": elim.get("players"), "round_count": len(rounds)})
            entries.append({
                "id": f"auto:copa-elim:{source}",
                "competition": "Torneo",
                "title": "Eliminatoria Bo3",
                "season": season_name,
                "champion": champion,
                "runner_up": runner,
                "team": [],
                "team_snapshot": [],
                "notes": f"Resultado final: {_clean_text(final.get('score'), '-')}",
                "created_at": archived_at,
            })

    doubles = cup_states.get("Copa Dobles") if isinstance(cup_states.get("Copa Dobles"), dict) else {}
    final = doubles.get("final") if isinstance(doubles.get("final"), dict) else {}
    if _valid_bo3(final.get("score_a"), final.get("score_b")):
        teams = {
            str(team.get("id")): team
            for team in doubles.get("teams", [])
            if isinstance(team, dict) and team.get("id")
        }
        team_a = teams.get(str(final.get("team_a")))
        team_b = teams.get(str(final.get("team_b")))
        if team_a and team_b:
            score_a = _as_int(final.get("score_a"), 0)
            score_b = _as_int(final.get("score_b"), 0)
            champion_team = team_a if score_a > score_b else team_b
            runner_team = team_b if champion_team is team_a else team_a
            members = " + ".join(str(member) for member in champion_team.get("members") or [])
            source = _clean_text(doubles.get("hall_run_id")) or _stable_digest({"teams": doubles.get("teams"), "round_count": len(doubles.get("rounds") or [])})
            entries.append({
                "id": f"auto:copa-dobles:{source}",
                "competition": "Copa Dobles",
                "title": "Copa Dobles",
                "season": season_name,
                "champion": _clean_text(champion_team.get("name"), "Equipo campeon"),
                "runner_up": _clean_text(runner_team.get("name")),
                "team": [],
                "team_snapshot": [],
                "notes": f"Integrantes: {members or '-'} | Final {score_a}-{score_b}",
                "created_at": archived_at,
            })
    return entries


def build_season_archive(
    *,
    label: str | None = None,
    archived_at: int | None = None,
    league_state: dict[str, Any] | None = None,
    season_document: dict[str, Any] | None = None,
    lifecycle: dict[str, Any] | None = None,
    cup_states: dict[str, Any] | None = None,
    locks_by_round: dict[int, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    archived_ts = int(archived_at if archived_at is not None else _now())
    state = league_state if isinstance(league_state, dict) else _league_state_from_settings()
    snapshots = _round_snapshots_from_state(state)
    final_round = latest_closed_round(state)
    document = season_document if isinstance(season_document, dict) else load_season_document(players=list(USERS.keys()))
    version = season_version_for_round(document, max(1, int(final_round or 1)))
    participants = _participants_from_sources(
        season_document=document,
        round_no=final_round,
        snapshots=snapshots,
    )
    trainer_statuses = _trainer_status_archive(participants)
    league = _league_summary(league_state=state, snapshots=snapshots)
    locks = locks_by_round if isinstance(locks_by_round, dict) else _collect_team_locks(final_round)
    cup_state_snapshot = cup_states if isinstance(cup_states, dict) else _cup_states_from_settings()
    life = lifecycle if isinstance(lifecycle, dict) else load_season_lifecycle()
    finished_at = _as_int(life.get("finished_at"), 0) or archived_ts
    season_name = _clean_text(label) or version.name
    champion = _clean_text(league.get("champion"))
    runner = _clean_text(league.get("runner_up"))
    champion_team, champion_team_source = _team_snapshot_for(
        champion,
        final_round=final_round,
        locks_by_round=locks,
    ) if champion else ([], "")
    league_hall_entry = None
    if champion:
        league_hall_entry = {
            "id": f"auto:liga:{version.id}:{max(final_round, version.max_rounds)}",
            "competition": "Liga",
            "title": f"{season_name} - Liga",
            "season": season_name,
            "champion": champion,
            "runner_up": runner,
            "team": [mon["species"] for mon in champion_team if mon.get("species")],
            "team_snapshot": champion_team,
            "team_source": champion_team_source,
            "notes": f"{league.get('points_final', {}).get(champion, 0):.1f} pts.",
            "created_at": archived_ts,
        }
    hall_entries = [entry for entry in ([league_hall_entry] if league_hall_entry else [])]
    hall_entries.extend(_cup_hall_entries(cup_state_snapshot, season_name=season_name, archived_at=archived_ts))
    identity_source = {
        "season_name": season_name,
        "version_id": version.id,
        "final_round": final_round,
        "closed_rounds": sorted(snapshots.keys()),
        "champion": champion,
        "runner_up": runner,
        "snapshot_digest": _stable_digest(snapshots),
        "cup_digest": _stable_digest(cup_state_snapshot),
    }
    archive_id = f"season:{_stable_digest(identity_source)}"
    return {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "id": archive_id,
        "label": season_name,
        "state": SEASON_STATE_ARCHIVED,
        "source_state": _clean_text(life.get("state"), SEASON_STATE_FINISHED),
        "started_at": _as_int(life.get("started_at"), 0),
        "finished_at": finished_at,
        "archived_at": archived_ts,
        "participants": participants,
        "trainer_statuses": trainer_statuses,
        "season_config": document,
        "season_version_used": version.id,
        "max_rounds": int(version.max_rounds),
        "league": league,
        "team_locks": {str(round_no): locks.get(round_no, []) for round_no in sorted(locks)},
        "champion_team": {
            "trainer": champion,
            "source": champion_team_source,
            "team": champion_team,
        },
        "cup": {
            "states": cup_state_snapshot,
            "hall_entries": [entry for entry in hall_entries if entry.get("competition") != "Liga"],
        },
        "hall_entries": hall_entries,
        "metadata": {
            "identity": identity_source,
            "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        },
    }


def _find_archive(archive_id: str) -> dict[str, Any] | None:
    for archive in load_season_archives():
        if _clean_text(archive.get("id")) == archive_id:
            return archive
    return None


def finish_active_season(*, admin_user: str | None, finished_at: int | None = None) -> dict[str, Any]:
    require_league_admin(admin_user)
    lifecycle = load_season_lifecycle()
    if lifecycle["state"] == SEASON_STATE_ARCHIVED:
        raise ValueError("La temporada ya esta archivada.")
    league_state = _league_state_from_settings()
    if bool(league_state.get("active")):
        raise ValueError("No se puede finalizar con una jornada abierta.")
    if latest_closed_round(league_state) <= 0:
        raise ValueError("No hay jornadas cerradas para finalizar.")
    finished_ts = int(finished_at if finished_at is not None else _now())
    return save_season_lifecycle(
        {
            "state": SEASON_STATE_FINISHED,
            "finished_at": lifecycle.get("finished_at") or finished_ts,
        }
    )


def archive_current_season(
    *,
    admin_user: str | None,
    label: str | None = None,
    archived_at: int | None = None,
) -> dict[str, Any]:
    require_league_admin(admin_user)
    lifecycle = load_season_lifecycle()
    if lifecycle["state"] == SEASON_STATE_ACTIVE:
        lifecycle = finish_active_season(admin_user=admin_user, finished_at=archived_at)
    if lifecycle["state"] == SEASON_STATE_DRAFT:
        raise ValueError("No se puede archivar una temporada en borrador.")
    if lifecycle["state"] == SEASON_STATE_DISCARDED:
        raise ValueError("No se puede archivar una temporada descartada.")
    existing_id = _clean_text(lifecycle.get("archive_id"))
    if existing_id:
        existing = _find_archive(existing_id)
        if existing:
            return existing
    archive = build_season_archive(
        label=label,
        archived_at=archived_at,
        lifecycle=lifecycle,
    )
    existing = _find_archive(str(archive["id"]))
    if existing:
        save_season_lifecycle(
            {
                "state": SEASON_STATE_ARCHIVED,
                "archive_id": existing["id"],
                "archived_at": _as_int(existing.get("archived_at"), 0),
            }
        )
        return existing
    archives = load_season_archives()
    archives.append(archive)
    _save_season_archives(archives)
    save_season_lifecycle(
        {
            "state": SEASON_STATE_ARCHIVED,
            "archive_id": archive["id"],
            "archived_at": archive["archived_at"],
            "finished_at": archive["finished_at"],
        }
    )
    try:
        from app.interfaz.hall_of_fame import sync_hall_of_fame_from_sources

        sync_hall_of_fame_from_sources()
    except Exception:
        pass
    return archive


def hall_entries_from_archives() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for archive in load_season_archives():
        archive_id = _clean_text(archive.get("id"))
        for raw_entry in archive.get("hall_entries") or []:
            if not isinstance(raw_entry, dict):
                continue
            entry = dict(raw_entry)
            entry["archive_id"] = archive_id
            entry.setdefault("created_at", _as_int(archive.get("archived_at"), _now()))
            entries.append(entry)
    return entries


def clear_active_season_state() -> dict[str, Any]:
    errors: list[str] = []
    try:
        from storage import clear_active_competition_rows

        report = clear_active_competition_rows()
        errors.extend(str(err) for err in (report.get("errors") or []))
    except Exception as exc:
        errors.append(f"active rows: {exc}")

    for key, value in ACTIVE_SEASON_SETTING_DEFAULTS.items():
        try:
            settings_set(key, value)
        except Exception as exc:
            errors.append(f"settings:{key}: {exc}")
    try:
        settings_set(
            "season_config_v2",
            json.dumps(default_season_document(players=list(USERS.keys())), ensure_ascii=False),
        )
    except Exception as exc:
        errors.append(f"settings:season_config_v2: {exc}")
    if st is not None:
        try:
            for key in list(st.session_state.keys()):
                if str(key).startswith("league_") or str(key) in {
                    "swiss",
                    "elim",
                    "copa_dobles",
                    "redeem_ctx",
                }:
                    st.session_state.pop(key, None)
        except Exception:
            pass
    return {"ok": not errors, "errors": errors}


def prepare_new_active_season(*, admin_user: str | None) -> dict[str, Any]:
    require_league_admin(admin_user)
    lifecycle = load_season_lifecycle()
    if lifecycle["state"] not in {SEASON_STATE_ARCHIVED, SEASON_STATE_DISCARDED}:
        raise ValueError("Prepara una nueva temporada solo despues de archivar o descartar.")
    report = clear_active_season_state()
    if not report.get("ok"):
        return report
    save_season_lifecycle(
        {
            "state": SEASON_STATE_ACTIVE,
            "started_at": _now(),
            "finished_at": 0,
            "archived_at": 0,
            "archive_id": "",
        }
    )
    return {"ok": True, "errors": []}


def mark_season_discarded(*, admin_user: str | None) -> dict[str, Any]:
    require_league_admin(admin_user)
    report = clear_active_season_state()
    if not report.get("ok"):
        return report
    save_season_lifecycle(
        {
            "state": SEASON_STATE_DISCARDED,
            "finished_at": 0,
            "archived_at": 0,
            "archive_id": "",
        }
    )
    return {"ok": True, "errors": []}
