"""Synthetic contract tests; public gameplay evidence lives in its own manifest."""

import json
import unittest
from copy import deepcopy

import test_phase16d_save_sync as sync
import test_phase18_oras as oras
from pydantic import ValidationError

from app.application.save_ingestion import TrustedSaveIngestion, parsed_payload
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.models import ObservedSave, compare_observations
from app.save_parser.registration import observation_digest


def sm_payload(game="SN"):
    value = oras.oras_payload(game)
    value.update(generation=7)
    value["boxes"].append({"number": 32, "slots": [None] * 30})
    value["boxes"][31]["slots"][29], value["boxes"][30]["slots"][29] = (
        value["boxes"][30]["slots"][29],
        None,
    )
    for p in (value["party"][0], value["boxes"][31]["slots"][29]):
        p.update(species_id=26, type_ids=[12, 13], item_id=776, ability_id=207)
        p["moves"][0]["id"] = 719
        p["identity"].update(format=7, origin_version=30 if game == "SN" else 31)
    return value


def read(value):
    return ObservedSave.model_validate_json(json.dumps(value))


class SMContractTests(unittest.TestCase):
    def test_authenticated_raw_routes_keep_jwt_denials_for_both_games(self):
        # Reuse the existing HTTP contract checks with Gen7 server observations.
        for game in ("SN", "MN"):
            self.repo = sync.Repository()
            self.parser = sync.FakeParser()
            self.parser.value = read(sm_payload(game))
            self.parser.version = sync.VERSION
            self.service = TrustedSaveIngestion(self.repo, self.parser)
            self.digest = observation_digest(self.parser.value, self.parser.version)
            sync.IngestionTests.test_authenticated_raw_api_and_denials(self)
            self.assertIsNone(self.repo.writes[0]["identity_plan"])

    def test_full_960_slots_fit_existing_neutral_transport_limit(self):
        from app.save_parser.cloud import MAX_OBSERVATION_BYTES

        value = sm_payload()
        mon = value["party"][0]
        for box in value["boxes"]:
            box["slots"] = [deepcopy(mon) for _ in range(30)]
        obs = read(value)
        self.assertLess(
            len(obs.model_dump_json().encode()), MAX_OBSERVATION_BYTES - 2048
        )

    def test_both_games_exact_boxes_private_identity_and_unknown_progress(self):
        for game in ("SN", "MN"):
            obs = read(sm_payload(game))
            self.assertEqual(len(obs.boxes), 32)
            self.assertEqual(obs.party[0].type_ids, (12, 13))
            self.assertIsNone(obs.progress)
            self.assertEqual(obs, read(obs.model_dump(mode="json")))
            with self.assertRaises(ValueError):
                obs.identity_observations()
            payload = parsed_payload(obs, sync.SID, sync.TRAINER_ID, sync.HASH)
            self.assertEqual(payload["party"][0]["pokemon"]["item_generation"], 7)
            self.assertEqual(payload["party"][0]["pokemon"]["form"], 1)

    def test_rejects_wrong_game_generation_count_progress(self):
        for change in (
            {"game": "SW"},
            {"game": "SH"},
            {"game": "X"},
            {"generation": 6},
            {"boxes": sm_payload()["boxes"][:-1]},
            {
                "progress": {
                    "schema_version": 1,
                    "primary_region": "unova",
                    "regions": [{"region": "unova", "badge_flags": [False] * 8}],
                }
            },
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                read(sm_payload() | change)

    def test_sm_native_limits_and_required_type_evidence(self):
        for key, bad in (
            ("species_id", 803),
            ("type_ids", None),
            ("type_ids", [12, 18]),
            ("item_id", 921),
            ("ability_id", 233),
        ):
            v = sm_payload()
            v["party"][0][key] = bad
            with self.subTest(key=key), self.assertRaises(ValidationError):
                read(v)
        v = sm_payload()
        v["party"][0]["moves"][0]["id"] = 720
        with self.assertRaises(ValidationError):
            read(v)
        for game in ("OR", "AS"):
            v = oras.oras_payload(game)
            v["party"][0]["species_id"] = 802
            with self.assertRaises(ValidationError):
                read(v)

    def test_private_ec_and_native_format_are_mandatory(self):
        for key, bad in (
            ("encryption_constant", None),
            ("encryption_constant", True),
            ("format", 6),
            ("ot_name", ""),
        ):
            v = sm_payload()
            v["party"][0]["identity"][key] = bad
            with self.subTest(key=key), self.assertRaises(ValidationError):
                read(v)

    def test_local_movement_duplicate_and_ec_change_fail_closed(self):
        v = sm_payload()
        moved = deepcopy(v)
        moved["boxes"][0]["slots"][0], moved["party"][0] = moved["party"][0], None
        self.assertEqual(compare_observations(read(v), read(moved))[0].status, "MOVED")
        moved["party"][0] = deepcopy(moved["boxes"][0]["slots"][0])
        self.assertEqual(
            compare_observations(read(v), read(moved))[0].status, "AMBIGUOUS"
        )
        v2 = deepcopy(v)
        v2["party"][0]["identity"]["encryption_constant"] += 1
        self.assertEqual(compare_observations(read(v), read(v2))[0].status, "AMBIGUOUS")

    def test_current_game_trainer_and_stale_intent_remain_authoritative(self):
        repo = sync.Repository()
        parser = sync.FakeParser()
        parser.value = read(sm_payload())
        parser.version = sync.VERSION
        service = TrustedSaveIngestion(repo, parser)
        for identity in (
            {"game": "MN", "trainer": parser.value.trainer.model_dump(mode="json")},
            {"game": "OR", "trainer": parser.value.trainer.model_dump(mode="json")},
            {
                "game": "SN",
                "trainer": parser.value.trainer.model_dump(mode="json") | {"tid": 1},
            },
        ):
            repo.context.update(current_save_id=sync.SID, save_identity=identity)
            with self.assertRaises(SeasonAdminRejected):
                service.receive(
                    sync.SID,
                    sync.TRAINER_ID,
                    sync.HASH,
                    sync.SID,
                    observation_digest(parser.value, parser.version),
                    sync.DATA,
                )
        self.assertEqual(repo.raw, [])
        self.assertEqual(repo.writes, [])
