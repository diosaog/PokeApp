"""E authority, typed boundaries, privacy and replay before planning."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.initial_assignment import (
    InitialAssignmentRejected,
    initial_assignment_review,
)
from app.application.frontend_reads import FrontendReads
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID
from test_api_season_admin import FakeRepository
from test_initial_assignment import SID, body, context, decide


def receipt():
    return dict(
        operation_id=str(uuid4()),
        resource_id=SID,
        season_id=SID,
        event_id=str(uuid4()),
        replayed=False,
        state="active",
        setup_revision=6,
        roster_revision=4,
        config_revision=1,
    )


class InitialAssignmentApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.repo.response = receipt()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    season_admin_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.path = f"/v1/admin/seasons/{SID}/initial-assignment/finalize"
        self.read = f"/v1/seasons/{SID}/initial-assignment"
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "initial-key",
        }

    def post(self, command=None, headers=None):
        return self.client.post(
            self.path,
            json=command if command is not None else body(context()),
            headers=self.headers if headers is None else headers,
        )

    def test_read_requires_enabled_verified_identity(self):
        self.repo.response = initial_assignment_review(context())
        self.assertEqual(self.client.get(self.read).status_code, 401)
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(
            self.client.get(self.read, headers=self.headers).status_code, 403
        )
        self.assertFalse(self.repo.calls)

    def test_non_admin_can_read_but_cannot_finalize_or_resolve(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.repo.response = initial_assignment_review(context())
        self.assertEqual(
            self.client.get(self.read, headers=self.headers).status_code, 200
        )
        self.assertEqual(self.repo.calls[-1][0], "initial_state")
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(len(self.repo.calls), 1)

    def test_finalize_uses_verified_actor_and_exact_body(self):
        command = body(context())
        self.assertEqual(self.post(command).status_code, 200)
        operation, sent = self.repo.calls[0]
        self.assertEqual(operation, "initial_finalize")
        self.assertEqual(
            sent,
            dict(
                actor_trainer_id=TRAINER_ID,
                season_id=SID,
                body=command,
                idempotency_key="initial-key",
            ),
        )

    def test_authority_manual_progress_and_injected_plan_rejected(self):
        for key in (
            "actor_trainer_id",
            "is_admin",
            "observed_badges",
            "cap_reached",
            "adjusted_deaths",
            "plan",
            "assignments",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self.post({**body(context()), key: 2}).status_code, 422
                )
        self.assertFalse(self.repo.calls)

    def test_typed_revision_digest_key_and_reason(self):
        for key, value in (
            ("expected_setup_revision", True),
            ("expected_roster_revision", 1.5),
            ("input_hash", "bad"),
        ):
            self.assertEqual(
                self.post({**body(context()), key: value}).status_code, 422
            )
        self.assertEqual(
            self.post(headers={"Authorization": "Bearer validated"}).status_code, 422
        )
        ctx = context((0, 1, 1, 3))
        command = decide(
            ctx, initial_assignment_review(ctx)["boundary_tie"]["player_ids"]
        )
        command["tie_resolution"]["orders"][0]["reason"] = " "
        self.assertEqual(self.post(command).status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_null_resolution_omitted_and_human_member_order_preserved(self):
        self.assertEqual(
            self.post({**body(context()), "tie_resolution": None}).status_code, 200
        )
        self.assertNotIn("tie_resolution", self.repo.calls[-1][1]["body"])
        ctx = context((0, 1, 1, 3))
        ids = list(
            reversed(initial_assignment_review(ctx)["boundary_tie"]["player_ids"])
        )
        command = decide(ctx, ids)
        self.assertEqual(self.post(command).status_code, 200)
        self.assertEqual(self.repo.calls[-1][1]["body"], command)

    def test_whitelisted_conflicts_do_not_expose_internal_evidence(self):
        for code in (
            "INITIAL_ASSIGNMENT_REVIEW_STALE",
            "INITIAL_ASSIGNMENT_NOT_READY",
            "INITIAL_BOUNDARY_TIE_UNRESOLVED",
        ):
            self.repo.failure = InitialAssignmentRejected(code)
            response = self.post()
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["detail"]["code"], code)
        self.repo.failure = InitialAssignmentRejected("SECRET SQL")
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.text)

    def test_cross_season_malformed_or_private_response_fails_closed(self):
        review = initial_assignment_review(context())
        for changed in (
            {"season_id": str(uuid4())},
            {"players": [{"raw": "SECRET"}]},
            {"blocking_reasons": ["SECRET"]},
        ):
            self.repo.response = {**review, **changed}
            response = self.client.get(self.read, headers=self.headers)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("SECRET", response.text)

    def test_backend_failures_are_sanitized_and_private_responses_not_cached(self):
        self.repo.failure = PersistenceError("SECRET DSN")
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.text)
        self.assertEqual(response.headers["Cache-Control"], "no-store")


class InitialAssignmentAdapterTests(unittest.TestCase):
    def client(self, *results):
        calls, values = [], iter(results)

        def rpc(name, args):
            calls.append((name, deepcopy(args)))
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=next(values)))

        return SimpleNamespace(rpc=rpc), calls

    def test_replay_receipt_short_circuits_changed_or_assigned_inputs(self):
        saved = {**receipt(), "replayed": True}
        client, calls = self.client(dict(receipt=saved))
        with patch(
            "app.repositories.supabase.season_admin.plan_initial_assignment"
        ) as planner:
            result = SupabaseSeasonAdminRepository(client).execute(
                "initial_finalize", {"body": body(context())}
            )
        self.assertEqual(result, saved)
        planner.assert_not_called()
        self.assertEqual(len(calls), 1)

    def test_valid_plan_commits_same_body_and_database_fingerprint(self):
        ctx = context()
        client, calls = self.client(ctx, receipt())
        request = dict(
            actor_trainer_id=TRAINER_ID,
            season_id=SID,
            body=body(ctx),
            idempotency_key="same",
        )
        SupabaseSeasonAdminRepository(client).execute("initial_finalize", request)
        self.assertEqual(
            [c[0] for c in calls],
            ["initial_assignment_context", "api_admin_finalize_initial_assignment"],
        )
        envelope = calls[-1][1]["p_request"]
        self.assertEqual(envelope["request"], request)
        self.assertEqual(envelope["input_hash"], ctx["input_hash"])
        self.assertEqual(set(envelope["plan"]), {"assignments", "audit"})

    def test_stale_review_stops_before_durable_rpc(self):
        ctx = context()
        client, calls = self.client(ctx)
        with self.assertRaises(InitialAssignmentRejected):
            SupabaseSeasonAdminRepository(client).execute(
                "initial_finalize", {"body": {**body(ctx), "input_hash": "b" * 64}}
            )
        self.assertEqual(len(calls), 1)

    def test_read_projection_removes_private_provenance(self):
        client, calls = self.client(context())
        result = SupabaseSeasonAdminRepository(client).execute(
            "initial_state", {"season_id": SID}
        )
        self.assertNotIn("SECRET", str(result))
        self.assertEqual(calls[0][1]["p_request"]["operation"], "read")

    def test_unknown_backend_error_never_automatically_retries(self):
        calls = []

        def rpc(*args):
            calls.append(args)
            raise RuntimeError("SECRET transport")

        with self.assertRaises(PersistenceError):
            SupabaseSeasonAdminRepository(SimpleNamespace(rpc=rpc)).execute(
                "initial_finalize", {"body": body(context())}
            )
        self.assertEqual(len(calls), 1)

    def test_j1_progress_guards_remain_conflicts_in_both_matchday_flows(self):
        from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
        from app.repositories.supabase.season_admin import SeasonAdminRejected

        class Rejection(Exception):
            code = "PT409"

        for code in ("initial_assignment_required", "initial_assignment_not_ready"):
            for operation in ("open", "participant_results"):
                error = Rejection()
                error.message = code

                def rpc(*args):
                    raise error

                with self.subTest(code=code, operation=operation):
                    with self.assertRaises(SeasonAdminRejected) as raised:
                        SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc)).execute(
                            operation, {}
                        )
                    self.assertEqual(raised.exception.status, 409)
                    self.assertEqual(raised.exception.code, code.upper())


class ObservedOverviewTests(unittest.TestCase):
    def test_transport_diagnostic_never_logs_exception_or_response_contents(self):
        from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository

        class Client:
            def table(self, *args):
                raise RuntimeError("SECRET credential, SQL and private rows")

            def rpc(self, *args):
                raise RuntimeError("SECRET token and payload")

        repo = SupabaseFrontendReadRepository(Client())
        for operation in (
            lambda: repo.rows("seasons", "id"),
            lambda: repo.league_general(SID),
            lambda: repo.initial_observations(SID),
        ):
            with self.assertLogs("app.repositories.supabase.frontend_reads") as log:
                with self.assertRaises(PersistenceError):
                    operation()
            self.assertIn("cause=RuntimeError", str(log.output))
            self.assertNotIn("SECRET", str(log.output))

    def store(self):
        from test_api_frontend_reads import ReadStore, SID as SEASON, PID

        store = ReadStore()
        store.data["seasons"][0]["metadata"] = dict(
            initial_assignment_rule="observed_deaths_v1", private="SECRET"
        )
        store.data["public_season_players"] = [
            dict(id=PID, season_id=SEASON, trainer_id=TRAINER_ID, status="active")
        ]
        store.data["public_season_player_stats"] = [
            dict(season_player_id=PID, season_id=SEASON, badges_count=8)
        ]
        store.observations = [
            dict(
                id=PID,
                progress_state="unknown",
                observed_badges=None,
                private_source="SECRET",
            )
        ]
        store.observation_calls = 0

        def observed(sid):
            self.assertEqual(sid, SEASON)
            store.observation_calls += 1
            return deepcopy(store.observations)

        store.initial_observations = observed
        return store, SEASON

    def test_modern_unknown_ignores_registered_counter_and_hides_metadata(self):
        store, sid = self.store()
        result = FrontendReads(store).overview(sid, TRAINER_ID)
        self.assertIsNone(result.players[0].badges_count)
        self.assertNotIn("SECRET", result.model_dump_json())
        self.assertEqual(store.observation_calls, 1)
        self.assertFalse(any(c[0] == "public_season_player_stats" for c in store.calls))

    def test_observed_zero_stays_zero(self):
        store, sid = self.store()
        store.observations[0].update(progress_state="observed", observed_badges=0)
        self.assertEqual(
            FrontendReads(store).overview(sid, TRAINER_ID).players[0].badges_count, 0
        )

    def test_malformed_or_duplicate_observation_roster_fails_closed(self):
        for invalid in ("duplicate", "foreign", "state", "boolean"):
            store, sid = self.store()
            if invalid == "duplicate":
                store.observations *= 2
            elif invalid == "foreign":
                store.observations[0]["id"] = str(uuid4())
            elif invalid == "state":
                store.observations[0].update(progress_state="manual", observed_badges=2)
            else:
                store.observations[0].update(
                    progress_state="observed", observed_badges=True
                )
            with self.subTest(invalid=invalid), self.assertRaises(PersistenceError):
                FrontendReads(store).overview(sid, TRAINER_ID)


if __name__ == "__main__":
    unittest.main()
