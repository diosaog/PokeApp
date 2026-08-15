from __future__ import annotations

from pathlib import Path
import unittest

from app.domain.activity import ActivityEvent, ActivityEventType
from app.domain.archives import SeasonArchive
from app.domain.common import CompetitionType, Visibility, to_jsonable
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.league import LeagueStanding, MatchdaySnapshot
from app.domain.legacy import (
    activity_event_from_legacy,
    box_from_legacy,
    matchday_snapshot_from_legacy,
    season_version_from_legacy,
    team_lock_from_legacy,
)
from app.domain.pokemon import PokemonMove, PrivatePokemon, PublicPokemon, StatSpread
from app.domain.saves import BoxSlot, PokemonBox
from app.domain.seasons import (
    Division,
    Season,
    SeasonLifecycle,
    SeasonPlayer,
    SeasonRules,
    SeasonVersion,
)
from app.domain.shop import Purchase, PurchaseStatus, ShopItem, ShopPromotion
from app.domain.team_locks import TeamLock
from app.domain.trainers import Trainer, TrainerFlags, TrainerStatus
from app.domain.trials import Penalty, PenaltyType, TrialCase


def _season_version() -> SeasonVersion:
    return SeasonVersion(
        id="v1",
        season_id="season-1",
        name="Temporada Test",
        effective_matchday=1,
        max_matchdays=4,
        participant_ids=("Anto", "Victor"),
        division_sizes=(1, 1),
        promotion_relegation_count=1,
        points_by_position={1: 9, 2: 8},
        coins_by_position={1: 15, 2: 14},
        rules=SeasonRules(team_lock_required=True, last_b_gets_steal=True),
    )


class DomainContractTests(unittest.TestCase):
    def test_domain_modules_do_not_import_infrastructure(self) -> None:
        forbidden = (
            "import streamlit",
            "from storage",
            "import storage",
            "supabase",
            "discord",
            "conex_pkhex",
        )
        domain_root = Path(__file__).resolve().parents[1] / "app" / "domain"
        for path in domain_root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            lowered = source.lower()
            for needle in forbidden:
                self.assertNotIn(needle, lowered, msg=f"{path.relative_to(domain_root)} imports {needle}")

    def test_season_contracts_are_json_safe(self) -> None:
        season = Season(
            id="season-1",
            name="Temporada Test",
            lifecycle=SeasonLifecycle.ACTIVE,
            active_version_id="v1",
            started_at="2026-08-15T00:00:00Z",
        )
        version = _season_version()
        division = Division(id="division-a", season_id=season.id, name="Liga A", tier_order=1)
        player = SeasonPlayer(
            id="sp-anto",
            season_id=season.id,
            trainer_id="Anto",
            status=TrainerStatus.ACTIVE,
            division_id=division.id,
        )

        payload = to_jsonable({"season": season, "version": version, "division": division, "player": player})

        self.assertEqual(payload["season"]["lifecycle"], "active")
        self.assertEqual(payload["version"]["rules"]["team_lock_required"], True)
        self.assertEqual(payload["version"]["division_sizes"], [1, 1])
        self.assertEqual(payload["version"]["points_by_position"], {"1": 9, "2": 8})
        self.assertEqual(payload["player"]["status"], "active")

    def test_trainer_identity_is_separate_from_status_and_flags(self) -> None:
        trainer = Trainer(id="Anto", display_name="Anto")
        flags = TrainerFlags(trainer_id=trainer.id, robbed=True, robbed_by="Victor")
        player = SeasonPlayer(
            id="sp-anto",
            season_id="season-1",
            trainer_id=trainer.id,
            status=TrainerStatus.ABANDONED,
        )

        self.assertEqual(trainer.id, "Anto")
        self.assertNotIn("status", to_jsonable(trainer))
        self.assertTrue(to_jsonable(flags)["robbed"])
        self.assertEqual(to_jsonable(player)["status"], "abandoned")

    def test_private_pokemon_can_be_projected_to_public(self) -> None:
        private = PrivatePokemon(
            species="Milotic",
            nickname="Pau",
            level=55,
            types=("Agua",),
            item="Restos",
            moves=(PokemonMove("Recover", pp=16), PokemonMove("Scald", pp=15)),
            ability="Competitive",
            nature="Bold",
            ivs=StatSpread(hp=31, atk=0, defense=31, spa=31, spd=31, spe=20),
            evs=StatSpread(hp=252, defense=252),
        )

        public = private.to_public()
        public_payload = to_jsonable(public)
        private_payload = to_jsonable(private)

        self.assertEqual(public.species, "Milotic")
        self.assertNotIn("ability", public_payload)
        self.assertNotIn("ivs", public_payload)
        self.assertEqual(private_payload["ivs"]["hp"], 31)
        self.assertEqual(private_payload["ability"], "Competitive")

    def test_pokemon_box_requires_empty_slots_to_be_preserved(self) -> None:
        slots = tuple(BoxSlot(box_number=1, slot_number=i) for i in range(1, 31))
        box = PokemonBox(box_number=1, name="Caja 1", slots=slots)

        self.assertEqual(len(box.slots), 30)
        self.assertIsNone(box.slots[0].pokemon)

        with self.assertRaises(ValueError):
            PokemonBox(box_number=1, name="Rota", slots=slots[:29])

    def test_legacy_box_adapter_preserves_zero_based_slots_and_empties(self) -> None:
        box = box_from_legacy(
            box_number=1,
            name="Caja 1",
            pokemon_rows=[
                {"species": "Pichu", "slot_index": 0, "level": 22},
                {"species": "Entei", "slot_index": 5, "level": 40},
            ],
        )

        self.assertEqual(len(box.slots), 30)
        self.assertEqual(box.slots[0].pokemon.species, "Pichu")
        self.assertIsNone(box.slots[1].pokemon)
        self.assertEqual(box.slots[5].pokemon.species, "Entei")

    def test_matchday_snapshot_freezes_config_and_awards(self) -> None:
        standing = LeagueStanding(
            matchday_id="season-1:matchday:1",
            trainer_id="Anto",
            division_id="division-a",
            position=1,
            division_position=1,
            points_awarded=9,
            coins_awarded=15,
        )
        snapshot = MatchdaySnapshot(
            id="snap-1",
            schema_version=1,
            matchday_id="season-1:matchday:1",
            season_id="season-1",
            matchday_number=1,
            closed_at="2026-08-15T00:00:00Z",
            season_version=_season_version(),
            division_composition={"division-a": ("Anto",), "division-b": ("Victor",)},
            standings=(standing,),
            points_awarded={"Anto": 9},
            coins_awarded={"Anto": 15},
        )

        payload = to_jsonable(snapshot)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["season_version"]["id"], "v1")
        self.assertEqual(payload["division_composition"]["division-a"], ["Anto"])
        self.assertEqual(payload["standings"][0]["points_awarded"], 9)

    def test_activity_event_legacy_mapping_uses_domain_values(self) -> None:
        event = activity_event_from_legacy(
            {
                "id": "evt-1",
                "type": "TEAM_LOCKED",
                "created_at": 1780000000,
                "actor": "Anto",
                "trainer": "Anto",
                "context": {"jornada": 3},
                "payload": {"is_late": False},
                "visibility": "trainer-only",
                "dedupe_key": "TEAM_LOCKED:3:Anto",
            }
        )

        payload = to_jsonable(event)

        self.assertEqual(event.type, ActivityEventType.TEAM_LOCKED)
        self.assertEqual(payload["type"], "team_locked")
        self.assertEqual(payload["visibility"], "owner")
        self.assertTrue(payload["created_at"].endswith("Z"))

    def test_shop_contracts_separate_catalog_promotion_purchase(self) -> None:
        item = ShopItem(
            id="leftovers",
            category="competitivos",
            name="Restos",
            description="Restaura PS por turno.",
            base_price=8,
        )
        promo = ShopPromotion(
            id="promo-1",
            item_id=item.id,
            season_id="season-1",
            matchday_number=3,
            base_price=8,
            discount_price=6,
            stock_total=2,
            stock_used=1,
        )
        purchase = Purchase(
            id="purchase-1",
            trainer_id="Anto",
            item_id=item.id,
            item_name=item.name,
            quantity=1,
            unit_price=6,
            total_price=6,
            purchased_at="2026-08-15T00:00:00Z",
            status=PurchaseStatus.PENDING,
            promotion_id=promo.id,
            base_unit_price=8,
        )

        self.assertEqual(to_jsonable(promo)["kind"], "normal")
        self.assertEqual(to_jsonable(purchase)["promotion_id"], "promo-1")
        with self.assertRaises(ValueError):
            Purchase(
                id="bad",
                trainer_id="Anto",
                item_id=item.id,
                item_name=item.name,
                quantity=2,
                unit_price=6,
                total_price=6,
                purchased_at="2026-08-15T00:00:00Z",
            )

    def test_trial_case_uses_penalty_value_objects(self) -> None:
        case = TrialCase(
            id="case-1",
            season_id="season-1",
            case_no=1,
            title="Uso ilegal",
            creator_id="Anto",
            accused_id="Victor",
            penalties=(Penalty(type=PenaltyType.POINTS_REDUCTION, amount=1.5),),
            created_at="2026-08-15T00:00:00Z",
        )

        payload = to_jsonable(case)

        self.assertEqual(payload["status"], "proposed")
        self.assertEqual(payload["penalties"][0]["type"], "points_reduction")

    def test_hall_and_archive_use_public_frozen_team(self) -> None:
        public_mon = PublicPokemon(species="Milotic", moves=(PokemonMove("Recover"),))
        entry = HallOfFameEntry(
            id="hof-1",
            competition=CompetitionType.LEAGUE,
            title="Temporada Test - Liga",
            champion_id="Anto",
            runner_up_id="Victor",
            created_at="2026-08-15T00:00:00Z",
            frozen_team=(public_mon,),
            source="archive",
        )
        archive = SeasonArchive(
            id="archive-1",
            schema_version=1,
            season_id="season-1",
            label="Temporada Test",
            archived_at="2026-08-15T00:00:00Z",
            season_versions=(_season_version(),),
            champion_id="Anto",
            champion_team=(public_mon,),
            hall_entries=(entry,),
        )

        payload = to_jsonable(archive)

        self.assertEqual(payload["champion_team"][0]["species"], "Milotic")
        self.assertNotIn("ivs", payload["champion_team"][0])
        self.assertEqual(payload["hall_entries"][0]["competition"], "league")

    def test_team_lock_uses_frozen_public_team_and_save_reference(self) -> None:
        lock = TeamLock(
            id="lock-1",
            season_id="season-1",
            trainer_id="Anto",
            locked_at="2026-08-15T00:00:00Z",
            matchday_number=1,
            save_record_id="save-1",
            save_sha256="abc123",
            is_late=False,
            team=(PublicPokemon(species="Milotic"),),
        )

        payload = to_jsonable(lock)

        self.assertEqual(payload["team"][0]["species"], "Milotic")
        self.assertNotIn("ivs", payload["team"][0])
        self.assertEqual(payload["save_record_id"], "save-1")

    def test_legacy_team_lock_adapter_freezes_public_team(self) -> None:
        lock = team_lock_from_legacy(
            {
                "jornada": 2,
                "user": "Anto",
                "locked_at": 1780000000,
                "save_id": 99,
                "save_sha256": "hash",
                "team": [
                    {
                        "species": "Hydreigon",
                        "level": 71,
                        "ability": "Levitate",
                        "ivs": {"hp": 31},
                        "moves": ["Dark Pulse"],
                    }
                ],
            },
            season_id="season-1",
        )

        payload = to_jsonable(lock)

        self.assertEqual(payload["matchday_number"], 2)
        self.assertEqual(payload["team"][0]["species"], "Hydreigon")
        self.assertNotIn("ability", payload["team"][0])
        self.assertNotIn("ivs", payload["team"][0])

    def test_legacy_snapshot_adapter_maps_current_shape(self) -> None:
        snapshot = matchday_snapshot_from_legacy(
            {
                "schema_version": 1,
                "round_no": 1,
                "closed_at": 1780000000,
                "season_config_version": {
                    "id": "v1",
                    "name": "Temporada Legacy",
                    "effective_round": 1,
                    "max_rounds": 4,
                    "players": ["Anto", "Victor"],
                    "division_sizes": [1, 1],
                    "movement_count": 1,
                    "points_by_position": {"1": 9, "2": 8},
                    "coins_by_position": {"1": 15, "2": 14},
                    "rules": {"team_lock_required": True, "last_b_gets_steal": True, "cup_is_separate": True},
                },
                "division_snapshot": {"A": ["Anto"], "B": ["Victor"]},
                "standings": [
                    {
                        "user": "Anto",
                        "division": "A",
                        "division_position": 1,
                        "position": 1,
                        "points_awarded": 9,
                        "coins_awarded": 15,
                        "penalties": {"dead_count": 0, "trainer_status": "active"},
                    }
                ],
                "points_awarded": {"Anto": 9},
                "coins_awarded": {"Anto": 15},
            },
            season_id="season-1",
        )
        version = season_version_from_legacy(
            {
                "id": "v1",
                "name": "Temporada Legacy",
                "effective_round": 1,
                "max_rounds": 4,
                "players": ["Anto"],
                "division_sizes": [1],
            },
            season_id="season-1",
        )

        self.assertEqual(snapshot.matchday_number, 1)
        self.assertEqual(snapshot.standings[0].trainer_id, "Anto")
        self.assertEqual(snapshot.season_version.metadata.cup_is_separate, True)
        self.assertEqual(version.participant_ids, ("Anto",))


if __name__ == "__main__":
    unittest.main()
