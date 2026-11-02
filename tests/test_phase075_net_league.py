"""Official +1 scoring and witnessed extra battles, isolated from SQL/production."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from itertools import combinations
import unittest
from uuid import uuid4

from app.api.death_history_models import DeathHistoryBody, DeathHistoryRead
from app.api.matchday_models import TieOrder
from app.application.daily_ranking import NET_RULE, RankingDecisionRequired
from app.application.frontend_reads import public_daily_standing
from app.application.matchdays import plan_close
from test_phase073_league_rules import context
import test_api_season_admin as admin_fixture

SID = admin_fixture.SID


def row(plan, player_id):
    return next(s for s in plan["standings"] if s["trainer_id"] == player_id)


def deaths(player, actual, wipe=0, segment=None, previous=0):
    player.update(actual_deaths=actual, wipe_deaths=wipe,
        segment_deaths=actual if segment is None else segment,
        death_penalty_tenths=actual+wipe, dead_count=actual+wipe,
        prior_death_penalty_tenths=previous)


def tied_context():
    ctx, ids = context(5)
    # A genuine complete normal round robin where every participant wins twice.
    for match in ctx["inputs"]["matches"]:
        i, j = ids.index(match["player_a_id"]), ids.index(match["player_b_id"])
        match["winner_id"] = ids[i] if (j-i) % 5 in (1, 2) else ids[j]
    return ctx, ids


def tie_review(ctx):
    try:
        plan_close(ctx)
    except RankingDecisionRequired as exc:
        return exc.review
    raise AssertionError("Expected unresolved consequential tie")


def battle_resolution(review, ids):
    return dict(input_hash=review["input_hash"], orders=[dict(
        player_ids=ids, reason="Actual extra 1v1 battles reviewed",
        battles=[dict(player_a_id=a, player_b_id=b, winner_id=a,
            played_at="2026-10-01T12:00:00+00:00", evidence=f"Recorded extra battle {a}/{b}")
            for a, b in combinations(ids, 2)],
    )])


class NetLeagueTests(unittest.TestCase):
    def test_one_win_one_point_and_all_days_share_same_contract(self):
        for days in (1, 2, 3, 4, 9):
            ctx, ids = context(5)
            ctx["inputs"]["config"]["total_matchdays"] = days
            for day in range(1, days+1):
                ctx["inputs"]["number"] = day
                plan = plan_close(ctx)
                self.assertEqual([row(plan, pid)["points_awarded"] for pid in ids], [4, 3, 2, 1, 0])
                self.assertEqual({s["coins_awarded"] for s in plan["standings"]}, {17})
                self.assertEqual(len(plan["single_league_rewards"]), 2)
                self.assertIsNone(plan["last_b_player_id"])

    def test_positional_scoring_map_is_not_authority_for_new_contract(self):
        ctx, ids = context(5)
        ctx["inputs"]["config"]["scoring_json"] = {str(i): 9999 for i in range(1, 6)}
        self.assertEqual(row(plan_close(ctx), ids[0])["points_awarded"], 4)

    def test_ordinary_and_item_revived_deaths_keep_three_actual_and_three_tenths(self):
        for revived_by_item in (False, True):
            ctx, ids = context(5)
            deaths(ctx["inputs"]["players"][0], 3)
            # Item revival is already reconciled in the authoritative ledger;
            # it never removes this cumulative death or adds a second penalty.
            ctx["inputs"]["players"][0]["revived_by_item"] = revived_by_item
            s = row(plan_close(ctx), ids[0])
            self.assertEqual(s["metadata"]["actual_deaths"], 3)
            self.assertEqual(s["penalties"]["dead_points_penalty"], "0.3")

    def test_five_wipe_revivals_are_five_actual_deaths_and_one_point(self):
        ctx, ids = context(5)
        deaths(ctx["inputs"]["players"][0], 5, wipe=5)
        s = row(plan_close(ctx), ids[0])
        self.assertEqual(s["metadata"]["actual_deaths"], 5)
        self.assertEqual(s["metadata"]["actual_segment_deaths"], 5)
        self.assertEqual(s["penalties"]["dead_points_penalty"], "1.0")

    def test_cumulative_penalties_are_reconciled_once_as_net_contributions(self):
        j1, ids1 = context(6)
        deaths(j1["inputs"]["players"][2], 5)
        first = row(plan_close(j1), ids1[2])
        self.assertEqual(first["metadata"]["net_points"], "2.5")
        j2, ids2 = context(5)
        j2["inputs"]["number"] = 2
        j2["inputs"]["config"]["total_matchdays"] = 2
        deaths(j2["inputs"]["players"][2], 6, segment=1, previous=5)
        second = row(plan_close(j2), ids2[2])
        self.assertEqual(second["penalties"]["dead_points_penalty"], "0.6")
        self.assertEqual(second["metadata"]["point_penalties"], "0.1")
        self.assertEqual(Decimal(first["metadata"]["net_points"])+Decimal(second["metadata"]["net_points"]), Decimal("4.4"))

    def test_sanction_delta_preserves_arbitrary_sql_numeric_precision(self):
        ctx, ids = context(5)
        p = ctx["inputs"]["players"][0]
        p.update(points_reduction="1000000000000000000000000000000.00000000000000000002",
                 prior_points_reduction="1000000000000000000000000000000.00000000000000000001")
        s = row(plan_close(ctx), ids[0])
        self.assertEqual(Decimal(s["metadata"]["point_penalties"]), Decimal("0.00000000000000000001"))
        self.assertEqual(s["metadata"]["net_points"], "3.99999999999999999999")

    def test_segment_deaths_not_cumulative_or_wipe_penalty_units_choose_rank(self):
        ctx, ids = tied_context()
        for index, p in enumerate(ctx["inputs"]["players"]):
            deaths(p, 100-index, wipe=10-index, segment=index)
        standings = sorted(plan_close(ctx)["standings"], key=lambda s: s["position"])
        self.assertEqual([s["trainer_id"] for s in standings], ids)
        self.assertEqual([s["metadata"]["actual_segment_deaths"] for s in standings], list(range(5)))

    def test_global_round_robin_and_prizes_preserve_division_membership(self):
        ctx, ids = context(5)
        # The winning participant is in B; wins and the first prize remain global.
        ctx["inputs"]["config"]["division_sizes"] = {"A": 3, "B": 2}
        for p in ctx["inputs"]["players"]:
            p["division"] = "B" if p["id"] in ids[:2] else "A"
        plan = plan_close(ctx)
        self.assertEqual(row(plan, ids[0])["position"], 1)
        self.assertEqual(row(plan, ids[0])["points_awarded"], 4)
        self.assertEqual(plan["single_league_rewards"][0]["season_player_id"], ids[0])
        self.assertEqual(plan["single_league_rewards"][1]["season_player_id"], ids[-1])
        self.assertEqual(plan["new_divisions"]["B"], ids[:2])

    def test_partial_duplicate_or_division_only_round_robin_cannot_close(self):
        for mutation in ("missing", "duplicate", "foreign"):
            ctx, _ = context(5)
            matches = ctx["inputs"]["matches"]
            if mutation == "missing": matches.pop()
            elif mutation == "duplicate": matches[-1] = dict(matches[0], id="different-id")
            else: matches[-1]["player_b_id"] = "outside"
            with self.assertRaises(ValueError): plan_close(ctx)

    def test_unknown_missing_or_inconsistent_death_evidence_cannot_be_zero(self):
        for field in ("actual_deaths", "wipe_deaths", "segment_deaths", "death_snapshot_id",
                      "death_penalty_tenths", "prior_death_penalty_tenths"):
            ctx, _ = context(5)
            ctx["inputs"]["players"][0].pop(field)
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)): plan_close(ctx)
        ctx, _ = context(5)
        deaths(ctx["inputs"]["players"][0], 2, wipe=3)
        with self.assertRaises(ValueError): plan_close(ctx)

    def test_extra_1v1_is_required_and_never_becomes_normal_win_or_point(self):
        ctx, ids = tied_context()
        review = tie_review(ctx)
        self.assertEqual(review["ranking_rule"], NET_RULE)
        decision = battle_resolution(review, ids[::-1])
        before = deepcopy(ctx)
        plan = plan_close(ctx, tie_resolution=decision)
        self.assertEqual([row(plan, pid)["points_awarded"] for pid in ids], [2]*5)
        self.assertEqual([row(plan, pid)["metadata"]["wins"] for pid in ids], [2]*5)
        self.assertEqual(len(plan["matches"]), 10)
        self.assertEqual(plan["single_league_rewards"][0]["season_player_id"], ids[-1])
        self.assertEqual(ctx, before)
        self.assertEqual(len(plan["ranking"]["resolutions"][0]["battles"]), 10)

    def test_arbitrary_order_cyclic_incomplete_foreign_future_battles_block(self):
        ctx, ids = tied_context()
        review = tie_review(ctx)
        for kind in ("missing", "incomplete", "cycle", "duplicate", "foreign", "future", "naive", "empty"):
            decision = battle_resolution(review, ids)
            order = decision["orders"][0]
            if kind == "missing": order.pop("battles")
            elif kind == "incomplete": order["battles"].pop()
            elif kind == "cycle": order["battles"][-1]["winner_id"] = order["battles"][-1]["player_b_id"]
            elif kind == "duplicate": order["battles"][-1] = dict(order["battles"][0])
            elif kind == "foreign": order["battles"][0]["player_a_id"] = "outside"
            elif kind == "future": order["battles"][0]["played_at"] = "2999-01-01T00:00:00+00:00"
            elif kind == "naive": order["battles"][0]["played_at"] = "2026-10-01T00:00:00"
            else: order["battles"][0]["evidence"] = " "
            with self.subTest(kind=kind), self.assertRaises(RankingDecisionRequired) as raised:
                plan_close(ctx, tie_resolution=decision)
            self.assertEqual(raised.exception.code, "INVALID_TIE_RESOLUTION")

    def test_review_hash_binds_historical_counter_revision_snapshot_and_results(self):
        ctx, ids = tied_context()
        decision = battle_resolution(tie_review(ctx), ids)
        for field, value in (("death_snapshot_id", "different-snapshot"), ("actual_deaths", 1),
                             ("prior_points_reduction", "0.1")):
            altered = deepcopy(ctx)
            p = altered["inputs"]["players"][0]
            if field == "actual_deaths": deaths(p, 1, segment=0)
            else: p[field] = value
            with self.subTest(field=field), self.assertRaises(RankingDecisionRequired) as raised:
                plan_close(altered, tie_resolution=decision)
            self.assertEqual(raised.exception.code, "RANKING_REVIEW_STALE")

    def test_battle_transport_is_canonical_and_timezone_is_required(self):
        ids=sorted(str(uuid4()) for _ in range(3))
        battles=battle_resolution({'input_hash':'a'*64},ids)['orders'][0]['battles']
        canonical=TieOrder(player_ids=ids,reason='Recorded played battles',battles=battles[::-1])
        encoded=canonical.model_dump(mode='json')
        self.assertEqual([(b['player_a_id'],b['player_b_id']) for b in encoded['battles']],list(combinations(ids,2)))
        battles[0]['played_at']='2026-10-01T12:00:00'
        with self.assertRaises(ValueError): TieOrder(player_ids=ids,reason='Actual played battles',battles=battles)

    def test_old_073_snapshot_keeps_its_two_point_rule_when_explicitly_frozen(self):
        ctx, ids = context(5)
        ctx["inputs"]["config"]["scoring_mode"] = "single_round_robin_v1"
        ctx["ranking_rule"] = "wins_adjusted_deaths_v1"
        self.assertEqual(row(plan_close(ctx), ids[0])["points_awarded"], 8)

    def test_closed_read_exposes_frozen_breakdown(self):
        ctx, ids = context(5)
        s = row(plan_close(ctx), ids[0])
        result = public_daily_standing(dict(inputs=dict(ranking=dict(rule=NET_RULE))), s)
        self.assertEqual(result["wins"], 4)
        self.assertEqual(result["actual_segment_deaths"], 0)
        self.assertEqual(result["placement_rewards"], ["blindar_pokemon"])


class DeathHistoryApiTests(unittest.TestCase):
    def setUp(self):
        admin_fixture.SeasonAdminApiTests.setUp(self)
        self.pid = str(uuid4())
        self.path = f"/v1/admin/seasons/{SID}/participants/{self.pid}/death-history"
        self.repo.response = dict(season_id=SID, season_player_id=self.pid,trainer_id=str(uuid4()),
            revision=0, known=False, blocking_reason="death_history_evidence_required", actual_deaths=None,
            wipe_deaths=None,death_penalty_tenths=None,source_save_id=str(uuid4()),source_sha256="a"*64,
            identity_revision_id=str(uuid4()),wipe_revision=0,wipe_counter=0,current_matchday_id=str(uuid4()),
            segment_deaths=None,can_reconcile=True,recorded_deaths=0,observed_dead_entities=[],replayed=False)
        self.body = dict(actual_deaths=3,wipe_deaths=0,segment_deaths=3,source_sha256="a"*64,
                         expected_revision=0,reason="Verify source history",evidence="Save history checked")

    def test_admin_read_and_write_bind_scope_actor_source_and_revision(self):
        self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,200)
        self.assertEqual(self.client.put(self.path,json=self.body,headers=self.headers).status_code,200)
        operation, request = self.repo.calls[-1]
        self.assertEqual(operation,"death_history_reconcile")
        self.assertEqual(request["resource_id"],self.pid)
        self.assertEqual(request["body"]["source_sha256"],"a"*64)
        self.assertEqual(request["body"]["expected_revision"],0)
        self.assertIn("actor_trainer_id",request)

    def test_read_and_write_require_admin_and_write_requires_idempotency(self):
        self.assertEqual(self.client.get(self.path).status_code,401)
        self.assertEqual(self.client.put(self.path,json=self.body,headers={"Authorization":"Bearer validated"}).status_code,422)
        self.principals.trainer = replace(self.principals.trainer,is_admin=False)
        self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,403)
        self.assertEqual(self.client.put(self.path,json=self.body,headers=self.headers).status_code,403)
        self.assertFalse(self.repo.calls)

    def test_missing_source_forged_actor_invalid_counts_and_cross_scope_rejected(self):
        for change in (dict(source_sha256=""),dict(actual_deaths=True),dict(wipe_deaths=4),
                       dict(evidence=" "),dict(actor_trainer_id=str(uuid4()))):
            with self.subTest(change=change):
                self.assertEqual(self.client.put(self.path,json={**self.body,**change},headers=self.headers).status_code,422)
        self.repo.response["season_player_id"] = str(uuid4())
        self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,503)

    def test_known_history_cannot_have_unknown_or_double_counted_penalty(self):
        for changed in (dict(known=True),dict(known=True,actual_deaths=5,wipe_deaths=5,death_penalty_tenths=15)):
            with self.assertRaises(ValueError): DeathHistoryRead.model_validate({**self.repo.response,**changed})
        with self.assertRaises(ValueError): DeathHistoryBody.model_validate({**self.body,"revived_entity_ids":[self.pid,self.pid]})
        # Malformed/missing source counters stay actionable unknown evidence;
        # neither the API nor the UI should invent zero or turn it into a 503.
        self.repo.response.update(wipe_counter=None,wipe_revision=None,can_reconcile=False)
        self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,200)


if __name__ == "__main__":
    unittest.main()
