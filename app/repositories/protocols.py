from __future__ import annotations

from typing import Any, Protocol

from app.domain.activity import ActivityEvent
from app.domain.archives import SeasonArchive
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.league import MatchdaySnapshot
from app.domain.saves import SaveRecord
from app.domain.seasons import Season, SeasonVersion
from app.domain.shop import Purchase, Redemption, ShopItem, ShopPromotion
from app.domain.team_locks import TeamLock
from app.domain.trainers import Trainer, TrainerFlags, TrainerStatus
from app.domain.trials import TrialCase


class SeasonRepository(Protocol):
    def get_active_season(self) -> Season:
        ...

    def save_active_season(self, season: Season) -> Season:
        ...

    def list_versions(self) -> tuple[SeasonVersion, ...]:
        ...

    def save_versions(self, versions: tuple[SeasonVersion, ...], *, active_version_id: str) -> None:
        ...

    def list_archives(self) -> tuple[SeasonArchive, ...]:
        ...

    def save_archives(self, archives: tuple[SeasonArchive, ...]) -> None:
        ...


class LeagueRepository(Protocol):
    def load_state(self) -> dict[str, Any]:
        ...

    def save_state(self, state: dict[str, Any]) -> None:
        ...

    def list_matchday_snapshots(self) -> tuple[MatchdaySnapshot, ...]:
        ...

    def save_matchday_snapshots(self, snapshots: tuple[MatchdaySnapshot, ...]) -> None:
        ...


class TrainerRepository(Protocol):
    def list_trainers(self) -> tuple[Trainer, ...]:
        ...

    def load_flag_map(self) -> dict[str, dict[str, Any]]:
        ...

    def save_flag_map(self, flags: dict[str, dict[str, Any]]) -> None:
        ...

    def get_status(self, trainer_id: str) -> TrainerStatus:
        ...

    def set_status(self, trainer_id: str, status: TrainerStatus, *, by_user: str, now: int) -> TrainerStatus:
        ...

    def get_flags(self, trainer_id: str) -> TrainerFlags:
        ...

    def set_flags(self, flags: TrainerFlags) -> TrainerFlags:
        ...


class ShopRepository(Protocol):
    def list_catalog(self) -> tuple[ShopItem, ...]:
        ...

    def list_promotions(
        self,
        *,
        matchday_number: int | None = None,
        active_only: bool | None = None,
    ) -> tuple[ShopPromotion, ...]:
        ...

    def get_promotion(self, promotion_id: str) -> ShopPromotion | None:
        ...

    def create_promotion(self, promotion: ShopPromotion) -> ShopPromotion | None:
        ...

    def purchase_counts_by_matchday(self, matchdays: tuple[int, ...]) -> dict[int, dict[str, int]]:
        ...

    def all_purchased_item_names(self) -> set[str]:
        ...

    def claimed_promotion_ids(self, trainer_id: str, promotion_ids: tuple[str, ...]) -> set[str]:
        ...

    def purchase_discount(self, *, trainer_id: str, promotion_id: str, matchday_number: int) -> dict[str, Any]:
        ...

    def add_purchase(
        self,
        *,
        trainer_id: str,
        item_name: str,
        price: int,
        matchday_number: int | None = None,
        promotion_id: str = "",
        base_price: int | None = None,
        notify: bool = True,
    ) -> Purchase:
        ...

    def list_purchases(self, trainer_id: str | None = None, *, limit: int = 100) -> tuple[Purchase, ...]:
        ...

    def list_redemptions(self, trainer_id: str | None = None, *, limit: int = 500) -> tuple[Redemption, ...]:
        ...


class SaveRepository(Protocol):
    def list_saves(self, *, limit: int = 50) -> tuple[SaveRecord, ...]:
        ...

    def list_saves_by_trainer(self, trainer_id: str, *, limit: int = 50) -> tuple[SaveRecord, ...]:
        ...

    def get_current_save(self, trainer_id: str) -> SaveRecord | None:
        ...

    def set_current_save(self, trainer_id: str, save_id: str) -> None:
        ...

    def load_save_bytes(self, save: SaveRecord) -> bytes:
        ...


class TeamLockRepository(Protocol):
    def get_team_lock(self, *, matchday_number: int, trainer_id: str) -> TeamLock | None:
        ...

    def list_team_locks(self, *, matchday_number: int) -> tuple[TeamLock, ...]:
        ...

    def upsert_team_lock(self, lock: TeamLock) -> TeamLock | None:
        ...


class ActivityRepository(Protocol):
    def append(self, event: ActivityEvent) -> ActivityEvent:
        ...

    def list_recent(
        self,
        *,
        limit: int = 5,
        viewer: str | None = None,
        event_types: tuple[str, ...] | None = None,
    ) -> tuple[ActivityEvent, ...]:
        ...

    def find_by_dedupe_key(self, dedupe_key: str) -> ActivityEvent | None:
        ...


class HallOfFameRepository(Protocol):
    def list_entries(self) -> tuple[HallOfFameEntry, ...]:
        ...

    def save_entries(self, entries: tuple[HallOfFameEntry, ...]) -> None:
        ...

    def find_entry(self, entry_id: str) -> HallOfFameEntry | None:
        ...


class CompetitionRepository(Protocol):
    def load_cup_state(self, key: str) -> dict[str, Any]:
        ...

    def save_cup_state(self, key: str, state: dict[str, Any]) -> None:
        ...

    def list_trials(self) -> tuple[TrialCase, ...]:
        ...

    def save_trials(self, cases: tuple[TrialCase, ...]) -> None:
        ...
