"""V2 competitive-jornada and legacy-compatible store-ban contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CompetitiveMatchday:
    id: str
    season_id: str
    number: int
    status: str

    def __post_init__(self):
        if not self.id or not self.season_id or type(self.number) is not int or self.number <= 0:
            raise ValueError("invalid_current_matchday")
        if self.status not in ("scheduled", "open", "closed"):
            raise ValueError("current_matchday_invalid")


def resolve_current_matchday(season: Mapping, matchday: Mapping | None) -> CompetitiveMatchday:
    if not season.get("current_matchday_id"):
        raise ValueError("current_matchday_required")
    if not matchday or matchday.get("id") != season["current_matchday_id"] or matchday.get("season_id") != season["id"]:
        raise ValueError("current_matchday_invalid")
    return CompetitiveMatchday(**{key: matchday[key] for key in ("id", "season_id", "number", "status")})


def legacy_store_ban_window(penalty: Mapping) -> tuple[int | None, int | None]:
    try:
        start, end = int(penalty.get("start_tramo") or 0), int(penalty.get("end_tramo") or 0)
    except (ValueError, TypeError, OverflowError):
        return None, None
    if start > 0 and end > 0 and start > end:
        raise ValueError("invalid_store_ban_window")
    return start if start > 0 else None, end if end > 0 else None


def store_ban_applies(penalty: Mapping, case: Mapping | None, *, season_id: str,
                      trainer_id: str, current_matchday_number: int) -> bool:
    if type(current_matchday_number) is not int or current_matchday_number <= 0:
        raise ValueError("invalid_current_matchday")
    if (penalty.get("season_id") != season_id or penalty.get("trainer_id") != trainer_id
            or penalty.get("penalty_type") != "store_ban" or not case
            or penalty.get("trial_case_id") != case.get("id") or case.get("status") != "resolved"
            or case.get("accused_trainer_id") != trainer_id or case.get("season_id") not in (None, season_id)):
        return False
    start, end = penalty.get("start_matchday_number"), penalty.get("end_matchday_number")
    return start is None or end is None or start <= current_matchday_number <= end
