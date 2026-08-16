from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.domain.activity import ActivityEvent, ActivityEventType
from app.domain.archives import SeasonArchive
from app.domain.common import CompetitionType, Visibility, epoch_to_utc_iso, to_jsonable
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.legacy import (
    activity_event_from_legacy,
    matchday_snapshot_from_legacy,
    pokemon_from_legacy,
    season_version_from_legacy,
    team_lock_from_legacy,
    trainer_status_from_legacy,
)
from app.domain.league import MatchdaySnapshot
from app.domain.pokemon import PublicPokemon
from app.domain.saves import SaveRecord
from app.domain.seasons import Season, SeasonLifecycle, SeasonMetadata, SeasonRules, SeasonVersion
from app.domain.shop import (
    PromotionKind,
    PromotionState,
    Purchase,
    PurchaseStatus,
    Redemption,
    ShopItem,
    ShopPromotion,
)
from app.domain.team_locks import TeamLock
from app.domain.trainers import Trainer, TrainerFlags, TrainerStatus
from app.domain.trials import (
    JuryVote,
    Penalty,
    PenaltyType,
    TrialCase,
    TrialStatus,
    TrialVerdict,
    TrialVote,
)
from app.domain.services.shop import item_key


LEGACY_SEASON_ID = "legacy-season"


def text(value: Any, fallback: str = "") -> str:
    out = str(value or "").strip()
    return out or fallback


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def utc_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return epoch_to_utc_iso(value)
    raw = text(value)
    if raw.isdigit():
        return epoch_to_utc_iso(int(raw))
    return raw


def iso_to_epoch(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    raw = text(value)
    if not raw:
        return 0
    if raw.isdigit():
        return max(0, int(raw))
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int(dt.timestamp()))
    except Exception:
        return 0


def season_from_lifecycle(
    raw: dict[str, Any] | None,
    *,
    season_id: str = LEGACY_SEASON_ID,
    name: str = "Temporada actual",
    active_version_id: str = "",
) -> Season:
    data = raw if isinstance(raw, dict) else {}
    state = text(data.get("state"), "active")
    try:
        lifecycle = SeasonLifecycle(state)
    except Exception:
        lifecycle = SeasonLifecycle.ACTIVE
    return Season(
        id=season_id,
        name=name,
        lifecycle=lifecycle,
        active_version_id=active_version_id,
        started_at=utc_iso(data.get("started_at")),
        finished_at=utc_iso(data.get("finished_at")),
        archived_at=utc_iso(data.get("archived_at")),
        discarded_at=utc_iso(data.get("discarded_at")),
    )


def lifecycle_from_season(season: Season, *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(previous or {})
    out.update(
        {
            "schema_version": 1,
            "state": season.lifecycle.value,
            "started_at": iso_to_epoch(season.started_at),
            "finished_at": iso_to_epoch(season.finished_at),
            "archived_at": iso_to_epoch(season.archived_at),
            "discarded_at": iso_to_epoch(season.discarded_at),
            "archive_id": text(out.get("archive_id")),
        }
    )
    return out


def season_version_to_legacy_dict(version: SeasonVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "name": version.name,
        "effective_round": int(version.effective_matchday),
        "max_rounds": int(version.max_matchdays),
        "players": list(version.participant_ids),
        "division_count": len(version.division_sizes),
        "division_sizes": list(version.division_sizes),
        "movement_count": int(version.promotion_relegation_count),
        "points_by_position": {str(k): int(v) for k, v in version.points_by_position.items()},
        "coins_by_position": {str(k): int(v) for k, v in version.coins_by_position.items()},
        "rules": {
            "team_lock_required": bool(version.rules.team_lock_required),
            "last_b_gets_steal": bool(version.rules.last_b_gets_steal),
            "cup_is_separate": bool(version.metadata.cup_is_separate),
        },
    }


def season_version_from_any(raw: Any, *, season_id: str = LEGACY_SEASON_ID) -> SeasonVersion:
    if isinstance(raw, SeasonVersion):
        return raw
    if isinstance(raw, dict):
        return season_version_from_legacy(raw, season_id=season_id)
    attrs = {
        "id": text(getattr(raw, "id", "")),
        "name": text(getattr(raw, "name", ""), "Temporada legacy"),
        "effective_round": as_int(getattr(raw, "effective_round", 1), 1),
        "max_rounds": as_int(getattr(raw, "max_rounds", 1), 1),
        "players": list(getattr(raw, "players", []) or []),
        "division_sizes": list(getattr(raw, "division_sizes", []) or []),
        "movement_count": as_int(getattr(raw, "movement_count", 0), 0),
        "points_by_position": dict(getattr(raw, "points_by_position", {}) or {}),
        "coins_by_position": dict(getattr(raw, "coins_by_position", {}) or {}),
        "rules": dict(getattr(raw, "rules", {}) or {}),
    }
    return season_version_from_legacy(attrs, season_id=season_id)


def trainer_from_legacy(name: str, raw: dict[str, Any] | None = None) -> Trainer:
    data = raw if isinstance(raw, dict) else {}
    return Trainer(
        id=text(data.get("id") or name),
        display_name=text(data.get("display_name") or data.get("name") or name),
        avatar_url=text(data.get("avatar_url") or data.get("avatar")),
        metadata={k: v for k, v in data.items() if isinstance(k, str) and k not in {"id", "display_name", "name", "avatar_url", "avatar"}},
    )


def trainer_flags_from_legacy(trainer_id: str, raw: dict[str, Any] | None) -> TrainerFlags:
    data = raw if isinstance(raw, dict) else {}
    return TrainerFlags(
        trainer_id=trainer_id,
        robbed=bool(data.get("robbed")),
        robbed_at=utc_iso(data.get("robbed_at")),
        robbed_by=text(data.get("robbed_by")),
        robbed_source=text(data.get("robbed_source") or data.get("source")),
        note=text(data.get("note")),
    )


def trainer_flags_to_legacy(flags: TrainerFlags, *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(previous or {})
    if flags.robbed:
        out["robbed"] = True
        if flags.robbed_at:
            out["robbed_at"] = iso_to_epoch(flags.robbed_at) or flags.robbed_at
        if flags.robbed_by:
            out["robbed_by"] = flags.robbed_by
        if flags.robbed_source:
            out["robbed_source"] = flags.robbed_source
    else:
        out.pop("robbed", None)
        out.pop("robbed_at", None)
        out.pop("robbed_by", None)
        out.pop("robbed_source", None)
    if flags.note:
        out["note"] = flags.note
    return out


def shop_item_from_catalog(category: str, raw: dict[str, Any]) -> ShopItem:
    name = text(raw.get("name"))
    return ShopItem(
        id=item_key(name),
        category=text(category),
        name=name,
        description=text(raw.get("desc") or raw.get("description")),
        base_price=max(0, as_int(raw.get("price"), 0)),
        image_url=text(raw.get("img") or raw.get("image_url")),
        metadata={"icon": text(raw.get("icon"))} if text(raw.get("icon")) else {},
    )


def promotion_from_legacy(
    raw: dict[str, Any],
    *,
    season_id: str = LEGACY_SEASON_ID,
    now: int | None = None,
) -> ShopPromotion:
    name = text(raw.get("item") or raw.get("name"))
    active = bool(raw.get("active"))
    used = max(0, as_int(raw.get("stock_used"), 0))
    total = max(0, as_int(raw.get("stock_total"), 0))
    activates_ts = as_int(raw.get("activates_at"), 0)
    if not active or (total and used >= total):
        state = PromotionState.ENDED
    elif now is not None and activates_ts and int(now) < activates_ts:
        state = PromotionState.PENDING
    else:
        state = PromotionState.ACTIVE
    kind_raw = text(raw.get("discount_kind"), "normal")
    try:
        kind = PromotionKind(kind_raw)
    except Exception:
        kind = PromotionKind.NORMAL
    promo_id = text(raw.get("id") or raw.get("discount_id")) or f"promo:{as_int(raw.get('jornada'), 0)}:{item_key(name)}:{kind.value}"
    return ShopPromotion(
        id=promo_id,
        item_id=item_key(name),
        season_id=season_id,
        matchday_number=as_int(raw.get("jornada") or raw.get("matchday_number"), 0) or None,
        kind=kind,
        base_price=max(0, as_int(raw.get("base_price"), 0)),
        discount_price=max(0, as_int(raw.get("discount_price"), 0)),
        stock_total=total,
        stock_used=used,
        announced_at=utc_iso(raw.get("announced_at") or raw.get("created_at")),
        activates_at=utc_iso(raw.get("activates_at") or raw.get("created_at")),
        ends_at=utc_iso(raw.get("exhausted_at")),
        state=state,
        dedupe_key=text(raw.get("dedupe_key")),
        metadata={"item_name": name, "category": text(raw.get("category"))},
    )


def promotion_to_legacy_payload(promotion: ShopPromotion) -> dict[str, Any]:
    return {
        "id": as_int(promotion.id, 0),
        "item": text(promotion.metadata.get("item_name")) or promotion.item_id,
        "category": text(promotion.metadata.get("category")),
        "base_price": int(promotion.base_price),
        "discount_price": int(promotion.discount_price),
        "stock_total": int(promotion.stock_total),
        "stock_used": int(promotion.stock_used),
        "discount_kind": promotion.kind.value,
        "jornada": int(promotion.matchday_number or 0),
        "active": promotion.state != PromotionState.ENDED,
        "announced_at": iso_to_epoch(promotion.announced_at),
        "activates_at": iso_to_epoch(promotion.activates_at),
        "exhausted_at": iso_to_epoch(promotion.ends_at),
    }


def purchase_from_legacy(raw: Any, *, season_id: str = LEGACY_SEASON_ID) -> Purchase:
    if isinstance(raw, dict):
        pid = raw.get("id")
        trainer = raw.get("user") or raw.get("trainer_id")
        item = raw.get("item") or raw.get("item_name")
        price = raw.get("price") or raw.get("unit_price")
        created = raw.get("created_at") or raw.get("purchased_at")
        status = raw.get("status")
        discount_id = raw.get("discount_id")
        base_price = raw.get("base_price")
        jornada = raw.get("jornada") or raw.get("matchday_number")
    else:
        values = list(raw or ())
        pid = values[0] if len(values) > 0 else ""
        trainer = values[1] if len(values) > 1 else ""
        item = values[2] if len(values) > 2 else ""
        price = values[3] if len(values) > 3 else 0
        created = values[4] if len(values) > 4 else 0
        status = values[5] if len(values) > 5 else "pending"
        discount_id = ""
        base_price = None
        jornada = None
    status_raw = text(status, "pending")
    try:
        purchase_status = PurchaseStatus(status_raw)
    except Exception:
        purchase_status = PurchaseStatus.PENDING
    unit_price = max(0, as_int(price, 0))
    return Purchase(
        id=text(pid),
        trainer_id=text(trainer),
        item_id=item_key(item),
        item_name=text(item),
        quantity=1,
        unit_price=unit_price,
        total_price=unit_price,
        purchased_at=utc_iso(created),
        status=purchase_status,
        season_id=season_id,
        matchday_number=as_int(jornada, 0) or None,
        promotion_id=text(discount_id),
        base_unit_price=as_int(base_price, 0) if base_price is not None else None,
    )


def redemption_from_legacy(raw: Any) -> Redemption:
    if isinstance(raw, dict):
        rid = raw.get("id")
        purchase_id = raw.get("purchase_id")
        trainer = raw.get("user") or raw.get("trainer_id")
        item = raw.get("item") or raw.get("item_name")
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else json_loads(raw.get("payload_json"), {})
        created = raw.get("created_at") or raw.get("redeemed_at")
    else:
        values = list(raw or ())
        rid = values[0] if len(values) > 0 else ""
        purchase_id = values[1] if len(values) > 1 else ""
        trainer = values[2] if len(values) > 2 else ""
        item = values[3] if len(values) > 3 else ""
        payload = json_loads(values[4] if len(values) > 4 else None, {})
        created = values[5] if len(values) > 5 else 0
    return Redemption(
        id=text(rid),
        purchase_id=text(purchase_id),
        trainer_id=text(trainer),
        item_id=item_key(item),
        item_name=text(item),
        redeemed_at=utc_iso(created),
        payload=payload if isinstance(payload, dict) else {},
    )


def save_record_from_legacy(raw: Any, *, current_save_id: str = "") -> SaveRecord:
    if isinstance(raw, dict):
        sid = raw.get("id")
        filename = raw.get("filename")
        original = raw.get("original_name")
        sha = raw.get("sha256")
        trainer = raw.get("user") or raw.get("uploader")
        created = raw.get("created_at") or raw.get("uploaded_at")
        file_ref = raw.get("url") or raw.get("file_ref")
    else:
        values = list(raw or ())
        sid = values[0] if len(values) > 0 else ""
        filename = values[1] if len(values) > 1 else ""
        original = values[2] if len(values) > 2 else ""
        sha = values[3] if len(values) > 3 else ""
        trainer = values[4] if len(values) > 4 else ""
        created = values[5] if len(values) > 5 else 0
        file_ref = ""
    sid_text = text(sid)
    return SaveRecord(
        id=sid_text,
        trainer_id=text(trainer, "unknown"),
        filename=text(filename),
        original_name=text(original) or text(filename),
        sha256=text(sha, "unknown"),
        uploaded_at=utc_iso(created),
        file_ref=text(file_ref),
        is_current=bool(current_save_id and sid_text == str(current_save_id)),
    )


def activity_event_to_legacy(event: ActivityEvent) -> dict[str, Any]:
    return {
        "schema_version": int(event.schema_version),
        "id": event.id,
        "type": event.type.name,
        "created_at": iso_to_epoch(event.created_at),
        "actor": event.actor_id,
        "trainer": event.trainer_id,
        "context": dict(event.context),
        "payload": dict(event.payload),
        "visibility": {
            Visibility.PUBLIC: "public",
            Visibility.OWNER: "trainer-only",
            Visibility.ADMIN: "admin-only",
            Visibility.SERVER_ONLY: "admin-only",
        }.get(event.visibility, "public"),
        "dedupe_key": event.dedupe_key,
    }


def activity_event_from_any(raw: Any) -> ActivityEvent | None:
    if isinstance(raw, ActivityEvent):
        return raw
    if not isinstance(raw, dict):
        return None
    try:
        return activity_event_from_legacy(raw)
    except Exception:
        return None


def public_pokemon_from_legacy(raw: Any) -> PublicPokemon | None:
    if isinstance(raw, PublicPokemon):
        return raw.to_public() if hasattr(raw, "to_public") else raw
    if not isinstance(raw, dict):
        species = text(raw)
        return PublicPokemon(species=species) if species else None
    try:
        return pokemon_from_legacy(raw, private=False)
    except Exception:
        species = text(raw.get("species") or raw.get("name"))
        return PublicPokemon(species=species) if species else None


def hall_entry_from_legacy(raw: Any) -> HallOfFameEntry | None:
    if isinstance(raw, HallOfFameEntry):
        return raw
    if not isinstance(raw, dict):
        return None
    champion = text(raw.get("champion") or raw.get("champion_id"))
    if not champion:
        return None
    competition_raw = text(raw.get("competition"), "league").lower()
    competition_map = {
        "liga": CompetitionType.LEAGUE,
        "league": CompetitionType.LEAGUE,
        "copa": CompetitionType.CUP,
        "cup": CompetitionType.CUP,
        "torneo": CompetitionType.TOURNAMENT,
        "tournament": CompetitionType.TOURNAMENT,
        "copa dobles": CompetitionType.DOUBLES_CUP,
        "doubles_cup": CompetitionType.DOUBLES_CUP,
    }
    team_raw = raw.get("team_snapshot") if isinstance(raw.get("team_snapshot"), list) else []
    team = tuple(mon for mon in (public_pokemon_from_legacy(item) for item in team_raw) if mon)
    if not team:
        team = tuple(
            PublicPokemon(species=name)
            for name in (raw.get("team") if isinstance(raw.get("team"), list) else [])
            if text(name)
        )
    return HallOfFameEntry(
        id=text(raw.get("id")) or f"hof:{champion}:{iso_to_epoch(raw.get('created_at'))}",
        competition=competition_map.get(competition_raw, CompetitionType.LEAGUE),
        title=text(raw.get("title"), "Temporada archivada"),
        champion_id=champion,
        runner_up_id=text(raw.get("runner_up") or raw.get("runner_up_id")),
        created_at=utc_iso(raw.get("created_at")),
        season_id=text(raw.get("season_id")),
        archive_id=text(raw.get("archive_id")),
        frozen_team=team,
        source=text(raw.get("team_source") or raw.get("source")),
        notes=text(raw.get("notes")),
    )


def hall_entry_to_legacy(entry: HallOfFameEntry) -> dict[str, Any]:
    team_payload = [to_jsonable(mon) for mon in entry.frozen_team]
    competition_label = {
        CompetitionType.LEAGUE: "Liga",
        CompetitionType.CUP: "Copa",
        CompetitionType.TOURNAMENT: "Torneo",
        CompetitionType.DOUBLES_CUP: "Copa Dobles",
    }.get(entry.competition, entry.competition.value)
    return {
        "id": entry.id,
        "competition": competition_label,
        "title": entry.title,
        "season": entry.season_id or "",
        "champion": entry.champion_id,
        "runner_up": entry.runner_up_id,
        "team": [text(mon.get("species")) for mon in team_payload if isinstance(mon, dict) and text(mon.get("species"))],
        "team_snapshot": team_payload,
        "team_source": entry.source,
        "archive_id": entry.archive_id,
        "notes": entry.notes,
        "created_at": iso_to_epoch(entry.created_at),
    }


def season_archive_from_legacy(raw: Any) -> SeasonArchive | None:
    if isinstance(raw, SeasonArchive):
        return raw
    if not isinstance(raw, dict):
        return None
    archive_id = text(raw.get("id"))
    if not archive_id:
        return None
    season_config = raw.get("season_config") if isinstance(raw.get("season_config"), dict) else {}
    versions = tuple(
        season_version_from_any(item)
        for item in (season_config.get("versions") if isinstance(season_config.get("versions"), list) else [])
    )
    snapshots_raw = (
        raw.get("league", {}).get("round_snapshots")
        if isinstance(raw.get("league"), dict)
        else {}
    )
    snapshots = []
    if isinstance(snapshots_raw, dict):
        for item in snapshots_raw.values():
            if isinstance(item, dict):
                try:
                    snapshots.append(matchday_snapshot_from_legacy(item))
                except Exception:
                    continue
    statuses_raw = raw.get("trainer_statuses") if isinstance(raw.get("trainer_statuses"), dict) else {}
    statuses: dict[str, TrainerStatus] = {}
    for trainer, data in statuses_raw.items():
        status_value = data.get("status") if isinstance(data, dict) else data
        statuses[text(trainer)] = trainer_status_from_legacy(status_value)
    champion_team_raw = (
        raw.get("champion_team", {}).get("team")
        if isinstance(raw.get("champion_team"), dict)
        else []
    )
    champion_team = tuple(
        mon for mon in (public_pokemon_from_legacy(item) for item in (champion_team_raw or [])) if mon
    )
    hall_entries = tuple(
        entry
        for entry in (hall_entry_from_legacy(item) for item in (raw.get("hall_entries") or []))
        if entry
    )
    league_raw = raw.get("league") if isinstance(raw.get("league"), dict) else {}
    return SeasonArchive(
        id=archive_id,
        schema_version=max(1, as_int(raw.get("schema_version"), 1)),
        season_id=text(raw.get("season_id"), LEGACY_SEASON_ID),
        label=text(raw.get("label"), "Temporada archivada"),
        archived_at=utc_iso(raw.get("archived_at")),
        season_versions=versions,
        matchday_snapshots=tuple(snapshots),
        trainer_statuses=statuses,
        champion_id=text(league_raw.get("champion")),
        runner_up_id=text(league_raw.get("runner_up")),
        champion_team=champion_team,
        hall_entries=hall_entries,
        metadata={"legacy": raw},
    )


def trial_case_from_legacy(raw: Any, *, season_id: str = LEGACY_SEASON_ID) -> TrialCase | None:
    if isinstance(raw, TrialCase):
        return raw
    if not isinstance(raw, dict):
        return None
    title = text(raw.get("title"))
    creator = text(raw.get("creator") or raw.get("creator_id"))
    accused = text(raw.get("accused") or raw.get("accused_id"))
    if not title or not creator or not accused:
        return None
    status_map = {
        "propuesta": TrialStatus.PROPOSED,
        "proposed": TrialStatus.PROPOSED,
        "en_proceso": TrialStatus.IN_PROGRESS,
        "in_progress": TrialStatus.IN_PROGRESS,
        "finalizado": TrialStatus.FINISHED,
        "finished": TrialStatus.FINISHED,
    }
    verdict_map = {
        "culpable": TrialVerdict.GUILTY,
        "guilty": TrialVerdict.GUILTY,
        "inocente": TrialVerdict.NOT_GUILTY,
        "not_guilty": TrialVerdict.NOT_GUILTY,
        "pending": TrialVerdict.PENDING,
        "pendiente": TrialVerdict.PENDING,
    }
    vote_map = {
        "guilty": TrialVote.GUILTY,
        "culpable": TrialVote.GUILTY,
        "not_guilty": TrialVote.NOT_GUILTY,
        "inocente": TrialVote.NOT_GUILTY,
    }
    penalty_map = {
        "store_ban": PenaltyType.STORE_BAN,
        "coins_reduction": PenaltyType.COINS_REDUCTION,
        "pokemon_release": PenaltyType.POKEMON_RELEASE,
        "points_reduction": PenaltyType.POINTS_REDUCTION,
    }
    votes = []
    for item in raw.get("jury_votes") or []:
        if not isinstance(item, dict):
            continue
        jury = text(item.get("jury") or item.get("jury_trainer_id"))
        vote = vote_map.get(text(item.get("vote")).lower())
        if jury and vote:
            votes.append(JuryVote(jury_trainer_id=jury, vote=vote, voted_at=utc_iso(item.get("ts") or item.get("voted_at"))))
    penalties = []
    for item in raw.get("penalties") or []:
        if not isinstance(item, dict):
            continue
        ptype = penalty_map.get(text(item.get("type")).lower(), PenaltyType.OTHER)
        penalties.append(
            Penalty(
                type=ptype,
                amount=as_float(item.get("amount"), 0.0),
                text=text(item.get("text") or item.get("description")),
                start_matchday=as_int(item.get("start_tramo"), 0) or None,
                end_matchday=as_int(item.get("end_tramo"), 0) or None,
                metadata={k: v for k, v in item.items() if isinstance(k, str)},
            )
        )
    return TrialCase(
        id=text(raw.get("id")),
        season_id=season_id,
        case_no=max(1, as_int(raw.get("case_no"), 1)),
        title=title,
        creator_id=creator,
        accused_id=accused,
        status=status_map.get(text(raw.get("status")).lower(), TrialStatus.PROPOSED),
        verdict=verdict_map.get(text(raw.get("verdict")).lower(), TrialVerdict.PENDING),
        summary=text(raw.get("summary")),
        hearing_date=text(raw.get("hearing_date")),
        is_public=bool(raw.get("is_public", True)),
        evidence=text(raw.get("evidence")),
        witnesses=text(raw.get("witnesses")),
        priority=text(raw.get("priority"), "medium"),
        category=text(raw.get("category")),
        public_vote=bool(raw.get("public_vote")),
        jury_size=max(1, as_int(raw.get("jury_size"), 5)),
        jury_votes=tuple(votes),
        resolution_notes=text(raw.get("resolution_notes")),
        penalties=tuple(penalties),
        created_at=utc_iso(raw.get("created_at")),
        updated_at=utc_iso(raw.get("updated_at")),
        resolved_at=utc_iso(raw.get("resolved_at")),
        metadata={"legacy": raw},
    )


def team_lock_from_any(raw: Any, *, season_id: str = LEGACY_SEASON_ID) -> TeamLock | None:
    if isinstance(raw, TeamLock):
        return raw
    if not isinstance(raw, dict):
        return None
    try:
        return team_lock_from_legacy(raw, season_id=season_id)
    except Exception:
        return None
