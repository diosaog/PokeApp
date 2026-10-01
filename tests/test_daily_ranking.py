"""Daily sporting ties cannot silently allocate rewards or division places."""

from copy import deepcopy
from decimal import Decimal
import unittest

from app.application.daily_ranking import LEGACY_RULE, RULE, RankingDecisionRequired
from app.application.matchdays import plan_close
from app.domain.services.league import rank_division
from test_api_matchdays import domain_context


def cycle(players):
    a, b, c = players
    return {(a, b): a, (b, c): b, (a, c): c}


def two_pairs(players):
    """Complete four-player round: first two win twice, last two once."""
    a, b, c, d = players
    return {(a, b): a, (a, c): a, (a, d): d, (b, c): b, (b, d): b, (c, d): c}


def fixture(*, four_in_b=False):
    context = domain_context()
    a = ["a1", "a2", "a3"]
    b = ["b1", "b2", "b3", "b4"] if four_in_b else ["b1", "b2", "b3"]
    inputs = context["inputs"]
    inputs["results_revision"] = 7
    inputs["players"] = [
        dict(
            id=pid,
            trainer_id=pid,
            ranking_key=pid,
            division=division,
            dead_count=0,
            points_reduction=0,
            coins_reduction=0,
        )
        for division, ids in (("A", a), ("B", b))
        for pid in ids
    ]
    if four_in_b:
        for p in inputs["players"]:
            if p["id"] in ("b3", "b4"):
                p["dead_count"] = int(p["id"][-1])
    inputs["config"].update(
        division_sizes={"A": len(a), "B": len(b)},
        promotion_relegation_count=0,
        scoring_json={str(i): 7 for i in range(1, len(a) + len(b) + 1)},
        coin_rewards_json={str(i): 11 for i in range(1, len(a) + len(b) + 1)},
        rules_json=dict(team_lock_required=True, last_b_gets_steal=False),
    )
    a_results = {(a[0], a[1]): a[0], (a[0], a[2]): a[0], (a[1], a[2]): a[1]}
    inputs["matches"] = [
        dict(
            id=f"{division}-{left}-{right}",
            player_a_id=left,
            player_b_id=right,
            winner_id=winner,
            division=division,
        )
        for division, results in (
            ("A", a_results),
            ("B", two_pairs(b) if four_in_b else cycle(b)),
        )
        for (left, right), winner in results.items()
    ]
    return context


def pending_review(context, corrections=None):
    try:
        plan_close(context, corrections)
    except RankingDecisionRequired as exc:
        if exc.code != "RANKING_TIE_UNRESOLVED":
            raise
        return exc.review
    raise AssertionError("Expected a consequential sporting tie")


def resolution(review):
    return dict(
        input_hash=review["input_hash"],
        orders=[
            dict(
                player_ids=list(reversed(group["player_ids"])),
                reason="External agreed playoff order",
            )
            for group in review["groups"]
            if group["consequences"]
        ],
    )


class SportingComparisonTests(unittest.TestCase):
    def test_two_players_wins_precede_adjusted_deaths(self):
        ranking = rank_division(
            ["a", "b"], {("a", "b"): "a"}, dead_counts={"a": 100, "b": 0}
        )
        self.assertEqual(ranking.unique_order(), ("a", "b"))

    def test_two_equal_win_players_use_fewer_deaths(self):
        ranking = rank_division(["a", "b"], {}, dead_counts={"a": 2, "b": 1})
        self.assertEqual(ranking.unique_order(), ("b", "a"))

    def test_two_equal_wins_and_deaths_are_not_unique(self):
        ranking = rank_division(["z", "a"], {}, dead_counts={"z": 1, "a": 1})
        self.assertEqual(ranking.groups[0].display_members, ("a", "z"))
        with self.assertRaises(ValueError):
            ranking.unique_order()
        with self.assertRaises(TypeError):
            _ = ranking[0]

    def test_three_different_win_counts_precede_deaths(self):
        results = {("a", "b"): "a", ("a", "c"): "a", ("b", "c"): "b"}
        ranking = rank_division(
            ["c", "b", "a"], results, dead_counts={"a": 100, "b": 10, "c": 0}
        )
        self.assertEqual(ranking.unique_order(), ("a", "b", "c"))

    def test_three_equal_win_counts_use_deaths_without_head_to_head(self):
        ranking = rank_division(
            ["a", "b", "c"],
            cycle(["a", "b", "c"]),
            dead_counts={"a": 3, "b": 2, "c": 1},
        )
        self.assertEqual(ranking.unique_order(), ("c", "b", "a"))

    def test_residual_pair_is_unresolved_even_when_head_to_head_exists(self):
        ranking = rank_division(
            ["a", "b", "c"],
            cycle(["a", "b", "c"]),
            dead_counts={"a": 0, "b": 1, "c": 1},
        )
        self.assertEqual(
            [g.display_members for g in ranking.groups], [("a",), ("b", "c")]
        )
        with self.assertRaises(ValueError):
            ranking.unique_order()

    def test_complete_round_two_way_tie_ignores_head_to_head(self):
        ids = ["a", "b", "c", "d"]
        ranking = rank_division(
            ids, two_pairs(ids), dead_counts={"a": 2, "b": 0, "c": 3, "d": 4}
        )
        self.assertEqual(ranking.unique_order(), ("b", "a", "c", "d"))

    def test_names_uuid_and_input_order_only_order_transport(self):
        for ids in (
            ["Zoe", "Ana", "Bo"],
            [
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "00000000-0000-0000-0000-000000000001",
                "other",
            ],
        ):
            with self.subTest(ids=ids):
                matches = cycle(ids)
                first = rank_division(ids, matches, dead_counts={p: 0 for p in ids})
                reordered = rank_division(
                    list(reversed(ids)),
                    dict(reversed(list(matches.items()))),
                    dead_counts={p: 0 for p in ids},
                )
                self.assertEqual(first, reordered)
                self.assertEqual(len(first.groups), 1)
                self.assertEqual(set(first.groups[0].display_members), set(ids))
                with self.assertRaises(ValueError):
                    first.unique_order()

    def test_large_adjusted_deaths_remain_exact_and_fractional_values_rejected(self):
        large = 2**60
        ranking = rank_division(
            ["a", "z"], {}, dead_counts={"a": large + 2, "z": large + 1}
        )
        self.assertEqual(ranking.unique_order(), ("z", "a"))
        self.assertEqual(ranking.groups[0].adjusted_deaths, large + 1)
        for invalid in (-1, True, 1.2, Decimal("1.2"), "1", None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                rank_division(["a"], {}, dead_counts={"a": invalid})


class DailyConsequenceTests(unittest.TestCase):
    def test_neutral_tie_after_podium_closes_with_shared_sporting_places(self):
        context = fixture()
        plan = plan_close(context)
        tied = [r for r in plan["standings"] if r["division_id"] == "B"]
        self.assertEqual({r["position"] for r in tied}, {4})
        self.assertEqual({r["division_position"] for r in tied}, {1})
        self.assertEqual(
            {r["metadata"]["allocation_position"] for r in tied}, {4, 5, 6}
        )
        self.assertEqual(
            {r["metadata"]["tie_status"] for r in tied}, {"unresolved_neutral"}
        )
        self.assertEqual({r["metadata"]["position_end"] for r in tied}, {6})
        self.assertEqual({r["points_awarded"] for r in tied}, {7})
        self.assertEqual({r["coins_awarded"] for r in tied}, {11})
        self.assertEqual(plan["new_divisions"]["B"], ["b1", "b2", "b3"])
        self.assertIsNone(plan["last_b_player_id"])
        self.assertEqual(plan["ranking"]["resolutions"], [])

    def test_each_different_consequence_requires_resolution(self):
        for consequence in ("points", "coins", "movement", "last_b_reward"):
            with self.subTest(consequence=consequence):
                context = fixture()
                config = context["inputs"]["config"]
                if consequence == "points":
                    config["scoring_json"]["5"] = 8
                elif consequence == "coins":
                    config["coin_rewards_json"]["5"] = 12
                elif consequence == "movement":
                    config["promotion_relegation_count"] = 1
                else:
                    config["rules_json"]["last_b_gets_steal"] = True
                review = pending_review(context)
                self.assertEqual(review["groups"][0]["consequences"], [consequence])

    def test_podium_requires_resolution_even_when_rewards_are_equal(self):
        context = fixture()
        for match in context["inputs"]["matches"]:
            if match["player_a_id"] == "a1" and match["player_b_id"] == "a3":
                match["winner_id"] = "a3"
        review = pending_review(context)
        a_tie = next(g for g in review["groups"] if g["division"] == "A")
        self.assertEqual(a_tie["consequences"], ["podium"])

    def test_tie_wholly_inside_promoted_block_needs_no_resolution(self):
        context = fixture(four_in_b=True)
        context["inputs"]["config"]["promotion_relegation_count"] = 2
        plan = plan_close(context)
        self.assertEqual(set(plan["new_divisions"]["A"]), {"a1", "b1", "b2"})
        tied = [r for r in plan["standings"] if r["trainer_id"] in ("b1", "b2")]
        self.assertEqual([r["position"] for r in tied], [4, 4])
        self.assertEqual(plan["ranking"]["groups"][0]["consequences"], [])

    def test_tie_crossing_promotion_cut_cannot_allocate_movement(self):
        context = fixture(four_in_b=True)
        context["inputs"]["config"]["promotion_relegation_count"] = 1
        review = pending_review(context)
        self.assertEqual(review["groups"][0]["player_ids"], ["b1", "b2"])
        self.assertEqual(review["groups"][0]["consequences"], ["movement"])
        plan = plan_close(context, tie_resolution=resolution(review))
        self.assertIn("b2", plan["new_divisions"]["A"])
        self.assertNotIn("b1", plan["new_divisions"]["A"])

    def test_final_has_no_movement_but_last_b_reward_still_requires_resolution(self):
        context = fixture()
        context["inputs"]["number"] = 2
        context["inputs"]["config"]["promotion_relegation_count"] = 1
        self.assertEqual(
            plan_close(context)["ranking"]["groups"][0]["consequences"], []
        )
        context["inputs"]["config"]["rules_json"]["last_b_gets_steal"] = True
        review = pending_review(context)
        self.assertEqual(review["groups"][0]["consequences"], ["last_b_reward"])
        plan = plan_close(context, tie_resolution=resolution(review))
        self.assertEqual(plan["last_b_player_id"], "b1")

    def test_explicit_order_allocates_and_audits_differing_rewards(self):
        context = fixture()
        context["inputs"]["config"]["scoring_json"].update({"4": 30, "5": 20, "6": 10})
        review = pending_review(context)
        decision = resolution(review)
        plan = plan_close(context, tie_resolution=decision)
        standings = {r["trainer_id"]: r for r in plan["standings"]}
        self.assertEqual(
            [standings[p]["points_awarded"] for p in ("b3", "b2", "b1")], [30, 20, 10]
        )
        self.assertEqual(plan["ranking"]["resolutions"], decision["orders"])
        self.assertEqual(plan["ranking"]["input_hash"], review["input_hash"])
        self.assertEqual(
            {standings[p]["metadata"]["tie_status"] for p in ("b1", "b2", "b3")},
            {"externally_resolved"},
        )

    def test_missing_invalid_and_duplicate_decisions_fail_closed(self):
        context = fixture()
        context["inputs"]["config"]["promotion_relegation_count"] = 1
        review = pending_review(context)
        valid = resolution(review)
        invalid_orders = [
            [dict(player_ids=["b1", "b2"], reason="Incomplete block")],
            [dict(player_ids=["b1", "b2", "a1"], reason="Foreign member")],
            [dict(player_ids=["b1", "b1", "b2", "b3"], reason="Duplicate member")],
            [dict(player_ids=["b1", "b2", "b3"], reason=" ")],
            [dict(player_ids=["b1", "b2", "b3"], reason="x" * 501)],
            valid["orders"] * 2,
        ]
        for orders in invalid_orders:
            with (
                self.subTest(orders=orders),
                self.assertRaises(RankingDecisionRequired) as caught,
            ):
                plan_close(
                    context,
                    tie_resolution=dict(input_hash=review["input_hash"], orders=orders),
                )
            self.assertEqual(caught.exception.code, "INVALID_TIE_RESOLUTION")
        with self.assertRaises(RankingDecisionRequired) as caught:
            plan_close(
                context, tie_resolution=dict(input_hash=review["input_hash"], orders=[])
            )
        self.assertEqual(caught.exception.code, "RANKING_TIE_UNRESOLVED")

    def test_external_order_cannot_override_neutral_tie(self):
        context = fixture()
        plan = plan_close(context)
        with self.assertRaises(RankingDecisionRequired) as caught:
            plan_close(
                context,
                tie_resolution=dict(
                    input_hash=plan["ranking"]["input_hash"],
                    orders=[
                        dict(
                            player_ids=["b3", "b2", "b1"],
                            reason="Not a sporting reason",
                        )
                    ],
                ),
            )
        self.assertEqual(caught.exception.code, "INVALID_TIE_RESOLUTION")

    def test_review_hash_binds_results_deaths_config_and_revision(self):
        initial = fixture()
        initial["inputs"]["config"]["promotion_relegation_count"] = 1
        decision = resolution(pending_review(initial))
        for field in ("result", "deaths", "config", "revision"):
            context = deepcopy(initial)
            if field == "result":
                context["inputs"]["matches"][0]["winner_id"] = "a2"
            elif field == "deaths":
                context["inputs"]["players"][0]["dead_count"] = 1
            elif field == "config":
                context["inputs"]["config"]["coin_rewards_json"]["1"] = 50
            else:
                context["inputs"]["results_revision"] += 1
            with (
                self.subTest(field=field),
                self.assertRaises(RankingDecisionRequired) as caught,
            ):
                plan_close(context, tie_resolution=decision)
            self.assertEqual(caught.exception.code, "RANKING_REVIEW_STALE")

    def test_duplicate_slugs_and_reordered_sources_do_not_choose_sporting_places(self):
        context = fixture()
        original = plan_close(context)
        for p in context["inputs"]["players"]:
            p["ranking_key"] = "same-name"
        context["inputs"]["players"].reverse()
        context["inputs"]["matches"].reverse()
        reordered = plan_close(context)
        self.assertEqual(original["standings"], reordered["standings"])
        self.assertEqual(original["ranking"], reordered["ranking"])

    def test_frozen_context_and_resolution_are_not_mutated(self):
        context = fixture()
        context["inputs"]["config"]["promotion_relegation_count"] = 1
        decision = resolution(pending_review(context))
        before, original_decision = deepcopy(context), deepcopy(decision)
        plan_close(context, tie_resolution=decision)
        self.assertEqual(context, before)
        self.assertEqual(decision, original_decision)

    def test_correction_review_uses_corrected_results_and_keeps_original_inputs(self):
        context = fixture()
        corrections = [dict(match_id="A-a1-a3", winner_season_player_id="a3")]
        before = deepcopy(context)
        review = pending_review(context, corrections)
        plan = plan_close(context, corrections, resolution(review))
        self.assertEqual(context, before)
        self.assertEqual(
            next(m for m in plan["matches"] if m["id"] == "A-a1-a3")["winner_id"], "a3"
        )
        self.assertEqual(plan["ranking"]["groups"][0]["status"], "externally_resolved")
        self.assertEqual(plan["ranking"]["groups"][1]["status"], "unresolved_neutral")

    def test_legacy_frozen_correction_keeps_historical_rule(self):
        context = fixture(four_in_b=True)
        context["ranking_rule"] = LEGACY_RULE
        for p in context["inputs"]["players"]:
            if p["id"] == "b1":
                p["dead_count"] = 5
        before = deepcopy(context)
        correction = [dict(match_id="A-a1-a3", winner_season_player_id="a3")]
        legacy = plan_close(context, correction)
        self.assertEqual(context, before)
        self.assertEqual(
            [r["trainer_id"] for r in legacy["standings"]],
            ["a1", "a2", "a3", "b1", "b2", "b3", "b4"],
        )
        self.assertEqual(legacy["ranking"]["rule"], LEGACY_RULE)
        self.assertEqual(legacy["ranking"]["resolutions"], [])
        modern = deepcopy(context)
        modern["ranking_rule"] = RULE
        plan = plan_close(modern)
        self.assertEqual(
            [r["trainer_id"] for r in plan["standings"]][3:5], ["b2", "b1"]
        )

    def test_legacy_correction_rejects_new_manual_override(self):
        context = domain_context()
        context["ranking_rule"] = LEGACY_RULE
        with self.assertRaises(RankingDecisionRequired) as caught:
            plan_close(context, tie_resolution=dict(input_hash="0" * 64, orders=[]))
        self.assertEqual(caught.exception.code, "INVALID_TIE_RESOLUTION")

    def test_decimal_sanction_is_preserved_and_not_a_sporting_tie_breaker(self):
        context = fixture()
        exact = "9007199254740993.123456789"
        next(p for p in context["inputs"]["players"] if p["id"] == "b1")[
            "points_reduction"
        ] = exact
        plan = plan_close(context)
        row = next(r for r in plan["standings"] if r["trainer_id"] == "b1")
        self.assertEqual(row["penalties"]["points_reduction"], exact)
        self.assertEqual(row["position"], 4)
        self.assertEqual(row["points_awarded"], 7)


if __name__ == "__main__":
    unittest.main()
