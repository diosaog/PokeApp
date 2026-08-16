from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from app.application.activity import record_activity
from app.application.shop import purchase_discounted_item
from app.application.team_locks import lock_team_for_matchday
from app.domain.activity import ActivityEventType
from app.domain.common import Visibility
from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules, SeasonVersion
from app.domain.shop import PromotionKind, PromotionState, ShopPromotion
from app.domain.trainers import Trainer, TrainerStatus
from app.repositories import mappers
from app.repositories.legacy.activity import LegacyActivityRepository
from app.repositories.legacy.season import LegacySeasonRepository
from app.repositories.legacy.settings_store import LegacySettingsStore
from app.repositories.legacy.shop import LegacyShopRepository
from app.repositories.legacy.trainers import LegacyTrainerRepository
from app.repositories.memory import (
    InMemoryActivityRepository,
    InMemoryShopRepository,
    InMemoryTeamLockRepository,
    InMemoryTrainerRepository,
)


def _settings_store(initial: dict[str, object] | None = None):
    store = {
        key: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        for key, value in (initial or {}).items()
    }

    def get(key: str):
        return store.get(key)

    def set_value(key: str, value: str):
        store[key] = value

    return store, LegacySettingsStore(getter=get, setter=set_value)


class RepositoryTests(unittest.TestCase):
    def test_dependency_direction_guards_domain_and_interfaces(self) -> None:
        domain_root = Path("app/domain")
        for path in domain_root.rglob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("app.repositories", source, f"{path} imports repositories")

        clean_repo_files = [
            Path("app/repositories/protocols.py"),
            Path("app/repositories/mappers.py"),
            Path("app/repositories/memory/repositories.py"),
        ]
        for path in clean_repo_files:
            source = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("from storage", source, f"{path} imports legacy storage")
            self.assertNotIn("import streamlit", source, f"{path} imports Streamlit")
            self.assertNotIn("supabase", source, f"{path} mentions Supabase")

    def test_legacy_season_repository_maps_config_lifecycle_and_archive_settings(self) -> None:
        store, settings = _settings_store(
            {
                "season_config_v2": {
                    "schema_version": 1,
                    "active_version_id": "v1",
                    "versions": [
                        {
                            "id": "v1",
                            "name": "Temporada Test",
                            "effective_round": 1,
                            "max_rounds": 4,
                            "players": ["Anto", "Victor"],
                            "division_sizes": [1, 1],
                            "movement_count": 1,
                            "points_by_position": {"1": 9, "2": 8},
                            "coins_by_position": {"1": 15, "2": 14},
                            "rules": {
                                "team_lock_required": True,
                                "last_b_gets_steal": True,
                                "cup_is_separate": True,
                            },
                        }
                    ],
                },
                "season_lifecycle_v1": {
                    "state": "active",
                    "started_at": 1780000000,
                    "finished_at": 0,
                    "archived_at": 0,
                    "archive_id": "",
                },
            }
        )
        repo = LegacySeasonRepository(settings=settings)

        season = repo.get_active_season()
        versions = repo.list_versions()
        repo.save_versions(versions, active_version_id="v1")

        self.assertEqual(season.lifecycle.value, "active")
        self.assertEqual(season.active_version_id, "v1")
        self.assertEqual(versions[0].participant_ids, ("Anto", "Victor"))
        self.assertIn("season_config_v2", store)

    def test_legacy_activity_repository_maps_dedupes_and_filters_visibility(self) -> None:
        store, settings = _settings_store()
        repo = LegacyActivityRepository(settings=settings)
        first = record_activity(
            repo,
            ActivityEventType.TEAM_LOCKED,
            created_at=1000,
            actor_id="Anto",
            trainer_id="Anto",
            visibility=Visibility.PUBLIC,
            dedupe_key="TEAM_LOCKED:1:Anto",
        )
        second = record_activity(
            repo,
            ActivityEventType.TEAM_LOCKED,
            created_at=2000,
            actor_id="Anto",
            trainer_id="Anto",
            visibility=Visibility.PUBLIC,
            dedupe_key="TEAM_LOCKED:1:Anto",
        )

        saved = json.loads(store["activity_events_v1"])
        recent = repo.list_recent(limit=5, viewer="Victor")

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(saved), 1)
        self.assertEqual(recent[0].type, ActivityEventType.TEAM_LOCKED)

    def test_legacy_trainer_repository_updates_status_and_flags(self) -> None:
        _store, settings = _settings_store({"trainer_flags": {}})
        repo = LegacyTrainerRepository(settings=settings)

        status = repo.set_status("Victor", TrainerStatus.ABANDONED, by_user="Anto", now=1000)
        flags = repo.load_flag_map()

        self.assertEqual(status, TrainerStatus.ABANDONED)
        self.assertTrue(flags["Victor"]["abandoned"])
        self.assertEqual(repo.get_status("Victor"), TrainerStatus.ABANDONED)

    def test_legacy_shop_repository_maps_catalog_promotions_and_purchases(self) -> None:
        repo = LegacyShopRepository()
        with (
            patch(
                "storage.list_shop_discounts",
                return_value=[
                    {
                        "id": 7,
                        "item": "Restos",
                        "category": "competitivos",
                        "base_price": 8,
                        "discount_price": 6,
                        "stock_total": 2,
                        "stock_used": 0,
                        "discount_kind": "normal",
                        "jornada": 3,
                        "active": True,
                        "created_at": 1000,
                        "announced_at": 1000,
                        "activates_at": 1000,
                    }
                ],
            ),
            patch("storage.all_purchased_items", return_value={"Gemas Elementales"}),
            patch("storage.purchase_counts_by_item_for_jornadas", return_value={1: {"Restos": 1}}),
        ):
            promotions = repo.list_promotions(matchday_number=3, active_only=True)
            purchased = repo.all_purchased_item_names()
            counts = repo.purchase_counts_by_matchday((1,))

        self.assertEqual(promotions[0].item_id, "restos")
        self.assertEqual(promotions[0].discount_price, 6)
        self.assertIn("Gemas Elementales", purchased)
        self.assertEqual(counts[1]["Restos"], 1)

    def test_application_purchase_uses_repository_then_domain_then_repository(self) -> None:
        promo = ShopPromotion(
            id="1",
            item_id="restos",
            matchday_number=4,
            kind=PromotionKind.NORMAL,
            base_price=8,
            discount_price=6,
            stock_total=2,
            stock_used=0,
            announced_at="2026-01-01T00:00:00Z",
            activates_at="2026-01-01T00:00:00Z",
            state=PromotionState.ACTIVE,
            metadata={"item_name": "Restos", "category": "competitivos"},
        )
        repo = InMemoryShopRepository(promotions=(promo,))

        result = purchase_discounted_item(
            repo,
            trainer_id="Samu",
            promotion_id="1",
            matchday_number=4,
            now=mappers.iso_to_epoch("2026-01-01T00:00:00Z"),
        )

        self.assertTrue(result["purchased"])
        self.assertEqual(repo.list_purchases("Samu")[0].item_name, "Restos")

    def test_in_memory_repositories_support_status_and_team_lock_use_cases(self) -> None:
        trainer_repo = InMemoryTrainerRepository(
            trainers=(Trainer(id="Anto", display_name="Anto"),),
        )
        trainer_repo.set_status("Anto", TrainerStatus.RETIRED, by_user="Anto", now=1000)

        lock_repo = InMemoryTeamLockRepository()
        lock = lock_team_for_matchday(
            lock_repo,
            lock_id="lock-1",
            season_id="season-1",
            trainer_id="Anto",
            locked_at="2026-01-01T00:00:00Z",
            matchday_number=1,
            team=(PublicPokemon(species="Milotic"),),
            participant_ids=("Anto",),
            rules=SeasonRules(team_lock_required=True),
        )

        self.assertEqual(trainer_repo.get_status("Anto"), TrainerStatus.RETIRED)
        self.assertEqual(lock_repo.get_team_lock(matchday_number=1, trainer_id="Anto"), lock)

    def test_mappers_keep_contracts_at_repository_boundary(self) -> None:
        version = SeasonVersion(
            id="v2",
            season_id="season-1",
            name="Temporada Dos",
            effective_matchday=2,
            max_matchdays=4,
            participant_ids=("Anto", "Victor"),
            division_sizes=(1, 1),
            promotion_relegation_count=1,
            points_by_position={1: 9, 2: 8},
            coins_by_position={1: 15, 2: 14},
        )
        legacy = mappers.season_version_to_legacy_dict(version)
        roundtrip = mappers.season_version_from_any(legacy, season_id="season-1")
        save = mappers.save_record_from_legacy((9, "a.sav", "ROM.sav", "abc", "Anto", 1780000000), current_save_id="9")

        self.assertEqual(legacy["effective_round"], 2)
        self.assertEqual(roundtrip.effective_matchday, 2)
        self.assertTrue(save.is_current)
        self.assertEqual(save.trainer_id, "Anto")


if __name__ == "__main__":
    unittest.main()
