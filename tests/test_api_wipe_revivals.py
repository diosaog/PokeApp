"""Owned counter identity, strict transport and explicit-replay boundaries."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.repositories.supabase.wipe_revivals import (
    ERRORS,
    SupabaseWipeRevivalsRepository,
)
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID = str(uuid4())


class FakeWipeRepository:
    def __init__(self):
        self.calls = []
        self.failure = None
        self.response = dict(
            season_id=SID,
            revived_after_wipe=1,
            revision=2,
            editable=True,
            blocking_reason=None,
            replayed=False,
        )

    def execute(self, operation, request):
        self.calls.append((operation, request))
        if self.failure:
            raise self.failure
        return self.response


class WipeRevivalsApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeWipeRepository()
        self.principals, self.tokens = FakePrincipalRepository(), FakeTokenVerifier()
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=self.tokens,
                    principal_repository=self.principals,
                    wipe_revivals_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.path = f"/v1/seasons/{SID}/wipe-revivals"
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "wipe-key",
        }
        self.body = dict(revived_after_wipe=1, expected_revision=1)

    def put(self, body=None, headers=None):
        return self.client.put(
            self.path,
            headers=self.headers if headers is None else headers,
            json=self.body if body is None else body,
        )

    def test_anonymous_invalid_unmapped_and_disabled_before_repository(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.assertEqual(self.put(headers={}).status_code, 401)
        self.tokens.fail = InvalidSessionError()
        self.assertEqual(self.put().status_code, 401)
        self.tokens.fail = None
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.put().status_code, 403)
        self.principals.trainer = None
        self.assertEqual(self.put().status_code, 401)
        self.assertFalse(self.repo.calls)

    def test_non_admin_read_and_update_use_only_verified_identity(self):
        response = self.client.get(self.path, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(
            self.repo.calls[-1],
            ("state", dict(actor_trainer_id=TRAINER_ID, season_id=SID)),
        )
        self.assertEqual(self.put().status_code, 200)
        self.assertEqual(
            self.repo.calls[-1],
            (
                "set",
                dict(
                    actor_trainer_id=TRAINER_ID,
                    season_id=SID,
                    body=self.body,
                    idempotency_key="wipe-key",
                ),
            ),
        )

    def test_readonly_own_inactive_season_state_is_typed(self):
        for reason in (
            "participant_inactive",
            "season_inactive",
            "league_closed",
            "membership_ineligible",
        ):
            self.repo.response.update(editable=False, blocking_reason=reason)
            response = self.client.get(self.path, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["editable"])
            self.assertEqual(response.json()["blocking_reason"], reason)

    def test_negative_fraction_string_boolean_and_overflow_rejected(self):
        for field, bad in (
            ("revived_after_wipe", (-1, 0.4, "1", True, None, 2147483648)),
            ("expected_revision", (-1, 1.5, "1", True, None, 9007199254740992)),
        ):
            for value in bad:
                with self.subTest(field=field, value=value):
                    self.assertEqual(
                        self.put(dict(self.body, **{field: value})).status_code, 422
                    )
        self.assertFalse(self.repo.calls)
        self.repo.response.update(
            revived_after_wipe=2147483647, revision=9007199254740991
        )
        self.assertEqual(
            self.put(
                dict(revived_after_wipe=2147483647, expected_revision=9007199254740991)
            ).status_code,
            200,
        )
        self.repo.response.update(revived_after_wipe=0, revision=0)
        self.assertEqual(
            self.put(dict(revived_after_wipe=0, expected_revision=0)).status_code, 200
        )

    def test_spoofed_identity_and_generic_stats_are_not_commands(self):
        for name in (
            "trainer_id",
            "participant_id",
            "season_player_id",
            "actor_trainer_id",
            "season_id",
            "is_admin",
            "dead_count",
            "metadata",
            "wipe_revision",
            "operation",
        ):
            self.assertEqual(
                self.put(dict(self.body, **{name: TRAINER_ID})).status_code, 422
            )
        self.assertEqual(
            self.client.put(
                self.path + "/" + str(uuid4()), json=self.body, headers=self.headers
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                self.path, json=self.body, headers=self.headers
            ).status_code,
            405,
        )
        self.assertFalse(self.repo.calls)

    def test_required_key_and_uuid_scope(self):
        self.assertEqual(
            self.put(headers={"Authorization": "Bearer validated"}).status_code, 422
        )
        for key in ("", "invalid key", "x" * 129):
            self.assertEqual(
                self.put(
                    headers=dict(self.headers, **{"Idempotency-Key": key})
                ).status_code,
                422,
            )
        self.path = "/v1/seasons/not-a-uuid/wipe-revivals"
        self.assertEqual(self.put().status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_backend_rejections_are_typed(self):
        for code, status in ERRORS.items():
            self.repo.failure = SeasonAdminRejected(code.upper(), status)
            response = self.put()
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["detail"]["code"], code.upper())

    def test_response_scope_shape_and_privacy_fail_closed(self):
        original = dict(self.repo.response)
        for change in (
            dict(season_id=str(uuid4())),
            dict(revived_after_wipe=-1),
            dict(revision=9007199254740992),
            dict(revision=9),
            dict(revived_after_wipe=2),
            dict(editable=True, blocking_reason="league_closed"),
            dict(editable=False, blocking_reason=None),
            dict(editable=False, blocking_reason="league_closed"),
            dict(editable="true"),
            dict(private_team_snapshot="PRIVATE"),
            dict(trainer_id=TRAINER_ID),
        ):
            self.repo.response = dict(original, **change)
            response = self.put()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("PRIVATE", response.text)

    def test_explicit_replay_retains_body_key_and_is_not_a_new_read(self):
        self.repo.response["replayed"] = True
        for _ in range(2):
            response = self.put()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["replayed"])
        self.assertEqual(self.repo.calls[0], self.repo.calls[1])
        self.assertEqual(
            self.client.get(self.path, headers=self.headers).status_code, 503
        )

    def test_unknown_outcome_sanitized_without_retry(self):
        self.repo.failure = PersistenceError("PRIVATE DATABASE CONNECTION")
        response = self.put()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE", response.text)
        self.assertEqual(len(self.repo.calls), 1)


class WipeRevivalsAdapterTests(unittest.TestCase):
    def test_rpc_envelope_for_read_and_set(self):
        client = Mock()
        client.rpc.return_value.execute.return_value.data = (
            FakeWipeRepository().response
        )
        repo = SupabaseWipeRevivalsRepository(client)
        for op in ("state", "set"):
            request = dict(actor_trainer_id=TRAINER_ID, season_id=SID)
            repo.execute(op, request)
            client.rpc.assert_called_with(
                "api_participant_wipe_revivals",
                {"p_request": dict(operation=op, request=request)},
            )

    def test_error_allowlist_needs_exact_sqlstate(self):
        for code, status in ERRORS.items():
            client = Mock()
            error = Exception("PRIVATE")
            error.message, error.code = code, "PT" + str(status)
            client.rpc.return_value.execute.side_effect = error
            with self.assertRaises(SeasonAdminRejected):
                SupabaseWipeRevivalsRepository(client).execute("set", {})
            error.code = "XX000"
            with self.assertRaises(PersistenceError) as caught:
                SupabaseWipeRevivalsRepository(client).execute("set", {})
            self.assertNotIsInstance(caught.exception, SeasonAdminRejected)

    def test_transport_failure_does_not_retry_either_operation(self):
        import httpx

        for operation in ("state", "set"):
            client = Mock()
            client.rpc.return_value.execute.side_effect = httpx.ReadError("PRIVATE")
            with self.assertRaises(PersistenceError):
                SupabaseWipeRevivalsRepository(client).execute(operation, {})
            self.assertEqual(client.rpc.call_count, 1)

    def test_malformed_transport_response(self):
        for value in (None, [], True, "raw"):
            client = Mock()
            client.rpc.return_value.execute.return_value = SimpleNamespace(data=value)
            with self.assertRaises(PersistenceError):
                SupabaseWipeRevivalsRepository(client).execute("state", {})
