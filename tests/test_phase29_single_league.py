"""One league: one standings, no B, no movement and no last-of-B reward."""

from copy import deepcopy
import unittest

from app.application.initial_assignment import (
    initial_assignment_review,
    plan_initial_assignment,
)
from app.application.matchdays import plan_close
from test_daily_ranking import fixture
from test_initial_assignment import body, context


def single_league(n=4, movement=2, steal=True):
    ctx = fixture()
    inputs = ctx["inputs"]
    ids = [f"p{i}" for i in range(1, n + 1)]
    inputs["players"] = [
        dict(
            id=pid,
            trainer_id=pid,
            ranking_key=pid,
            division="A",
            dead_count=0,
            points_reduction=0,
            coins_reduction=0,
        )
        for pid in ids
    ]
    # Lower id wins: a strict order with no tie to resolve.
    inputs["matches"] = [
        dict(
            id=f"A-{a}-{b}",
            player_a_id=a,
            player_b_id=b,
            winner_id=a,
            division="A",
        )
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
    ]
    inputs["config"].update(
        division_sizes={"A": n},
        # Stored one-league configs carry 0 and false; the planner must not
        # invent movement or a B reward even if handed other values.
        promotion_relegation_count=movement,
        scoring_json={str(i): n - i + 1 for i in range(1, n + 1)},
        coin_rewards_json={str(i): 5 * (n - i + 1) for i in range(1, n + 1)},
        rules_json=dict(team_lock_required=True, last_b_gets_steal=steal),
    )
    return ctx, ids


class SingleLeagueCloseTests(unittest.TestCase):
    def test_one_standings_without_movement_or_last_of_b(self):
        for n in (2, 3, 5, 8):
            with self.subTest(n=n):
                ctx, ids = single_league(n)
                plan = plan_close(ctx)
                rows = sorted(plan["standings"], key=lambda s: s["position"])
                self.assertEqual([s["trainer_id"] for s in rows], ids)
                self.assertEqual([s["position"] for s in rows], list(range(1, n + 1)))
                self.assertEqual(
                    [s["division_position"] for s in rows], list(range(1, n + 1))
                )
                self.assertEqual({s["division_id"] for s in rows}, {"A"})
                self.assertEqual(
                    [s["points_awarded"] for s in rows], list(range(n, 0, -1))
                )
                self.assertEqual(plan["new_divisions"], {"A": ids, "B": []})
                self.assertIsNone(plan["last_b_player_id"])

    def test_two_leagues_unchanged(self):
        ctx = fixture()
        before = deepcopy(ctx)
        plan = plan_close(ctx)
        self.assertEqual(ctx, before)
        self.assertEqual(len(plan["new_divisions"]["A"]), 3)
        self.assertEqual(len(plan["new_divisions"]["B"]), 3)


class SingleLeagueAssignmentTests(unittest.TestCase):
    def test_everyone_starts_in_the_league_without_a_cut(self):
        for deaths in ((0, 1, 2, 3), (2, 2, 2, 2), (5, 0)):
            with self.subTest(deaths=deaths):
                ctx = context(deaths, cut=len(deaths))
                ctx["division_sizes"] = {"A": len(deaths)}
                review = initial_assignment_review(ctx)
                self.assertIsNone(review["boundary_tie"])
                self.assertEqual(
                    {p["proposed_division"] for p in review["players"]}, {"A"}
                )
                plan = plan_initial_assignment(ctx, body(ctx))
                self.assertEqual(len(plan["assignments"]["A"]), len(deaths))
                self.assertEqual(plan["assignments"]["B"], [])

    def test_recorded_one_league_assignment_reads_back(self):
        ctx = context((0, 1, 2), cut=3)
        ctx["division_sizes"] = {"A": 3}
        ids = [p["id"] for p in ctx["players"]]
        ctx.update(state="assigned", ready=False, blocking_reasons=["initial_assignment_locked"],
                   assignments={"A": ids, "B": []})
        review = initial_assignment_review(ctx)
        self.assertEqual({p["proposed_division"] for p in review["players"]}, {"A"})
        self.assertIsNone(review["division_sizes"]["B"])


if __name__ == "__main__":
    unittest.main()
