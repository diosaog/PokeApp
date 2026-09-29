"""GENERAL API boundary; authoritative SQL ordering/arithmetic tested on real PG."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from postgrest import SyncPostgrestClient

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.errors import PersistenceError
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID = str(uuid4())


def general():
    return dict(
        season=dict(id=SID, name="Liga", status="active"),
        days=[],
        rows=[
            dict(
                season_player_id=str(uuid4()),
                trainer_id=TRAINER_ID,
                display_name="Anto",
                status="retired",
                total_points="-9007199254740993.123456789",
                points_source_matchday_id=None,
                coin_balance="-4294967294",
                dead_count=None,
                dead_count_source="unknown",
                dead_count_observed_at=None,
                payload="SECRET",
                auth_user_id="SECRET",
            )
        ],
        metadata="SECRET",
    )


class Store:
    def __init__(self):
        self.result = general()
        self.calls = []

    def league_general(self, sid):
        self.calls.append(sid)
        if isinstance(self.result, Exception):
            raise self.result
        return deepcopy(self.result)


class LeagueGeneralTests(unittest.TestCase):
    def setUp(self):
        self.store, self.principals = Store(), FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    frontend_read_repository=self.store,
                ),
                config=APIConfig(),
            )
        )
        self.addCleanup(self.client.close)
        self.url = f"/v1/read/seasons/{SID}/league"
        self.headers = {"Authorization": "Bearer validated"}

    def get(self):
        return self.client.get(self.url, headers=self.headers)

    def test_enabled_jwt_guard_before_repository(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.get().status_code, 403)
        self.assertEqual(self.store.calls, [])

    def test_whitelist_exact_amounts_and_inactive_history(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("SECRET", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        row = response.json()["rows"][0]
        self.assertEqual(row["total_points"], "-9007199254740993.123456789")
        self.assertEqual(row["coin_balance"], "-4294967294")
        self.assertEqual(row["status"], "retired")
        self.assertIsNone(row["dead_count"])
        self.assertNotIn("champion", row)
        self.assertNotIn("rank", row)

    def test_single_rpc_for_all_players_preserves_server_order(self):
        rows = self.store.result["rows"]
        rows.extend(
            dict(rows[0], season_player_id=str(uuid4()), display_name=name)
            for name in ("Zeta", "Alfa")
        )
        self.assertEqual(
            [r["display_name"] for r in self.get().json()["rows"]],
            ["Anto", "Zeta", "Alfa"],
        )
        self.assertEqual(self.store.calls, [SID])

    def test_unknown_season_and_sanitized_failures(self):
        self.store.result = None
        self.assertEqual(self.get().status_code, 404)
        for value in (
            PersistenceError("SECRET"),
            [],
            dict(
                general(), season=dict(id=str(uuid4()), name="Other", status="active")
            ),
            dict(general(), season=dict(id=SID, name="Gone", status="discarded")),
        ):
            with self.subTest(value=type(value)):
                self.store.result = value
                response = self.get()
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("SECRET", response.text)

    def test_capacity_and_nonfinite_points_fail_closed(self):
        self.store.result["rows"] *= 501
        self.assertEqual(self.get().status_code, 503)
        for value in ("NaN", "Infinity"):
            self.store.result = general()
            self.store.result["rows"][0]["total_points"] = value
            self.assertEqual(self.get().status_code, 503)

    def test_postgrest_rpc_transport_and_errors(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=general())

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client = SyncPostgrestClient(
                "https://example.invalid/rest/v1", http_client=http
            )
            repo = SupabaseFrontendReadRepository(client)
            self.assertEqual(
                repo.league_general(SID)["rows"][0]["coin_balance"], "-4294967294"
            )
            self.assertEqual(calls[0].url.path, "/rest/v1/rpc/league_general_read")
            self.assertEqual(json.loads(calls[0].content), {"p_season_id": SID})
        for payload in ([], "SECRET"):
            with httpx.Client(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(200, json=payload)
                )
            ) as http:
                client = SyncPostgrestClient(
                    "https://example.invalid/rest/v1", http_client=http
                )
                with self.assertRaises(PersistenceError):
                    SupabaseFrontendReadRepository(client).league_general(SID)
