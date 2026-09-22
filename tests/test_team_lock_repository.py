from copy import deepcopy
from dataclasses import fields
import json
from pathlib import Path
import unittest

import httpx
from postgrest import SyncPostgrestClient

from app.application.team_locks import lock_team_v2
from app.domain.services.team_locks import validate_team_lock
from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules
from app.repositories.errors import ConflictError, NotFoundError, PermissionDeniedError, PersistenceError
from app.repositories.supabase.team_locks import RPC_NAME, SupabaseTeamLockRepository
from team_lock_fixtures import MATCHDAY, OTHER, SAVE, SEASON, MemoryAtomicTeamLocks
from test_api_phase8b import TRAINER_ID


class TeamLockRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.memory = MemoryAtomicTeamLocks()
        self.receipt = lock_team_v2(self.memory, season_id=SEASON, matchday_id=MATCHDAY, trainer_id=TRAINER_ID, save_file_id=SAVE)
        self.mutation = self.memory.mutations[0]
        self.requests = []
        self.rpc_status = 200
        self.rpc_body = [{f.name: deepcopy(getattr(self.receipt, f.name)) for f in fields(self.receipt)}]
        source = self.memory.source
        self.rows = dict(seasons=source.season, matchdays=source.matchday, season_players=source.participant,
                         save_files=source.save, parsed_saves=source.parsed)

        def respond(request):
            self.requests.append(request)
            if request.url.path.endswith("/rpc/" + RPC_NAME):
                return httpx.Response(self.rpc_status, json=self.rpc_body)
            row = self.rows.get(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json=[row] if row else [])

        client = SyncPostgrestClient("https://example.invalid/rest/v1")
        client.session = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(client.session.close)
        self.repo = SupabaseTeamLockRepository(client)

    def test_real_builder_sends_one_rpc_with_complete_payload(self):
        self.assertEqual(self.repo.upsert_with_activity(self.mutation), self.receipt)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertTrue(request.url.path.endswith("/rpc/api_upsert_team_lock"))
        payload = json.loads(request.content)
        self.assertEqual(payload, {"p_" + f.name: getattr(self.mutation, f.name) for f in fields(self.mutation)})
        self.assertEqual(payload["p_save_sha256"], "a" * 64)
        self.assertNotIn("p_is_late", payload)
        self.assertNotIn("p_deadline_at", payload)

    def test_source_reads_are_bounded_and_owner_season_scoped(self):
        source = self.repo.load_source(season_id=SEASON, matchday_id=MATCHDAY, trainer_id=TRAINER_ID, save_file_id=SAVE)
        self.assertEqual(source, self.memory.source)
        self.assertEqual(len(self.requests), 5)
        by_table = {r.url.path.rsplit("/", 1)[-1]: dict(r.url.params) for r in self.requests}
        for table in by_table:
            self.assertEqual(by_table[table]["limit"], "1")
        self.assertEqual(by_table["save_files"]["trainer_id"], "eq." + TRAINER_ID)
        self.assertEqual(by_table["save_files"]["season_id"], "eq." + SEASON)
        self.assertEqual(by_table["matchdays"]["season_id"], "eq." + SEASON)
        self.assertEqual(by_table["parsed_saves"]["parser_version"], "eq.fixture-v1")
        self.assertEqual(by_table["parsed_saves"]["save_file_id"], "eq." + SAVE)

    def test_missing_save_does_not_query_parsed_table(self):
        self.rows["save_files"] = None
        source = self.repo.load_source(season_id=SEASON, matchday_id=MATCHDAY, trainer_id=TRAINER_ID, save_file_id=SAVE)
        self.assertIsNone(source.save)
        self.assertIsNone(source.parsed)
        self.assertEqual(len(self.requests), 4)

    def test_rpc_errors_are_typed_without_sql_detail(self):
        for code, error in (("PT403", PermissionDeniedError), ("PT404", NotFoundError),
                            ("PT409", ConflictError), ("23503", PersistenceError), ("XX000", PersistenceError)):
            with self.subTest(code=code):
                self.rpc_status = 400
                self.rpc_body = {"code": code, "message": "dummy-sensitive-SQL", "hint": None, "details": None}
                with self.assertRaises(error) as caught:
                    self.repo.upsert_with_activity(self.mutation)
                self.assertNotIn("dummy-sensitive", str(caught.exception))
                self.assertIsNotNone(caught.exception.__cause__)

    def test_no_receipt_multiple_rows_and_wrong_owner_fail_closed(self):
        original = deepcopy(self.rpc_body)
        for response in ([], original * 2, [{**original[0], "trainer_id": OTHER}], [{}]):
            with self.subTest(response=response):
                self.rpc_body = response
                with self.assertRaises(PersistenceError):
                    self.repo.upsert_with_activity(self.mutation)

    def test_receipt_does_not_alias_backend_json(self):
        record = self.repo.upsert_with_activity(self.mutation)
        self.rpc_body[0]["private_team_snapshot"][0]["ivs"]["hp"] = 0
        self.assertEqual(record.private_team_snapshot[0]["ivs"]["hp"], 31)

    def test_exact_six_rule_in_shared_service(self):
        for required in (True, False):
            for size in range(9):
                with self.subTest(required=required, size=size):
                    decision = validate_team_lock(
                        trainer_id=TRAINER_ID, participant_ids=(TRAINER_ID,), matchday_number=1,
                        team=(PublicPokemon(species="Milotic"),) * size, rules=SeasonRules(team_lock_required=required),
                    )
                    self.assertEqual(decision.allowed, size == 6)

    def test_v2_application_and_repository_do_not_import_legacy_or_transport(self):
        for name in ("app/application/team_locks.py", "app/repositories/supabase/team_locks.py"):
            source = Path(name).read_text(encoding="utf-8").lower()
            for forbidden in ("from storage", "import streamlit", "fastapi", "conex_pkhex", "discord_notify"):
                self.assertNotIn(forbidden, source)
