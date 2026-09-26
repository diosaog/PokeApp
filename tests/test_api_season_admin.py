import unittest
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.season_admin_models import ConfigVersionBody, InitialDivisionsBody
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import REJECTIONS, RPCS, SeasonAdminRejected, SupabaseSeasonAdminRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


SID = str(uuid4())


def config_body():
    return dict(name="Initial", effective_from_matchday=1, total_matchdays=4,
        division_sizes={"A": 2, "B": 2}, movement_count=1,
        scoring={str(i): 5-i for i in range(1, 5)}, coin_rewards={str(i): 10-i for i in range(1, 5)},
        rules=dict(team_lock_required=True, last_b_gets_steal=True),
        expected_config_revision=0, expected_roster_revision=4)


class FakeRepository:
    def __init__(self):
        self.calls = []
        self.failure = None
        self.response = dict(operation_id=str(uuid4()), resource_id=SID, season_id=SID,
            event_id=str(uuid4()), replayed=False, state="draft", setup_revision=0, roster_revision=0, config_revision=0)

    def execute(self, operation, request):
        self.calls.append((operation, request))
        if self.failure:
            raise self.failure
        return self.response


class SeasonAdminApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.principals = FakePrincipalRepository()
        self.tokens = FakeTokenVerifier()
        self.client = TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals, season_admin_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer validated", "Idempotency-Key": "admin-key"}

    def post(self, body=None, headers=None, path="/v1/admin/seasons"):
        return self.client.post(path, json=body or {"name": "Initial"}, headers=self.headers if headers is None else headers)

    def test_missing_bearer(self):
        self.assertEqual(self.post(headers={"Idempotency-Key": "x"}).status_code, 401)
        self.assertFalse(self.repo.calls)

    def test_invalid_bearer(self):
        self.tokens.fail = InvalidSessionError()
        self.assertEqual(self.post().status_code, 401)

    def test_disabled_admin(self):
        self.principals.trainer = replace(self.principals.trainer, globally_enabled=False)
        self.assertEqual(self.post().status_code, 403)

    def test_non_admin_named_antonio(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.assertEqual(self.post().json()["detail"]["code"], "ADMIN_REQUIRED")
        self.assertFalse(self.repo.calls)

    def test_admin_no_participation_or_name_required(self):
        self.principals.trainer = replace(self.principals.trainer, display_name="Unrelated", slug="different")
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.repo.calls[0][1]["actor_trainer_id"], TRAINER_ID)

    def test_no_body_authority(self):
        for field in ("actor_trainer_id", "is_admin", "status", "auth_user_id", "current_matchday_id"):
            with self.subTest(field=field):
                self.assertEqual(self.post({"name": "x", field: "forged"}).status_code, 422)

    def test_key_required(self):
        self.assertEqual(self.post(headers={"Authorization": "Bearer validated"}).status_code, 422)

    def test_bad_keys(self):
        for value in ("", "has spaces", "x"*129):
            self.assertEqual(self.post(headers={**self.headers, "Idempotency-Key": value}).status_code, 422)

    def test_name_validation(self):
        for value in ("", "  ", "x"*121, 123, True):
            self.assertEqual(self.post({"name": value}).status_code, 422)

    def test_name_canonicalization(self):
        self.post({"name": "  Initial  "})
        self.assertEqual(self.repo.calls[0][1]["body"], {"name": "Initial"})

    def test_rename_typed_revision_and_durable_retry_key(self):
        response = self.client.put(f"/v1/admin/seasons/{SID}/name", json={"name": "New", "expected_revision": 4}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repo.calls[0][1]["idempotency_key"], "revision:4")
        for value in (-1, "4", True, 1.2):
            self.assertEqual(self.client.put(f"/v1/admin/seasons/{SID}/name", json={"name": "New", "expected_revision": value}, headers=self.headers).status_code, 422)

    def test_known_rejections_are_stable(self):
        for code, status in REJECTIONS.items():
            with self.subTest(code=code):
                self.repo.failure = SeasonAdminRejected(code.upper(), status)
                response = self.post()
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["code"], code.upper())

    def test_persistence_sanitized(self):
        self.repo.failure = PersistenceError("SQL and secret details")
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret details", response.text)

    def test_response_private_fields_fail_closed(self):
        self.repo.response["auth_user_id"] = "secret"
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)

    def test_response_scope_verified(self):
        self.repo.response["season_id"] = str(uuid4())
        response = self.client.put(f"/v1/admin/seasons/{SID}/name", json={"name": "x", "expected_revision": 0}, headers=self.headers)
        self.assertEqual(response.status_code, 503)

    def test_config_is_explicit_two_divisions(self):
        body = config_body()
        ConfigVersionBody.model_validate(body)
        for sizes in ({"A": 4}, {"A": 2, "B": 2, "C": 1}, {"A": 0, "B": 4}, {"A": True, "B": 3}):
            with self.assertRaises(ValueError):
                ConfigVersionBody.model_validate({**body, "division_sizes": sizes})

    def test_config_rules_allowlist(self):
        body = config_body()
        for rules in ({"arbitrary": True}, {**body["rules"], "cup_is_separate": True}, {**body["rules"], "team_lock_required": "true"}):
            with self.assertRaises(ValueError):
                ConfigVersionBody.model_validate({**body, "rules": rules})

    def test_reward_shapes(self):
        for scoring in ({"0": 1}, {"1": -1}, {"1": True}, {"1": "2"}, {"1": 0.5}):
            with self.assertRaises(ValueError):
                ConfigVersionBody.model_validate({**config_body(), "scoring": scoring})

    def test_assignments_semantic_canonicalization(self):
        ids = sorted([str(uuid4()), str(uuid4())])
        body = InitialDivisionsBody.model_validate(dict(config_version_id=SID, assignments={"A": ids[::-1], "B": [str(uuid4())]},
            expected_roster_revision=4, expected_setup_revision=5))
        self.assertEqual(body.model_dump(mode="json")["assignments"]["A"], ids)

    def test_all_admin_routes_have_auth_dependency(self):
        schema = self.client.get("/openapi.json").json()
        routes = [(path, method) for path, ops in schema["paths"].items() if path.startswith("/v1/admin") for method in ops]
        self.assertEqual(len(routes), 31)
        for path, method in routes:
            self.assertIn("security", schema["paths"][path][method])

    def test_explicit_lifecycle_without_generic_season_mutation(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for suffix in ("finish", "archive", "discard"):
            self.assertIn(f"/v1/admin/seasons/{{season_id}}/{suffix}", paths)
        for suffix in ("reopen", "retire", "close"):
            self.assertNotIn(f"/v1/admin/seasons/{{season_id}}/{suffix}", paths)


class SeasonAdminAdapterTests(unittest.TestCase):
    def test_staging_transport_distinguishes_schema_422_from_business_error(self):
        from tools.validate_supabase_v2_season_admin import ApiTransport
        response=SimpleNamespace(status_code=422,json=lambda:{'detail':[{'type':'missing','loc':['body','name']}]})
        client=SimpleNamespace(request=lambda *a,**k:response)
        transport=ApiTransport(lambda:client,{TRAINER_ID:'synthetic-test-token'})
        with self.assertRaises(SeasonAdminRejected) as exc:
            transport.execute('create',{'actor_trainer_id':TRAINER_ID,'body':{}})
        self.assertEqual((exc.exception.code,exc.exception.status),('INVALID_REQUEST',422))

    def test_each_operation_has_separate_rpc(self):
        self.assertEqual(len(set(RPCS.values())), 10)
        calls = []
        client = SimpleNamespace(rpc=lambda name, args: (calls.append((name, args)) or SimpleNamespace(execute=lambda: SimpleNamespace(data={}))))
        repo = SupabaseSeasonAdminRepository(client)
        for op, name in RPCS.items():
            repo.execute(op, {"actor_trainer_id": TRAINER_ID})
            self.assertEqual(calls[-1], (name, {"p_request": {"actor_trainer_id": TRAINER_ID}}))

    def test_allowlisted_postgres_errors_only(self):
        def fail():
            raise SimpleSqlError("PT409", "stale_revision")
        repo = SupabaseSeasonAdminRepository(SimpleNamespace(rpc=lambda *_: SimpleNamespace(execute=fail)))
        with self.assertRaises(SeasonAdminRejected) as exc:
            repo.execute("create", {})
        self.assertEqual(exc.exception.code, "STALE_REVISION")

    def test_unexpected_sql_error_is_sanitized(self):
        def fail():
            raise SimpleSqlError("42501", "private details")
        repo = SupabaseSeasonAdminRepository(SimpleNamespace(rpc=lambda *_: SimpleNamespace(execute=fail)))
        with self.assertRaises(PersistenceError) as exc:
            repo.execute("create", {})
        self.assertNotIn("private details", str(exc.exception))


class SimpleSqlError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
