"""Matchday order of the owner rule of 2026-11-17 (wins_h2h_deaths_v3).

Wins first; exactly two on equal wins: their direct match; three or more:
fewer stretch deaths, and a pair still level on deaths: their direct match.
Three or more with equal wins and deaths keep the extra 1v1 battles.
"""

from datetime import datetime, timedelta, timezone
from itertools import combinations
import unittest
from uuid import uuid4

from app.api.read_models import StandingRead
from app.application.daily_ranking import RankingDecisionRequired
from app.application.frontend_reads import public_daily_standing
from app.application.matchdays import plan_close
from app.domain.services.league import rank_head_to_head
from app.repositories.errors import PersistenceError
from test_phase073_league_rules import context as net_context


def context(n=4):
    ctx, ids = net_context(n)
    ctx["ranking_rule"] = "wins_h2h_deaths_v3"
    return ctx, ids


def play(ctx, winners):
    """Override winners: {(a, b): winner} in either pair order."""
    for match in ctx["inputs"]["matches"]:
        pair = frozenset((match["player_a_id"], match["player_b_id"]))
        for key, winner in winners.items():
            if frozenset(key) == pair:
                match["winner_id"] = winner


def deaths(ctx, values):
    for player in ctx["inputs"]["players"]:
        if player["id"] in values:
            count = values[player["id"]]
            player.update(actual_deaths=count, segment_deaths=count,
                          death_penalty_tenths=count, dead_count=count)


def standings(plan):
    return sorted(plan["standings"], key=lambda r: r["metadata"]["allocation_position"])


def order(plan):
    return [r["trainer_id"] for r in standings(plan)]


def cycle_top_three(ctx, ids):
    # p1>p2, p2>p3, p3>p1; all three beat p4: three on two wins.
    play(ctx, {(ids[0], ids[1]): ids[0], (ids[1], ids[2]): ids[1], (ids[0], ids[2]): ids[2]})


class HeadToHeadTiebreakTests(unittest.TestCase):
    def test_two_level_on_wins_are_ordered_by_their_direct_match_not_deaths(self):
        # Iker/Anto: same record, Iker won the direct match, Anto died less.
        ctx, ids = context()
        play(ctx, {(ids[0], ids[2]): ids[2], (ids[2], ids[3]): ids[3]})
        deaths(ctx, {ids[0]: 5, ids[1]: 0, ids[2]: 1})
        plan = plan_close(ctx)
        self.assertEqual(order(plan), [ids[0], ids[1], ids[3], ids[2]])
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        for pid in ids:
            self.assertEqual(rows[pid]["metadata"]["tiebreak"], "head_to_head")
            self.assertEqual(rows[pid]["metadata"]["tie_status"], "unique")
            self.assertEqual(rows[pid]["metadata"]["tie_size"], 1)
            self.assertEqual(rows[pid]["metadata"]["ranking_rule"], "wins_h2h_deaths_v3")
        self.assertEqual(rows[ids[0]]["metadata"]["actual_segment_deaths"], 5)
        self.assertEqual(plan["single_league_rewards"], [
            dict(code="blindar_pokemon", season_player_id=ids[0]),
            dict(code="robar_pokemon", season_player_id=ids[2]),
        ])
        self.assertEqual(rows[ids[0]]["metadata"]["placement_rewards"], ["blindar_pokemon"])
        self.assertEqual(rows[ids[2]]["metadata"]["placement_rewards"], ["robar_pokemon"])
        self.assertEqual(plan["ranking"]["groups"], [])
        self.assertEqual(rows[ids[0]]["points_awarded"], 2)

        # The previous rule put the trainer with fewer deaths first.
        ctx["ranking_rule"] = "wins_segment_deaths_v2"
        old = plan_close(ctx)
        self.assertEqual(order(old)[0], ids[1])
        self.assertNotIn("tiebreak", old["standings"][0]["metadata"])

    def test_three_level_on_wins_are_ordered_by_fewer_deaths(self):
        ctx, ids = context()
        cycle_top_three(ctx, ids)
        deaths(ctx, {ids[0]: 3, ids[1]: 1, ids[2]: 2})
        plan = plan_close(ctx)
        self.assertEqual(order(plan), [ids[1], ids[2], ids[0], ids[3]])
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        self.assertEqual({rows[p]["metadata"]["tiebreak"] for p in ids[:3]}, {"segment_deaths"})
        self.assertIsNone(rows[ids[3]]["metadata"]["tiebreak"])

    def test_a_pair_still_level_after_deaths_uses_its_direct_match(self):
        ctx, ids = context()
        cycle_top_three(ctx, ids)
        deaths(ctx, {ids[0]: 1, ids[1]: 1, ids[2]: 0})
        plan = plan_close(ctx)
        self.assertEqual(order(plan), [ids[2], ids[0], ids[1], ids[3]])
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        self.assertEqual(rows[ids[2]]["metadata"]["tiebreak"], "segment_deaths")
        self.assertEqual(rows[ids[0]]["metadata"]["tiebreak"], "head_to_head")
        self.assertEqual(rows[ids[1]]["metadata"]["tiebreak"], "head_to_head")
        self.assertEqual(plan["single_league_rewards"][0]["season_player_id"], ids[2])

    def test_three_level_on_wins_and_deaths_for_the_podium_need_extra_battles(self):
        ctx, ids = context()
        cycle_top_three(ctx, ids)
        with self.assertRaises(RankingDecisionRequired) as raised:
            plan_close(ctx)
        review = raised.exception.review
        self.assertEqual(review["ranking_rule"], "wins_h2h_deaths_v3")
        [group] = review["groups"]
        self.assertEqual(set(group["player_ids"]), set(ids[:3]))
        self.assertIn("matchday_prize", group["consequences"])
        played = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        chosen = [ids[2], ids[0], ids[1]]
        battles = [dict(player_a_id=a, player_b_id=b,
                        winner_id=a if chosen.index(a) < chosen.index(b) else b,
                        played_at=played, evidence="Extra 1v1 witnessed")
                   for a, b in combinations(group["player_ids"], 2)]
        plan = plan_close(ctx, tie_resolution=dict(input_hash=review["input_hash"], orders=[
            dict(player_ids=chosen, reason="Extra 1v1 battles", battles=battles)]))
        self.assertEqual(order(plan), chosen + [ids[3]])
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        self.assertEqual(rows[ids[2]]["metadata"]["tie_status"], "externally_resolved")
        self.assertIsNone(rows[ids[2]]["metadata"]["tiebreak"])

    def test_three_level_away_from_prizes_share_their_place(self):
        ctx, ids = context(7)
        # p4>p5, p5>p6, p6>p4: three on two wins at places 4-6 of 7.
        play(ctx, {(ids[3], ids[5]): ids[5]})
        plan = plan_close(ctx)
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        for pid in ids[3:6]:
            self.assertEqual(rows[pid]["metadata"]["tie_status"], "unresolved_neutral")
            self.assertEqual((rows[pid]["position"], rows[pid]["metadata"]["position_end"]), (4, 6))
        self.assertEqual(rows[ids[6]]["metadata"]["placement_rewards"], ["robar_pokemon"])

    def test_a_pair_is_never_offered_as_a_tie_to_resolve(self):
        ctx, ids = context()
        play(ctx, {(ids[0], ids[2]): ids[2], (ids[2], ids[3]): ids[3]})
        # Equal deaths: the old rule needed extra battles for this pair.
        ctx["ranking_rule"] = "wins_segment_deaths_v2"
        with self.assertRaises(RankingDecisionRequired):
            plan_close(ctx)
        ctx["ranking_rule"] = "wins_h2h_deaths_v3"
        self.assertEqual(order(plan_close(ctx)), [ids[0], ids[1], ids[3], ids[2]])

    def test_closed_read_exposes_the_tiebreak_and_stays_strict(self):
        ctx, ids = context()
        play(ctx, {(ids[0], ids[2]): ids[2], (ids[2], ids[3]): ids[3]})
        first = standings(plan_close(ctx))[0]
        snapshot = dict(inputs=dict(ranking=dict(rule="wins_h2h_deaths_v3")))
        result = public_daily_standing(snapshot, first)
        self.assertEqual((result["tiebreak"], result["placement_rewards"]), ("head_to_head", ["blindar_pokemon"]))
        read = StandingRead.model_validate(dict(result, season_player_id=str(uuid4())))
        self.assertEqual(read.tiebreak, "head_to_head")
        del first["metadata"]["tiebreak"]
        with self.assertRaises(PersistenceError):
            public_daily_standing(snapshot, first)

    def test_domain_refuses_an_undecided_direct_match(self):
        with self.assertRaisesRegex(ValueError, "Undecided direct match"):
            rank_head_to_head(["a", "b"], {}, dead_counts={"a": 0, "b": 0})
        ranking = rank_head_to_head(["a", "b"], {("b", "a"): "b"}, dead_counts={"a": 0, "b": 9})
        self.assertEqual(ranking.unique_order(), ("b", "a"))


if __name__ == "__main__":
    unittest.main()
