"""17.2 live public collection is scoped, bounded and separate from official locks."""
import unittest
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import test_api_frontend_reads as frontend_tests
from test_api_frontend_reads import PID, SAVE, SID
from test_api_phase8b import TRAINER_ID


class PublicCollectionTests(unittest.TestCase):
    def setUp(self):
        frontend_tests.FrontendReadTests.setUp(self)
        self.path = f"/v1/read/seasons/{SID}/trainers/{TRAINER_ID}/collection"
        pokemon = self.store.data["parsed_saves"][0]["payload"]["party"][0]["pokemon"]
        pokemon.update(nature="PRIVATE", ability="PRIVATE", ivs={"secret": 31},
                       evs={"secret": 252}, moves=[{"name": "Thunder", "pp": 5, "raw": "SECRET"}])
        self.store.data["parsed_saves"][0]["payload"]["boxes"] = [
            {"box_number": n, "slots": [{"slot_number": 1, "pokemon": pokemon}]} for n in (1, 8)
        ]
        self.store.data["season_player_stats"] = [{"season_player_id": PID, "revived_after_wipe": 2}]
        self.before = deepcopy(self.store.data)

    def get(self):
        return self.client.get(self.path, headers=self.headers)

    def test_public_allowlist_including_box8_without_lock(self):
        result = self.get()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["revived_after_wipe"], 2)
        self.assertEqual([p["location"] for p in result.json()["pokemon"]],
                         ["Equipo · 1", "Caja 1 · 1", "Caja 8 · 1"])
        for forbidden in ("SECRET", "PRIVATE", '"ivs"', '"evs"', '"ability"', '"nature"',
                          "pokemon_entity_id", "save_file", "source_hash", "parser_version"):
            self.assertNotIn(forbidden, result.text)
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertEqual(self.before, self.store.data)
        self.assertFalse({"team_locks", "pokemon_entities", "pokemon_observations"}
                         .intersection(c[0] for c in self.store.calls))
        self.assertEqual(len(self.store.calls), 6)

    def test_public_state_flags_are_combined_without_private_identity(self):
        entity_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        self.store.data["pokemon_observations"] = [
            dict(season_id=SID, trainer_id=TRAINER_ID, save_file_id=SAVE,
                 pokemon_entity_id=entity_ids[i], source="party" if i == 0 else "box",
                 box_number=0 if i == 0 else (1 if i == 1 else 8),
                 slot_number=1, outcome="MATCHED")
            for i in range(3)
        ]
        self.store.data["pokemon_entities"] = [
            dict(id=entity_id, season_id=SID, owner_trainer_id=TRAINER_ID,
                 identity_status="unambiguous")
            for entity_id in entity_ids
        ]
        self.store.public_pokemon_flags = lambda _sid, _ids: {
            entity_ids[0]: ["blindado", "revivido", "blindado"],
            entity_ids[1]: ["robado"],
            entity_ids[2]: [],
        }
        data = self.get().json()
        self.assertEqual(data["pokemon"][0]["pokemon"]["status_flags"],
                         ["blindado", "revivido"])
        self.assertEqual(data["pokemon"][1]["pokemon"]["status_flags"], ["robado"])
        self.assertEqual(data["pokemon"][2]["pokemon"]["status_flags"], [])
        for forbidden in ("pokemon_entity_id", "identity_status", "trainer_id"):
            self.assertNotIn(forbidden, self.get().text)

    def test_same_public_fields_for_self_admin_and_rival(self):
        expected = self.get().json()
        for tid, admin in [(str(uuid4()), False), (str(uuid4()), True), (TRAINER_ID, True)]:
            self.principals.trainer = replace(self.principals.trainer, id=tid, is_admin=admin)
            self.assertEqual(self.get().json(), expected)

    def test_jwt_and_enabled_required(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.principals.trainer = replace(self.principals.trainer, globally_enabled=False)
        self.assertEqual(self.get().status_code, 403)
        self.assertEqual(self.store.calls, [])

    def test_unknown_and_zero_are_distinct(self):
        self.store.data["season_player_stats"] = []
        self.store.data["season_players"][0]["current_save_file_id"] = None
        data = self.get().json()
        self.assertIsNone(data["revived_after_wipe"])
        self.assertEqual(data["status"], "no_current_save")
        self.assertEqual(data["pokemon"], [])
        self.store.data["season_player_stats"] = [{"season_player_id": PID, "revived_after_wipe": 0}]
        self.assertEqual(self.get().json()["revived_after_wipe"], 0)

    def test_scope_deleted_and_foreign_save_never_read(self):
        for field, value in [("season_id", str(uuid4())), ("trainer_id", str(uuid4())), ("deleted_at", "today")]:
            self.store.data = deepcopy(self.before)
            self.store.data["save_files"][0][field] = value
            self.store.calls.clear()
            self.assertEqual(self.get().json()["status"], "no_current_save")
            self.assertNotIn("parsed_saves", [c[0] for c in self.store.calls])
        self.store.data = deepcopy(self.before)
        self.store.data["season_players"] = []
        self.assertEqual(self.get().status_code, 404)
        self.store.data = deepcopy(self.before)
        self.store.data["seasons"][0]["status"] = "discarded"
        self.assertEqual(self.get().status_code, 404)

    def test_bad_provenance_or_counter_fails_closed(self):
        for key, value in [("save_record_id", str(uuid4())), ("trainer_id", str(uuid4())), ("source_hash", "SECRET")]:
            self.store.data = deepcopy(self.before)
            self.store.data["parsed_saves"][0]["payload"][key] = value
            result = self.get()
            self.assertEqual(result.status_code, 503)
            self.assertNotIn("SECRET", result.text)
        for value in (-1, True, "0"):
            self.store.data = deepcopy(self.before)
            self.store.data["season_player_stats"][0]["revived_after_wipe"] = value
            self.assertEqual(self.get().status_code, 503)

    def test_historical_lock_and_counter_unchanged(self):
        self.store.data["seasons"][0]["status"] = "archived"
        self.store.data["team_locks"] = [{"private_team_snapshot": "SECRET"}]
        before = deepcopy(self.store.data)
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual(self.store.data, before)

    def test_payload_not_ready_or_unsupported_remains_explicit(self):
        self.store.data["parsed_saves"][0]["status"] = "pending"
        self.assertEqual(self.get().json()["status"], "not_ready")
        self.store.data["parsed_saves"][0]["status"] = "parsed"
        self.store.data["parsed_saves"][0]["schema_version"] = 999
        self.assertEqual(self.get().json()["status"], "unsupported_payload")

    def test_partial_legacy_payload_does_not_claim_empty_boxes(self):
        for field in ("party", "boxes"):
            self.store.data = deepcopy(self.before)
            del self.store.data["parsed_saves"][0]["payload"][field]
            data = self.get().json()
            self.assertEqual(data["status"], "unsupported_payload")
            self.assertEqual(data["pokemon"], [])


if __name__ == "__main__":
    unittest.main()
