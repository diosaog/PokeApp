"""079: ordinary League start (readiness, J1 preparation, own death history).

SQL authority is proven on the real RPCs by tools/validate_phase079_all_vs_all.py;
these tests prove the API forwards only the authenticated caller, validates
every answer and maps refusals to their exact codes.
"""

from copy import deepcopy
from dataclasses import replace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.initial_assignment_models import InitialAssignmentRead
from app.api.main import create_app
from app.application.initial_assignment import initial_assignment_review
from app.repositories.errors import ConflictError
from app.repositories.supabase.matchdays import ERRORS, SupabaseMatchdayRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from team_lock_fixtures import MATCHDAY, SAVE, SEASON, MemoryAtomicTeamLocks
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID, DAY, PID, OTHER = (str(uuid4()) for _ in range(4))
SHA = "a" * 64


def readiness(**changes):
    value = dict(
        season_id=SID, state="unprepared", structure="all_vs_all", matchday=None,
        next_number=1, can_prepare=True, can_open=False, can_operate=True, reasons=[],
        participants=[dict(season_player_id=PID, trainer_id=TRAINER_ID, display_name="Iker",
                           reasons=["death_history_baseline_required"], self_confirmable=True)],
    )
    value.update(changes)
    return value


def own_state(**changes):
    value = dict(
        season_id=SID, season_player_id=PID, trainer_id=TRAINER_ID, revision=1, known=False,
        blocking_reason="death_history_baseline_required", actual_deaths=None, wipe_deaths=None,
        segment_deaths=None, dead_box_number=7, source_sha256=SHA, confirmed_at=None,
        current_matchday_id=None, can_confirm=True, confirm_blocker=None,
        proposed=dict(actual_deaths=3, wipe_deaths=0, segment_deaths=3), replayed=False,
    )
    value.update(changes)
    return value


CONFIRMED = own_state(revision=2, known=True, blocking_reason=None, actual_deaths=3, wipe_deaths=0,
                      segment_deaths=3, confirmed_at="2026-11-04T12:00:00Z", can_confirm=False,
                      confirm_blocker="death_history_confirmed", proposed=None,
                      resolution_id=str(uuid4()))


class FakeRepository:
    def __init__(self):
        self.calls, self.failure = [], None
        self.responses = dict(
            league_readiness=readiness(),
            prepare_first=dict(season_id=SID, matchday_id=DAY, number=1, status="scheduled",
                               revision=0, created=True),
            own_death_state=own_state(),
            own_death_confirm=CONFIRMED,
        )

    def execute(self, operation, request):
        self.calls.append((operation, deepcopy(request)))
        if self.failure:
            raise self.failure
        return deepcopy(self.responses[operation])


class LeagueStartApiTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.principals = FakeRepository(), FakePrincipalRepository()
        # An ordinary trainer, never an administrator.
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=FakeTokenVerifier(), principal_repository=self.principals,
            matchday_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base = f"/v1/seasons/{SID}"
        self.auth = {"Authorization": "Bearer valid"}

    def confirm(self, body=None, headers=None):
        return self.client.put(
            self.base + "/death-history",
            json=body if body is not None else dict(
                expected_revision=1, source_sha256=SHA, actual_deaths=3, wipe_deaths=0, segment_deaths=3),
            headers=headers if headers is not None else dict(self.auth, **{"Idempotency-Key": "death-1"}))

    def test_every_route_refuses_anonymous_callers_before_any_read(self):
        for method, path in (("get", "/league/readiness"), ("post", "/league/first-matchday"),
                             ("get", "/death-history"), ("put", "/death-history")):
            with self.subTest(path=path):
                kwargs = {"json": {}} if method == "put" else {}
                self.assertEqual(getattr(self.client, method)(self.base + path, **kwargs).status_code, 401)
        self.assertEqual(self.repo.calls, [])

    def test_observed_zero_is_readable_without_human_confirmation(self):
        self.repo.responses["own_death_state"] = own_state(
            known=True, blocking_reason=None, actual_deaths=0, wipe_deaths=0,
            segment_deaths=0, confirmed_at=None, can_confirm=False,
            confirm_blocker="death_history_confirmed", proposed=None,
        )
        response = self.client.get(self.base + "/death-history", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actual_deaths"], 0)
        self.assertIsNone(response.json()["confirmed_at"])
        self.assertTrue(response.json()["known"])
        self.assertFalse(response.json()["can_confirm"])
        self.assertEqual([op for op, _ in self.repo.calls], ["own_death_state"])

    def test_readiness_and_preparation_reach_sql_as_the_caller_only(self):
        response = self.client.get(self.base + "/league/readiness", headers=self.auth)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["participants"][0]["reasons"], ["death_history_baseline_required"])
        # A body cannot add an authority: the route reads none.
        prepared = self.client.post(self.base + "/league/first-matchday", headers=self.auth,
                                    json={"actor_trainer_id": str(uuid4()), "is_admin": True})
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(prepared.json()["matchday_id"], DAY)
        self.assertEqual(self.repo.calls, [
            ("league_readiness", dict(actor_trainer_id=TRAINER_ID, season_id=SID)),
            ("prepare_first", dict(actor_trainer_id=TRAINER_ID, season_id=SID)),
        ])

    def test_inconsistent_or_foreign_answers_fail_closed(self):
        for operation, bad in (
            ("league_readiness", readiness(season_id=OTHER)),
            ("league_readiness", readiness(can_open=True)),  # blocked yet open-able
            ("league_readiness", readiness(state="open", matchday=None)),
            ("league_readiness", readiness(participants=[dict(readiness()["participants"][0], reasons=["made_up"])])),
            ("prepare_first", dict(self.repo.responses["prepare_first"], season_id=OTHER)),
            ("own_death_state", own_state(trainer_id=str(uuid4()))),
            ("own_death_state", own_state(can_confirm=True, proposed=None)),
        ):
            with self.subTest(operation=operation, bad=bad):
                self.repo.responses[operation] = bad
                path = {"league_readiness": ("get", "/league/readiness"),
                        "prepare_first": ("post", "/league/first-matchday"),
                        "own_death_state": ("get", "/death-history")}[operation]
                response = getattr(self.client, path[0])(self.base + path[1], headers=self.auth)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()["detail"]["code"], "LEAGUE_UNAVAILABLE")
                self.repo.responses = FakeRepository().responses

    def test_own_confirmation_sends_only_the_shown_values_with_a_key(self):
        response = self.confirm()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["known"])
        operation, request = self.repo.calls[-1]
        self.assertEqual(operation, "own_death_confirm")
        self.assertEqual(request, dict(actor_trainer_id=TRAINER_ID, season_id=SID, idempotency_key="death-1",
                                       body=dict(expected_revision=1, source_sha256=SHA, actual_deaths=3,
                                                 wipe_deaths=0, segment_deaths=3)))
        calls = len(self.repo.calls)
        for body in (
            dict(expected_revision=1, source_sha256=SHA, actual_deaths=3, wipe_deaths=0, segment_deaths=3,
                 season_player_id=PID),  # no target trainer can be named
            dict(expected_revision=1, source_sha256=SHA, actual_deaths=1, wipe_deaths=2, segment_deaths=0),
            dict(expected_revision=1, source_sha256="bad", actual_deaths=3, wipe_deaths=0, segment_deaths=3),
        ):
            with self.subTest(body=body):
                self.assertEqual(self.confirm(body).status_code, 422)
        self.assertEqual(self.confirm(headers=self.auth).status_code, 422)  # Idempotency-Key required
        self.assertEqual(len(self.repo.calls), calls)
        # A success that does not match what was confirmed is not reported as one.
        self.repo.responses["own_death_confirm"] = dict(CONFIRMED, actual_deaths=4, wipe_deaths=1)
        self.assertEqual(self.confirm().status_code, 503)

    def test_sql_refusals_keep_their_exact_code(self):
        for code in ("death_history_admin_required", "death_history_changed", "death_history_already_confirmed",
                     "death_history_revision_conflict", "participant_required", "initial_assignment_required",
                     "opponent_missing", "invalid_roster", "season_not_active"):
            with self.subTest(code=code):
                status = ERRORS[code]
                self.repo.failure = SeasonAdminRejected(code.upper(), status)
                response = self.client.post(self.base + "/league/first-matchday", headers=self.auth)
                self.assertEqual((response.status_code, response.json()["detail"]["code"]), (status, code.upper()))


class Rpc:
    def __init__(self, data):
        self.data, self.calls = data, []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return self

    def execute(self):
        return self


class RepositoryMappingTests(unittest.TestCase):
    def test_league_operations_call_their_own_rpcs_with_the_request(self):
        request = dict(actor_trainer_id=TRAINER_ID, season_id=SID)
        for operation, name, envelope in (
            ("league_readiness", "api_league_readiness", request),
            ("prepare_first", "api_league_prepare_first_matchday", request),
            ("own_death_state", "api_participant_death_history", dict(operation="state", request=request)),
            ("own_death_confirm", "api_participant_death_history", dict(operation="confirm", request=request)),
        ):
            with self.subTest(operation=operation):
                client = Rpc({"ok": True})
                SupabaseMatchdayRepository(client).execute(operation, request)
                self.assertEqual(client.calls, [(name, {"p_request": envelope})])


class TeamLockReasonTests(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryAtomicTeamLocks()
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=FakeTokenVerifier(), principal_repository=FakePrincipalRepository(),
            team_lock_repository=self.repository)))
        self.addCleanup(self.client.close)
        self.path = f"/v1/seasons/{SEASON}/matchdays/{MATCHDAY}/team-lock"

    def put(self):
        return self.client.put(self.path, headers={"Authorization": "Bearer x"}, json={"save_file_id": SAVE})

    def test_actionable_refusal_reasons_reach_the_trainer(self):
        party = self.repository.source.parsed["payload"]["party"]
        self.repository.change("parsed", payload={"party": party[:4]})
        response = self.put()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], dict(
            code="TEAM_LOCK_CONFLICT", message="The current state does not allow this team lock.",
            reason="team_requires_six"))
        self.repository.change("parsed", payload={"party": party})
        self.repository.change("matchday", status="closed")
        self.assertEqual(self.put().json()["detail"]["reason"], "matchday_not_lockable")

    def test_unknown_messages_are_never_echoed(self):
        self.repository.upsert_with_activity = lambda mutation: (_ for _ in ()).throw(
            ConflictError("Team lock mutation was rejected."))
        response = self.put()
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("reason", response.json()["detail"])


class InitialAssignmentNotRequiredTests(unittest.TestCase):
    def test_all_vs_all_review_is_not_required_and_has_no_players(self):
        context = dict(season_id=SID, rule=None, state="not_required", config_version_id=None,
                       division_sizes=None, setup_revision=1, roster_revision=5, input_hash="b" * 64,
                       ready=False, blocking_reasons=["initial_assignment_not_required"], players=[])
        review = initial_assignment_review(context)
        self.assertEqual((review["state"], review["players"], review["boundary_tie"]), ("not_required", [], None))
        InitialAssignmentRead.model_validate(review)


if __name__ == "__main__":
    unittest.main()
