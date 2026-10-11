"""Public lock identity batching through the real PostgREST query builder."""

from copy import deepcopy
import unittest
from uuid import uuid4

import httpx
from postgrest import SyncPostgrestClient

from app.repositories.errors import PersistenceError
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository


class InventoryBatchTests(unittest.TestCase):
    def setUp(self):
        self.season = str(uuid4())
        self.locks, self.observations, self.entities = [], [], []
        for _ in range(6):
            trainer, save, entity = (str(uuid4()) for _ in range(3))
            self.locks.append(dict(trainer_id=trainer, save_file_id=save))
            self.observations.append(dict(
                trainer_id=trainer, save_file_id=save, pokemon_entity_id=entity,
                source="party", box_number=0, slot_number=1, outcome="MATCHED",
            ))
            self.entities.append(dict(id=entity, owner_trainer_id=trainer,
                                      identity_status="unambiguous"))
        self.requests = []
        self.failure = None
        self.client = SyncPostgrestClient("https://example.invalid/rest/v1")
        self.client.session = httpx.Client(transport=httpx.MockTransport(self.respond))
        self.addCleanup(self.client.session.close)
        self.repo = SupabaseFrontendReadRepository(self.client)

    def respond(self, request):
        self.requests.append(request)
        if self.failure:
            raise self.failure
        rows = self.observations if request.url.path.endswith("pokemon_observations") else self.entities
        return httpx.Response(200, json=rows)

    def test_same_two_scoped_reads_for_one_and_six_rivals(self):
        for size in (1, 6):
            self.requests.clear()
            result = self.repo.observed_entities_for_locks(self.season, self.locks[:size])
            self.assertEqual(len(result), size)
            self.assertEqual(len(self.requests), 2)
            observations, entities = self.requests
            for request in self.requests:
                self.assertEqual(request.method, "GET")
                self.assertEqual(request.url.params["season_id"], "eq." + self.season)
                self.assertEqual(request.url.params["limit"], "501")
                self.assertNotIn("evidence", request.url.params["select"])
            self.assertEqual(observations.url.params["source"], "eq.party")
            self.assertEqual(observations.url.params["box_number"], "eq.0")
            self.assertEqual(observations.url.params["slot_number"], "in.(1,2,3,4,5,6)")
            self.assertIn(self.locks[0]["save_file_id"], observations.url.params["save_file_id"])
            self.assertEqual(entities.url.params["identity_status"], "eq.unambiguous")
            self.assertEqual(entities.url.params["select"], "id,owner_trainer_id,identity_status")

    def test_no_locks_or_no_candidates_avoids_unneeded_queries(self):
        self.assertEqual(self.repo.observed_entities_for_locks(self.season, []), {})
        self.assertEqual(self.requests, [])
        self.observations = []
        self.assertEqual(self.repo.observed_entities_for_locks(self.season, self.locks), {})
        self.assertEqual(len(self.requests), 1)

    def test_wrong_save_cross_pair_foreign_owner_and_ambiguous_are_excluded(self):
        self.observations[0]["save_file_id"] = str(uuid4())
        self.observations[1]["save_file_id"] = self.locks[2]["save_file_id"]
        self.entities[2]["owner_trainer_id"] = self.locks[3]["trainer_id"]
        self.entities[3]["identity_status"] = "ambiguous"
        self.observations[4]["outcome"] = "AMBIGUOUS"
        result = self.repo.observed_entities_for_locks(self.season, self.locks)
        self.assertEqual(result, {
            (self.locks[5]["trainer_id"], "party", 0, 1): self.entities[5]["id"]
        })

    def test_malformed_duplicate_and_overflow_fail_closed(self):
        original = deepcopy(self.observations)
        cases = [[None], original * 84,
                 original + [original[0]],
                 [dict(original[0], slot_number=True)],
                 [dict(original[0], slot_number=7)],
                 [dict(original[0], source="box")],
                 [dict(original[0], pokemon_entity_id=None)]]
        for rows in cases:
            with self.subTest(rows_type=type(rows).__name__), self.assertRaises(PersistenceError):
                self.observations = rows
                self.repo.observed_entities_for_locks(self.season, self.locks)
        self.observations = original
        self.entities *= 84
        with self.assertRaises(PersistenceError):
            self.repo.observed_entities_for_locks(self.season, self.locks)

    def test_conflicting_lock_save_fails_before_transport(self):
        self.locks.append(dict(self.locks[0], save_file_id=str(uuid4())))
        with self.assertRaises(PersistenceError):
            self.repo.observed_entities_for_locks(self.season, self.locks)
        self.assertEqual(self.requests, [])

    def test_read_error_retry_is_bounded_and_sanitized(self):
        self.failure = httpx.ReadError("SECRET response")
        with self.assertLogs("app.repositories.supabase.frontend_reads") as logs:
            with self.assertRaises(PersistenceError):
                self.repo.observed_entities_for_locks(self.season, self.locks)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[0].url, self.requests[1].url)
        self.assertNotIn("SECRET", str(logs.output))

