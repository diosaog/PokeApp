from __future__ import annotations

import random
from pathlib import Path
import unittest

from app.domain.common import CompetitionType, Visibility, to_jsonable
from app.domain.league import PenaltySummary
from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules, SeasonVersion
from app.domain.services import (
    activity,
    archives,
    hall_of_fame,
    league,
    rewards,
    season,
    shop,
    snapshots,
    team_locks,
    trainers,
    trials,
)
from app.domain.trainers import TrainerStatus
from app.tienda.catalog_data import get_catalog


def _version() -> SeasonVersion:
    return SeasonVersion(
        id="v1",
        season_id="season-1",
        name="Temporada Test",
        effective_matchday=1,
        max_matchdays=4,
        participant_ids=("Anto", "Victor", "Samu", "Rober"),
        division_sizes=(2, 2),
        promotion_relegation_count=1,
        points_by_position={1: 9, 2: 8, 3: 7, 4: 6},
        coins_by_position={1: 15, 2: 14, 3: 12, 4: 11},
        rules=SeasonRules(team_lock_required=True, last_b_gets_steal=True),
    )


class DomainServiceTests(unittest.TestCase):
    def test_domain_services_do_not_import_infrastructure(self) -> None:
        forbidden = (
            "streamlit",
            "supabase",
            "session_state",
            "settings_get",
            "settings_set",
            "discord",
            "pkhex",
        )
        for path in Path("app/domain").rglob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                self.assertNotIn(token, source, f"{path} imports or mentions {token}")

    def test_season_resolution_validation_and_application_window(self) -> None:
        base = _version()
        later = SeasonVersion(
            id="v2",
            season_id="season-1",
            name="Temporada Test v2",
            effective_matchday=3,
            max_matchdays=4,
            participant_ids=base.participant_ids,
            division_sizes=base.division_sizes,
            promotion_relegation_count=base.promotion_relegation_count,
            points_by_position={1: 12, 2: 8, 3: 7, 4: 6},
            coins_by_position=base.coins_by_position,
            rules=base.rules,
        )

        self.assertEqual(season.select_effective_version([base, later], matchday_number=2).id, "v1")
        self.assertEqual(season.select_effective_version([base, later], matchday_number=3).id, "v2")
        self.assertFalse(season.has_blocking_issues(season.validate_season_version(base)))
        decision = season.can_apply_version(
            effective_matchday=2,
            closed_matchdays=[1, 2],
            current_matchday=3,
            matchday_is_open=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "closed_matchday")
        self.assertEqual(decision.minimum_matchday, 3)

    def test_league_ranking_movements_rewards_and_penalties_are_pure(self) -> None:
        results = {
            ("Anto", "Victor"): "Anto",
            ("Anto", "Samu"): "Samu",
            ("Victor", "Samu"): "Victor",
        }

        ranked = league.rank_division(
            ["Anto", "Victor", "Samu"],
            results,
            dead_counts={"Anto": 3, "Victor": 1, "Samu": 2},
        )

        self.assertEqual(ranked, ["Victor", "Samu", "Anto"])
        movement = league.calculate_division_movements(["A1", "A2"], ["B1", "B2"], 1)
        self.assertEqual(movement.new_a, ("A1", "B1"))
        self.assertEqual(movement.new_b, ("A2", "B2"))
        self.assertEqual(
            league.last_b_steal_award(["B1", "B2"], enabled=True).trainer_id,
            "B2",
        )
        self.assertEqual(
            league.total_points_with_penalties(9, dead_count=2, points_reduction=1.5),
            7.1,
        )

    def test_rewards_and_snapshot_contract_are_json_safe(self) -> None:
        version = _version()
        standings = rewards.build_standings_from_rankings(
            matchday_id="md-1",
            rank_a=["Anto", "Victor"],
            rank_b=["Samu", "Rober"],
            version=version,
            penalties_by_trainer={"Samu": PenaltySummary(dead_count=2, dead_points_penalty=0.4)},
        )
        points, coins = rewards.sum_awards(standings)

        built = snapshots.build_matchday_snapshot(
            snapshot_id="snap-1",
            matchday_id="md-1",
            season_id="season-1",
            matchday_number=1,
            closed_at=1780000000,
            version=version,
            rank_a=["Anto", "Victor"],
            rank_b=["Samu", "Rober"],
            division_composition={"A": ("Anto", "Victor"), "B": ("Samu", "Rober")},
            penalties_by_trainer={"Samu": PenaltySummary(dead_count=2, dead_points_penalty=0.4)},
        )
        payload = to_jsonable(built)

        self.assertEqual(points, {"Anto": 9, "Victor": 8, "Samu": 7, "Rober": 6})
        self.assertEqual(coins["Anto"], 15)
        self.assertEqual(payload["points_awarded"]["Samu"], 7)
        self.assertEqual(payload["penalties"]["Samu"]["dead_count"], 2)

    def test_shop_selection_and_purchase_decisions_are_deterministic(self) -> None:
        selected = shop.select_shop_promotions(
            get_catalog(),
            closed_round=3,
            purchase_counts={1: {}, 2: {}, 3: {}},
            discount_history=[],
            purchased_items={"Menta de Naturaleza"},
            rng=random.Random(17),
        )
        selected_names = {item["name"] for item in selected}

        self.assertNotIn("Menta de Naturaleza", selected_names)
        self.assertNotIn("Chapa Dorada", selected_names)
        self.assertEqual(shop.discount_price(12, "mega", item="Revivir Pokemon"), 8)

        discount = {
            "id": 10,
            "jornada": 4,
            "active": True,
            "activates_at": 1000,
            "stock_total": 2,
            "stock_used": 1,
            "base_price": 8,
            "discount_price": 6,
        }
        allowed = shop.evaluate_discount_purchase(
            discount,
            trainer_id="Anto",
            promotion_id=10,
            matchday_number=4,
            now=1000,
        )
        claimed = shop.evaluate_discount_purchase(
            discount,
            trainer_id="Anto",
            promotion_id=10,
            matchday_number=4,
            now=1000,
            claimed_discount_ids={10},
        )

        self.assertTrue(allowed.allowed)
        self.assertTrue(allowed.stock_exhausted)
        self.assertEqual(allowed.effective_price, 6)
        self.assertEqual(claimed.reason, "already_claimed")

    def test_trainer_status_and_robbed_cycle_are_pure(self) -> None:
        flags = {"robbed": True, "robbed_by": "Sergio"}
        transitioned = trainers.apply_status_transition(
            flags,
            TrainerStatus.ABANDONED,
            by_user="Anto",
            now=2000,
        )

        self.assertEqual(trainers.status_from_flags(transitioned), TrainerStatus.ABANDONED)
        self.assertNotIn("robbed", transitioned)
        self.assertEqual(trainers.status_labels_for_flags(transitioned), ("Abandono",))

        result = trainers.mark_trainer_robbed(
            {"Anto": {}, "Victor": {"robbed": True}},
            "Anto",
            by_user="Samu",
            active_trainers=("Anto", "Victor"),
            now=3000,
        )
        self.assertTrue(result.marked)
        self.assertTrue(result.cycle_reset)
        self.assertFalse(result.flags_by_trainer["Anto"].get("robbed", False))
        self.assertFalse(result.flags_by_trainer["Victor"].get("robbed", False))

    def test_team_lock_activity_hall_archive_and_trials_services(self) -> None:
        version = _version()
        milotic = PublicPokemon(species="Milotic", level=55)
        lock_validation = team_locks.validate_team_lock(
            trainer_id="Anto",
            participant_ids=version.participant_ids,
            matchday_number=1,
            team=(milotic,),
            rules=version.rules,
        )
        locked = team_locks.build_team_lock(
            lock_id="lock-1",
            season_id="season-1",
            trainer_id="Anto",
            locked_at="2026-08-15T00:00:00Z",
            team=(milotic,),
            matchday_number=1,
        )
        event = activity.build_team_locked_event(
            trainer_id="Anto",
            matchday_number=1,
            lock_id="lock-1",
            created_at=1780000000,
        )
        hall_entry = hall_of_fame.build_league_hall_entry(
            entry_id="hof-1",
            title="Temporada Test - Liga",
            champion_id="Anto",
            runner_up_id="Victor",
            created_at="2026-08-15T00:00:00Z",
            frozen_team=(milotic,),
        )
        archive = archives.build_season_archive(
            archive_id="archive-1",
            season_id="season-1",
            label="Temporada Test",
            archived_at="2026-08-15T00:00:00Z",
            season_versions=(version,),
            matchday_snapshots=(),
            trainer_statuses={"Anto": TrainerStatus.ACTIVE},
            champion_id="Anto",
            champion_team=(milotic,),
            hall_entries=(hall_entry,),
        )

        self.assertTrue(lock_validation.allowed)
        self.assertEqual(locked.team[0].species, "Milotic")
        self.assertEqual(event.context["matchday_number"], 1)
        self.assertTrue(activity.visible_to(event, "Victor").visible)
        self.assertEqual(hall_entry.competition, CompetitionType.LEAGUE)
        self.assertEqual(archive.hall_entries[0].champion_id, "Anto")
        self.assertEqual(trials.jury_majority(5), 3)
        self.assertEqual(
            trials.verdict_from_votes(("guilty", "guilty", "guilty"), jury_size=5).value,
            "guilty",
        )

    def test_activity_dedupe_and_visibility_are_pure(self) -> None:
        first = activity.build_purchase_completed_event(
            trainer_id="Samu",
            item="Restos",
            price=8,
            purchase_id=10,
            created_at=1000,
            matchday_number=3,
        )
        second = activity.build_purchase_completed_event(
            trainer_id="Samu",
            item="Restos",
            price=8,
            purchase_id=10,
            created_at=2000,
            matchday_number=3,
        )
        admin_event = activity.build_activity_event(
            first.type,
            created_at=3000,
            actor_id="Anto",
            trainer_id="Victor",
            visibility=Visibility.ADMIN,
            dedupe_key="admin-only",
        )

        self.assertEqual(len(activity.dedupe_events((first, second))), 1)
        self.assertFalse(activity.visible_to(admin_event, "Victor").visible)
        self.assertTrue(activity.visible_to(admin_event, "Anto").visible)


if __name__ == "__main__":
    unittest.main()
