from copy import deepcopy
from dataclasses import replace
import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from team_lock_fixtures import MATCHDAY, OTHER, SAVE, SEASON, MemoryAtomicTeamLocks
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier


class TeamLockApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryAtomicTeamLocks()
        self.principals = FakePrincipalRepository()
        self.verifier = FakeTokenVerifier()
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=self.verifier, principal_repository=self.principals,
            team_lock_repository=self.repository,
        )))
        self.path = f"/v1/seasons/{SEASON}/matchdays/{MATCHDAY}/team-lock"

    def put(self, **body):
        return self.client.put(self.path, headers={"Authorization": "Bearer dummy"}, json=body or {"save_file_id": SAVE})

    def rejected(self, status):
        response = self.put()
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(self.repository.mutations, [])
        return response

    def test_tl01_missing_bearer(self):
        self.assertEqual(self.client.put(self.path, json={"save_file_id": SAVE}).status_code, 401)

    def test_tl02_invalid_bearer(self):
        self.verifier.fail = InvalidSessionError()
        self.rejected(401)

    def test_tl03_disabled_admin(self):
        self.principals.trainer = replace(self.principals.trainer, globally_enabled=False)
        self.rejected(403)

    def test_tl04_missing_season(self):
        self.repository.source = replace(self.repository.source, season=None)
        self.rejected(404)

    def test_tl05_missing_matchday(self):
        self.repository.source = replace(self.repository.source, matchday=None)
        self.rejected(404)

    def test_tl06_matchday_other_season(self):
        self.repository.change("matchday", season_id=OTHER)
        self.rejected(404)

    def test_tl07_not_enrolled(self):
        self.repository.source = replace(self.repository.source, participant=None)
        self.rejected(404)

    def test_tl08_inactive_participation(self):
        for status in ("retired", "abandoned", "disqualified"):
            with self.subTest(status=status):
                self.repository.change("participant", status=status)
                self.rejected(403)

    def test_tl09_missing_save(self):
        self.repository.source = replace(self.repository.source, save=None)
        self.rejected(404)

    def test_tl10_foreign_save(self):
        self.repository.change("save", trainer_id=OTHER)
        self.rejected(404)

    def test_tl11_save_other_season(self):
        self.repository.change("save", season_id=OTHER)
        self.rejected(404)

    def test_tl12_missing_parsed_save(self):
        self.repository.source = replace(self.repository.source, parsed=None)
        self.rejected(409)

    def test_tl13_less_than_six(self):
        party = self.repository.source.parsed["payload"]["party"]
        for size in range(6):
            with self.subTest(size=size):
                self.repository.change("parsed", payload={"party": party[:size]})
                self.rejected(409)

    def test_tl14_exactly_six(self):
        response = self.put()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["trainer_id"], TRAINER_ID)
        self.assertEqual(len(response.json()["public_team_snapshot"]), 6)

    def test_tl15_more_than_six(self):
        self.repository.source.parsed["payload"]["party"].append({"slot_number": 7, "pokemon": {"species": "Crobat"}})
        self.rejected(409)

    def test_tl16_private_snapshot_persisted(self):
        self.assertEqual(self.put().status_code, 200)
        mon = self.repository.mutations[0].private_team_snapshot[0]
        self.assertEqual(mon["ivs"]["hp"], 31)
        self.assertEqual(mon["ability"], "Competitive")
        self.assertEqual(mon["original_trainer"], "private-owner")
        self.assertEqual(mon["moves"][0]["pp"], 0)

    def test_tl17_public_snapshot_persisted(self):
        self.put()
        self.assertEqual(self.repository.mutations[0].public_team_snapshot[0]["species"], "Milotic")
        self.assertEqual(self.repository.mutations[0].public_team_snapshot[0]["moves"][0]["name"], "Surf")

    def test_tl18_no_private_leak(self):
        self.put()
        for mon in self.repository.mutations[0].public_team_snapshot:
            for field in ("ability", "nature", "ivs", "evs", "original_trainer"):
                self.assertNotIn(field, mon)
            self.assertEqual(mon["metadata"], {})
            self.assertNotIn("dummy-never-public", str(mon))

    def test_tl19_authoritative_hash(self):
        self.assertEqual(self.put().json()["save_sha256"], "a" * 64)
        self.assertEqual(self.put(save_file_id=SAVE, save_sha256="b" * 64).status_code, 422)

    def test_tl20_self_service_even_for_admin(self):
        self.assertTrue(self.principals.trainer.is_admin)
        for key, value in (("trainer_id", OTHER), ("private_team_snapshot", []), ("is_late", True)):
            with self.subTest(key=key):
                self.assertEqual(self.put(**{"save_file_id": SAVE, key: value}).status_code, 422)
        self.assertEqual(self.repository.mutations, [])
        self.assertEqual(self.put().json()["trainer_id"], TRAINER_ID)

    def test_tl21_first_lock_created(self):
        self.put()
        self.assertEqual(len(self.repository.records), 1)

    def test_tl22_replacement_preserves_identity(self):
        first = self.put().json()
        self.repository.change("save", id=OTHER, sha256="b" * 64)
        self.repository.change("parsed", save_file_id=OTHER)
        self.repository.source.parsed["payload"]["party"][0]["pokemon"]["species"] = "Crobat"
        second = self.put(save_file_id=OTHER).json()
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["save_file_id"], OTHER)
        self.assertEqual(second["save_sha256"], "b" * 64)
        self.assertEqual(second["private_team_snapshot"][0]["species"], "Crobat")
        self.assertEqual(len(self.repository.records), 1)

    def test_tl23_repeated_request_has_one_resource(self):
        self.assertEqual(self.put().json()["id"], self.put().json()["id"])
        self.assertEqual(len(self.repository.records), 1)

    def test_tl24_activity_created(self):
        self.put()
        self.assertEqual(next(iter(self.repository.events.values()))["type"], "TEAM_LOCKED")

    def test_tl25_activity_deduplication(self):
        self.put()
        self.put()
        self.assertEqual(len(self.repository.events), 1)

    def test_tl26_replacement_keeps_first_event(self):
        self.put()
        first = deepcopy(self.repository.events)
        self.repository.source.parsed["payload"]["party"][0]["pokemon"]["species"] = "Crobat"
        self.put()
        self.assertEqual(first, self.repository.events)

    def test_tl27_snapshot_deeply_independent(self):
        self.put()
        stored = next(iter(self.repository.records.values()))
        self.repository.source.parsed["payload"]["party"][0]["pokemon"]["ivs"]["hp"] = 0
        self.repository.source.parsed["payload"]["party"][0]["pokemon"]["moves"][0]["name"] = "Splash"
        self.assertEqual(stored.private_team_snapshot[0]["ivs"]["hp"], 31)
        self.assertEqual(stored.public_team_snapshot[0]["moves"][0]["name"], "Surf")

    def test_tl28_closed_or_cancelled_matchday(self):
        for status in ("closed", "cancelled"):
            with self.subTest(status=status):
                self.repository.change("matchday", status=status)
                self.rejected(409)

    def test_tl29_no_operational_secret_fields(self):
        data = self.put().json()
        self.assertEqual(set(data), {"id", "season_id", "matchday_id", "trainer_id", "season_player_id",
                                   "save_file_id", "save_sha256", "locked_at", "deadline_at", "is_late",
                                   "public_team_snapshot", "private_team_snapshot", "created_at", "updated_at"})
        for field in ("service_role", "pepper", "auth_user_id", "storage_key", "parsed_payload"):
            self.assertNotIn(field, str(data))

    def test_tl30_atomic_repository_failure_not_success(self):
        self.repository.fail_event = True
        self.rejected(503)
        self.assertEqual(self.repository.records, {})
        self.assertEqual(self.repository.events, {})

    def test_unsupported_or_failed_parser_rejected(self):
        for values in ({"schema_version": 2}, {"status": "failed"}, {"parser_version": "different"}, {"save_file_id": OTHER}):
            with self.subTest(values=values):
                self.setUp()
                self.repository.change("parsed", **values)
                self.rejected(409)

    def test_ineligible_save_and_season_rejected(self):
        for values in ({"deleted_at": "2026-09-21"}, {"parser_status": "pending"}, {"parser_status": "failed"}, {"parser_status": "stale"}, {"sha256": "bad"}):
            with self.subTest(values=values):
                self.setUp()
                self.repository.change("save", **values)
                self.rejected(409)
        for status in ("draft", "finished", "archived", "discarded"):
            with self.subTest(status=status):
                self.setUp()
                self.repository.change("season", status=status)
                self.rejected(409)

    def test_malformed_party_and_identity_mismatch_rejected(self):
        for payload in ({"party": [None] * 6}, {"party": [{"slot_number": 1, "pokemon": {}}] * 6},
                        dict(self.repository.source.parsed["payload"], trainer_id=OTHER)):
            with self.subTest(payload=payload):
                self.repository.change("parsed", payload=payload)
                self.rejected(409)

    def test_legacy_flat_party_reuses_existing_normalizer(self):
        self.repository.change("parsed", payload={"party": [{"species_name": "Milotic", "ivs": {"hp": 31}, "ability": "Competitive"}] * 6})
        self.assertEqual(self.put().status_code, 200)
        self.assertEqual(self.repository.mutations[0].private_team_snapshot[0]["ivs"]["hp"], 31)

    def test_open_matchday_and_no_deadline(self):
        self.repository.change("matchday", status="open")
        data = self.put().json()
        self.assertIsNone(data["deadline_at"])
        self.assertFalse(data["is_late"])

    def test_invalid_uuid_and_extra_fields(self):
        self.assertEqual(self.put(save_file_id="not-a-uuid").status_code, 422)
        self.path = self.path.replace(SEASON, "not-a-uuid")
        self.assertEqual(self.put().status_code, 422)

    def test_backend_not_configured(self):
        client = TestClient(create_app(container=ApiContainer(token_verifier=self.verifier, principal_repository=self.principals)))
        response = client.put(self.path, json={"save_file_id": SAVE}, headers={"Authorization": "Bearer dummy"})
        self.assertEqual(response.status_code, 503)
