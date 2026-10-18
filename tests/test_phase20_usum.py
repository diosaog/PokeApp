"""USUM neutral/ingestion contracts; authentic fixtures have a separate PG gate."""

import unittest
from copy import deepcopy

import test_phase16d_save_sync as sync
import test_phase19_sm as sm
from pydantic import ValidationError

from app.application.save_ingestion import TrustedSaveIngestion, parsed_payload
from app.save_parser.models import compare_observations
from app.save_parser.registration import observation_digest


def ultra_payload(game="US"):
    v = sm.sm_payload(game)
    for p in (v["party"][0], v["boxes"][31]["slots"][29]):
        p.update(species_id=800, type_ids=[13, 8], ability_id=233, item_id=959)
        p["moves"][0]["id"] = 728
        p["identity"]["origin_version"] = 32 if game == "US" else 33
    return v


class UltraContractTests(unittest.TestCase):
    def test_native_limits_game_specific_and_no_progress(self):
        for game in ("US", "UM"):
            obs = sm.read(ultra_payload(game))
            self.assertIsNone(obs.progress)
            self.assertEqual(len(obs.boxes), 32)
            self.assertEqual(obs, sm.read(obs.model_dump(mode="json")))
            with self.assertRaises(ValueError):
                obs.identity_observations()
            payload = parsed_payload(obs, sync.SID, sync.TRAINER_ID, sync.HASH)
            self.assertEqual(payload["party"][0]["pokemon"]["item_generation"], 7)
            self.assertEqual(
                payload["party"][0]["pokemon"]["types"], ["Type #13", "Type #8"]
            )
            # Current game bounds must not follow a transferred Pokemon's origin.
            v = ultra_payload(game)
            v["party"][0]["identity"]["origin_version"] = 30
            sm.read(v)
            for change in (
                {"game": "SN"},
                {"game": "MN"},
                {"generation": 6},
                {"boxes": v["boxes"][:-1]},
                {"game": "SW"},
            ):
                with self.assertRaises(ValidationError):
                    sm.read(v | change)
            for key, bad in (
                ("species_id", 808),
                ("ability_id", 234),
                ("item_id", 960),
                ("type_ids", None),
            ):
                bad_v = deepcopy(v)
                bad_v["party"][0][key] = bad
                with self.assertRaises(ValidationError):
                    sm.read(bad_v)
            v["party"][0]["moves"][0]["id"] = 729
            with self.assertRaises(ValidationError):
                sm.read(v)
        sm.SMContractTests.test_rejects_wrong_game_generation_count_progress(self)

    def test_both_authenticated_raw_routes_and_server_only_observations(self):
        for game in ("US", "UM"):
            self.repo = sync.Repository()
            self.parser = sync.FakeParser()
            self.parser.value = sm.read(ultra_payload(game))
            self.parser.version = sync.VERSION
            self.service = TrustedSaveIngestion(self.repo, self.parser)
            self.digest = observation_digest(self.parser.value, self.parser.version)
            sync.IngestionTests.test_authenticated_raw_api_and_denials(self)
            self.assertIsNone(self.repo.writes[0]["identity_plan"])

    def test_local_identity_movement_and_ambiguity_without_allocations(self):
        v = ultra_payload()
        moved = deepcopy(v)
        moved["boxes"][0]["slots"][0], moved["party"][0] = moved["party"][0], None
        self.assertEqual(
            compare_observations(sm.read(v), sm.read(moved))[0].status, "MOVED"
        )
        moved["party"][0] = deepcopy(moved["boxes"][0]["slots"][0])
        self.assertEqual(
            compare_observations(sm.read(v), sm.read(moved))[0].status, "AMBIGUOUS"
        )
        changed = deepcopy(v)
        changed["party"][0]["identity"]["encryption_constant"] += 1
        self.assertEqual(
            compare_observations(sm.read(v), sm.read(changed))[0].status, "AMBIGUOUS"
        )
