"""Definitive League scoring, retaining explicit historical correction cases."""

from copy import deepcopy
import unittest

from app.application.daily_ranking import RankingDecisionRequired
from app.application.matchdays import plan_close
from test_phase29_single_league import single_league


def context(n=6):
    ctx, ids = single_league(n, movement=0, steal=False)
    ctx["inputs"]["number"] = 1
    ctx["inputs"]["config"].update(
        total_matchdays=1,
        scoring_mode="league_net_v1",
        death_penalty_per_mon="0.1",
        coin_rewards_json={str(i): 17 for i in range(1, n + 1)},
    )
    ctx["ranking_rule"] = "wins_segment_deaths_v2"
    for player in ctx["inputs"]["players"]:
        player.update(actual_deaths=0, wipe_deaths=0, segment_deaths=0,
                      death_penalty_tenths=0, prior_death_penalty_tenths=0,
                      prior_points_reduction="0", death_snapshot_id="frozen-segment-1")
    return ctx, ids


class LeagueRulesTests(unittest.TestCase):
    def test_three_wins_two_losses_award_three_and_common_configured_coins(self):
        ctx, ids = context()
        before = deepcopy(ctx)
        plan = plan_close(ctx)
        rows = {r["trainer_id"]: r for r in plan["standings"]}
        self.assertEqual(rows[ids[2]]["points_awarded"], 3)
        self.assertEqual({r["coins_awarded"] for r in rows.values()}, {17})
        self.assertEqual(plan["single_league_rewards"], [
            dict(code="blindar_pokemon", season_player_id=ids[0]),
            dict(code="robar_pokemon", season_player_id=ids[-1]),
        ])
        self.assertIsNone(plan["last_b_player_id"])
        self.assertEqual(ctx, before)

    def test_three_normal_deaths_and_one_wipe_revival_cost_half_point(self):
        ctx, ids = context()
        # SQL owns the adjusted counter: 3 + 2 * 1, not 3 + 1 + 2.
        ctx["inputs"]["players"][0]["dead_count"] = 5
        ctx["inputs"]["players"][0].update(actual_deaths=4, wipe_deaths=1,
            segment_deaths=4, death_penalty_tenths=5)
        first = next(r for r in plan_close(ctx)["standings"] if r["trainer_id"] == ids[0])
        self.assertEqual(first["penalties"]["dead_points_penalty"], "0.5")

    def test_old_frozen_context_keeps_position_rewards_and_old_death_rate(self):
        ctx, ids = context()
        del ctx["inputs"]["config"]["scoring_mode"]
        del ctx["inputs"]["config"]["death_penalty_per_mon"]
        ctx["ranking_rule"] = "wins_adjusted_deaths_v1"
        ctx["inputs"]["players"][0]["dead_count"] = 3
        plan = plan_close(ctx)
        first = next(r for r in plan["standings"] if r["trainer_id"] == ids[0])
        self.assertEqual(first["points_awarded"], 6)
        self.assertEqual(first["penalties"]["dead_points_penalty"], 0.6)
        self.assertNotIn("single_league_rewards", plan)

    def test_no_arbitrary_common_reward_for_a_positional_map(self):
        ctx, _ = context()
        ctx["inputs"]["config"]["coin_rewards_json"]["1"] = 100
        with self.assertRaisesRegex(ValueError, "common configured"):
            plan_close(ctx)

    def test_last_prize_requires_resolution_even_below_the_podium(self):
        ctx, ids = context()
        # Bottom three each win once, losing all matches against the top three.
        cycle = {(ids[3], ids[4]): ids[3], (ids[4], ids[5]): ids[4], (ids[3], ids[5]): ids[5]}
        for match in ctx["inputs"]["matches"]:
            pair = (match["player_a_id"], match["player_b_id"])
            if pair in cycle:
                match["winner_id"] = cycle[pair]
        with self.assertRaises(RankingDecisionRequired) as raised:
            plan_close(ctx)
        group = next(g for g in raised.exception.review["groups"] if set(g["player_ids"]) == set(ids[3:]))
        self.assertIn("matchday_prize", group["consequences"])

    def test_multiday_awards_victories_without_positional_points(self):
        ctx, ids = context()
        ctx["inputs"]["config"].update(total_matchdays=3)
        ctx["inputs"]["players"][0]["dead_count"] = 1
        ctx["inputs"]["players"][0].update(actual_deaths=1, segment_deaths=1, death_penalty_tenths=1)
        first = next(r for r in plan_close(ctx)["standings"] if r["trainer_id"] == ids[0])
        self.assertEqual(first["points_awarded"], 5)
        self.assertEqual(first["penalties"]["dead_points_penalty"], "0.1")
        self.assertEqual(len(plan_close(ctx)["single_league_rewards"]), 2)


if __name__ == "__main__":
    unittest.main()
