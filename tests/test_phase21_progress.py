"""Native facts, old receipt compatibility and gated economic authority."""

import json
import unittest
from copy import deepcopy

import test_phase16b_xy as xy
import test_phase16d_save_sync as sync
import test_phase18_oras as oras
import test_phase19_sm as sm
import test_phase20_usum as usum
from pydantic import ValidationError
from test_phase10_5l_progress import ProgressTests, observation

from app.application.save_ingestion import TrustedSaveIngestion, parsed_payload
from app.save_parser.models import NativeGameProgress
from app.save_parser.registration import observation_digest

GAMES = ("X", "Y", "OR", "AS", "SN", "MN", "US", "UM")


def facts(game="X", **changes):
    gym = game in GAMES[:4]
    return (
        dict(
            schema_version=1,
            model="gym_badges" if gym else "island_challenge",
            badge_flags=[False] * 8 if gym else None,
            league_access=None,
            league_visited=None,
            league_fly_unlocked=False if gym else None,
            hall_of_fame_entered=False if gym else None,
            champion_defeated=False,
            island_stamp_flags=None if gym else [False] * 4,
            island_challenge_completed=None if gym else False,
        )
        | changes
    )


def payload(game="X"):
    factory = (
        xy.xy_payload
        if game in GAMES[:2]
        else oras.oras_payload
        if game in GAMES[2:4]
        else sm.sm_payload
        if game in GAMES[4:6]
        else usum.ultra_payload
    )
    value = factory(game)
    value["native_progress"] = facts(game)
    return value


class NativeProgressContractTests(unittest.TestCase):
    def test_eight_games_keep_legacy_digest_and_reward_evidence(self):
        for game in GAMES:
            value = payload(game)
            native = sm.read(value)
            old = sm.read({k: v for k, v in value.items() if k != "native_progress"})
            self.assertEqual(
                observation_digest(native, sync.VERSION),
                observation_digest(old, sync.VERSION),
            )
            self.assertIsNone(native.progress)
            registered = parsed_payload(native, sync.SID, sync.TRAINER_ID, sync.HASH)
            self.assertIsNone(registered["observed_progress"]["progress"])
            self.assertEqual(registered["identity_policy_version"], 2)
            self.assertEqual(registered["native_progress"], facts(game))
            self.assertNotIn(
                "identity_policy_version",
                parsed_payload(old, sync.SID, sync.TRAINER_ID, sync.HASH),
            )

    def test_native_shape_is_strict_and_game_specific(self):
        for game in GAMES:
            for change in (
                dict(schema_version=True),
                dict(schema_version=2),
                dict(league_access=True),
                dict(champion_defeated="true"),
                dict(unapproved_reward=12),
            ):
                with (
                    self.subTest(game=game, change=change),
                    self.assertRaises(ValidationError),
                ):
                    NativeGameProgress.model_validate_json(
                        json.dumps(facts(game, **change))
                    )
            wrong = payload(game)
            wrong["native_progress"] = facts("US" if game in GAMES[:4] else "X")
            with self.assertRaises(ValidationError):
                sm.read(wrong)
        for flags in ([True] * 7, [1] * 8, ["false"] * 8):
            with self.assertRaises(ValidationError):
                sm.read(payload() | {"native_progress": facts(badge_flags=flags)})
        with self.assertRaises(ValidationError):
            sm.read(
                payload("US") | {"native_progress": facts("US", badge_flags=[True] * 8)}
            )

    def test_replay_of_old_receipt_does_not_backfill_native_identity_or_progress(self):
        for game in GAMES:
            repo, parser = sync.Repository(), sync.FakeParser()
            parser.version = sync.VERSION
            value = payload(game)
            parser.value = sm.read(
                {k: v for k, v in value.items() if k != "native_progress"}
            )
            service = TrustedSaveIngestion(repo, parser)
            kwargs = dict(
                season_id=sync.SID,
                trainer_id=sync.TRAINER_ID,
                raw_hash=sync.HASH,
                expected_save_id=None,
                local_digest=observation_digest(parser.value, sync.VERSION),
                data=sync.DATA,
            )
            first = service.receive(**kwargs)
            self.assertIsNone(repo.writes[0]["identity_plan"])
            parser.value = sm.read(value)
            self.assertEqual(service.receive(**kwargs), first)
            self.assertEqual((parser.calls, len(repo.writes), len(repo.raw)), (1, 1, 1))

    def test_trusted_registration_builds_schema2_and_retains_ambiguity(self):
        for game in GAMES:
            repo, parser = sync.Repository(), sync.FakeParser()
            parser.version, parser.value = sync.VERSION, sm.read(payload(game))
            service = TrustedSaveIngestion(repo, parser)
            service.receive(
                season_id=sync.SID,
                trainer_id=sync.TRAINER_ID,
                raw_hash=sync.HASH,
                expected_save_id=None,
                local_digest=observation_digest(parser.value, sync.VERSION),
                data=sync.DATA,
            )
            plan = repo.writes[0]["identity_plan"]
            self.assertEqual(
                (plan["identity_schema_version"], plan["reconciliation_version"]),
                (2, 2),
            )
            # Existing synthetic helpers deliberately share EC and lack met facts.
            self.assertTrue(
                all(
                    b["outcome"] == "AMBIGUOUS" and b["pokemon_entity_id"] is None
                    for b in plan["bindings"]
                )
            )
            self.assertTrue(
                all(b["legacy_fingerprints"] == [] for b in plan["bindings"])
            )


class NativeProgressApiTests(ProgressTests):
    # Inherited scope/auth/unknown/legacy tests stay applicable to the same reader.
    def test_native_progress_api_all_games_no_private_facts_or_rewards(self):
        for game in GAMES:
            self.row = observation()
            self.row.update(game=game, progress=None, native_progress=facts(game))
            result = self.get()
            self.assertEqual(result.status_code, 200)
            body = result.json()
            self.assertEqual(body["state"], "observed")
            self.assertEqual(body["badges_count"], 0 if game in GAMES[:4] else None)
            self.assertEqual(
                body["reward_state"],
                "pending_validation" if game in GAMES[:4] else "pending_policy",
            )
            for private in (
                "schema_version",
                "badge_flags",
                "island_stamp_flags",
                "source_hash",
                "identity_evidence",
            ):
                self.assertNotIn(private, result.text)
            self.assertIsNone(body["league_access"])
        self.assertEqual(self.store.calls, [])

    def test_badge_count_and_champion_are_independent_and_can_regress_as_facts(self):
        for game in GAMES[:4]:
            for count, champion in ((8, False), (8, True), (0, None), (2, False)):
                self.row = observation()
                self.row.update(
                    game=game,
                    progress=None,
                    native_progress=facts(
                        game,
                        badge_flags=[i < count for i in range(8)],
                        champion_defeated=champion,
                    ),
                )
                body = self.get().json()
                self.assertEqual(body["badges_count"], count)
                self.assertIs(body["champion_defeated"], champion)
        self.assertEqual(self.store.calls, [])

    def test_islands_preserve_sparse_native_flags_and_never_become_badges(self):
        self.row = observation()
        self.row.update(
            game="UM",
            progress=None,
            native_progress=facts(
                "UM",
                island_stamp_flags=[False, True, False, True],
                champion_defeated=True,
            ),
        )
        body = self.get().json()
        self.assertEqual(body["completed_islands"], ["akala", "poni"])
        self.assertIsNone(body["badges_count"])
        self.assertIsNone(body["regions"])
        self.assertIs(body["island_challenge_completed"], False)

    def test_malformed_or_cross_game_native_facts_fail_closed(self):
        self.row = observation()
        self.row.update(game="X", progress=None, native_progress=facts())
        original = deepcopy(self.row)
        for key, bad in (
            ("game", "B2"),
            ("observed_at", None),
            ("native_progress", facts("US")),
            ("native_progress", facts(champion_defeated=1)),
        ):
            self.row = deepcopy(original) | {key: bad}
            self.assertEqual(self.get().status_code, 503)


if __name__ == "__main__":
    unittest.main()
