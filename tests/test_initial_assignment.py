"""Initial death groups cannot acquire sporting order from transport ordering."""

from copy import deepcopy
import unittest
from uuid import UUID

from app.application.initial_assignment import (
    InitialAssignmentRejected,
    initial_assignment_review,
    plan_initial_assignment,
)

SID, CID = str(UUID(int=100)), str(UUID(int=101))
DIGEST = "a" * 64


def context(deaths=(0, 1, 2, 3), cut=2):
    return dict(
        season_id=SID,
        rule="observed_deaths_v1",
        state="pending",
        config_version_id=CID,
        division_sizes=dict(A=cut, B=len(deaths) - cut),
        setup_revision=5,
        roster_revision=len(deaths),
        input_hash=DIGEST,
        ready=True,
        blocking_reasons=[],
        players=[
            dict(
                id=str(UUID(int=i + 1)),
                trainer_id=str(UUID(int=i + 20)),
                display_name=f"Player {i}",
                progress_state="observed",
                observed_badges=2,
                cap_reached=True,
                adjusted_deaths=d,
                private_metadata="SECRET",
            )
            for i, d in enumerate(deaths)
        ],
        internal_provenance="SECRET",
    )


def body(ctx):
    return dict(
        config_version_id=ctx["config_version_id"],
        expected_setup_revision=ctx["setup_revision"],
        expected_roster_revision=ctx["roster_revision"],
        input_hash=ctx["input_hash"],
    )


def decide(ctx, ids):
    return dict(
        **body(ctx),
        tie_resolution=dict(
            input_hash=ctx["input_hash"],
            orders=[dict(player_ids=ids, reason="External sporting decision")],
        ),
    )


class InitialAssignmentTests(unittest.TestCase):
    def rejected(self, code, ctx, command):
        with self.assertRaises(InitialAssignmentRejected) as exc:
            plan_initial_assignment(ctx, command)
        self.assertEqual(exc.exception.code, code)

    def test_unambiguous_deaths_not_wins_names_or_sanctions(self):
        ctx = context((3, 0, 2, 1))
        for player in ctx["players"]:
            player.update(wins=100, points_reduction="999.9")
        plan = plan_initial_assignment(ctx, body(ctx))
        self.assertEqual(plan["assignments"]["A"], [str(UUID(int=2)), str(UUID(int=4))])
        self.assertEqual(set(plan), {"assignments", "audit"})
        self.assertIsNone(plan["audit"]["resolution"])

    def test_two_person_boundary_requires_explicit_decision(self):
        ctx = context((0, 2, 2, 5))
        self.rejected("INITIAL_BOUNDARY_TIE_UNRESOLVED", ctx, body(ctx))
        tie = initial_assignment_review(ctx)["boundary_tie"]
        self.assertEqual(tie["places_in_a"], 1)
        self.assertEqual(
            [p["proposed_division"] for p in initial_assignment_review(ctx)["players"]],
            ["A", None, None, "B"],
        )

    def test_multi_person_tie_records_only_boundary_human_order(self):
        ctx = context((0, 1, 1, 1, 2), cut=3)
        ids = initial_assignment_review(ctx)["boundary_tie"]["player_ids"]
        chosen = list(reversed(ids))
        plan = plan_initial_assignment(ctx, decide(ctx, chosen))
        self.assertEqual(
            set(plan["assignments"]["A"]), {ctx["players"][0]["id"], *chosen[:2]}
        )
        self.assertEqual(plan["audit"]["resolution"]["player_ids"], chosen)

    def test_neutral_ties_wholly_inside_each_division(self):
        ctx = context((1, 1, 4, 4))
        self.assertIsNone(initial_assignment_review(ctx)["boundary_tie"])
        self.assertEqual(
            len(plan_initial_assignment(ctx, body(ctx))["assignments"]["A"]), 2
        )
        self.rejected(
            "INVALID_TIE_RESOLUTION",
            ctx,
            decide(ctx, [p["id"] for p in ctx["players"][:2]]),
        )

    def test_every_supported_odd_even_cut_preserves_exact_capacity(self):
        for size in (3, 4, 5, 6):
            for cut in range(1, size):
                with self.subTest(size=size, cut=cut):
                    ctx = context(tuple(range(size)), cut)
                    assignments = plan_initial_assignment(ctx, body(ctx))["assignments"]
                    self.assertEqual(
                        [len(assignments[d]) for d in ("A", "B")], [cut, size - cut]
                    )

    def test_technical_roster_and_name_order_do_not_change_membership(self):
        ctx = context((1, 1, 3, 3))
        original = plan_initial_assignment(ctx, body(ctx))
        ctx["players"].reverse()
        for player in ctx["players"]:
            player["display_name"] = "Z changed"
        self.assertEqual(plan_initial_assignment(ctx, body(ctx)), original)

    def test_missing_observation_is_not_observed_zero(self):
        ctx = context()
        player = ctx["players"][0]
        player.update(progress_state="unknown", observed_badges=None, cap_reached=False)
        ctx.update(ready=False, blocking_reasons=["progress_unobserved"])
        review = initial_assignment_review(ctx)
        self.assertIsNone(review["players"][0]["observed_badges"])
        self.assertTrue(all(p["proposed_division"] is None for p in review["players"]))
        self.rejected("INITIAL_ASSIGNMENT_NOT_READY", ctx, body(ctx))
        player.update(progress_state="observed", observed_badges=0)
        ctx["blocking_reasons"] = ["cap_not_reached"]
        self.assertEqual(
            initial_assignment_review(ctx)["players"][0]["observed_badges"], 0
        )

    def test_missing_deaths_blocks_and_never_becomes_zero(self):
        ctx = context()
        ctx["players"][0]["adjusted_deaths"] = None
        ctx.update(ready=False, blocking_reasons=["death_inputs_unobserved"])
        self.rejected("INITIAL_ASSIGNMENT_NOT_READY", ctx, body(ctx))

    def test_false_authoritative_ready_or_malformed_fact_fails_closed(self):
        for change in (
            dict(observed_badges=None),
            dict(adjusted_deaths=True),
            dict(cap_reached=False),
            dict(adjusted_deaths=1.5),
        ):
            ctx = context()
            ctx["players"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                initial_assignment_review(ctx)

    def test_stale_death_progress_or_decision_hash_rejected(self):
        ctx = context((0, 1, 1, 3))
        command = decide(
            ctx, initial_assignment_review(ctx)["boundary_tie"]["player_ids"]
        )
        changed = deepcopy(ctx)
        changed["input_hash"] = "b" * 64
        self.rejected("INITIAL_ASSIGNMENT_REVIEW_STALE", changed, command)
        command["tie_resolution"]["input_hash"] = "b" * 64
        self.rejected("INITIAL_ASSIGNMENT_REVIEW_STALE", ctx, command)

    def test_config_and_cas_must_match_review(self):
        ctx = context()
        for key, value in (
            ("expected_setup_revision", 0),
            ("expected_roster_revision", 0),
            ("config_version_id", SID),
        ):
            self.rejected("STALE_REVISION", ctx, {**body(ctx), key: value})

    def test_duplicate_foreign_partial_or_multiple_boundary_orders_rejected(self):
        ctx = context((0, 1, 1, 3))
        ids = initial_assignment_review(ctx)["boundary_tie"]["player_ids"]
        for wrong in ([ids[0], ids[0]], ids[:1], [ids[0], ctx["players"][0]["id"]]):
            self.rejected("INVALID_TIE_RESOLUTION", ctx, decide(ctx, wrong))
        command = decide(ctx, ids)
        command["tie_resolution"]["orders"] *= 2
        self.rejected("INVALID_TIE_RESOLUTION", ctx, command)
        for reason in (" ", "x" * 501, None):
            command = decide(ctx, ids)
            command["tie_resolution"]["orders"][0]["reason"] = reason
            self.rejected("INVALID_TIE_RESOLUTION", ctx, command)

    def test_legacy_stays_locked_and_does_not_receive_new_order(self):
        ctx = context()
        ctx.update(
            state="legacy",
            rule=None,
            ready=False,
            blocking_reasons=["initial_assignment_legacy"],
        )
        self.assertTrue(
            all(
                p["proposed_division"] is None
                for p in initial_assignment_review(ctx)["players"]
            )
        )
        self.rejected("INITIAL_ASSIGNMENT_LOCKED", ctx, body(ctx))

    def test_assigned_read_uses_recorded_memberships_and_cannot_refinalize(self):
        ctx = context((3, 2, 1, 0))
        ids = [p["id"] for p in ctx["players"]]
        ctx.update(
            state="assigned",
            ready=False,
            blocking_reasons=[],
            assignments=dict(A=ids[:2], B=ids[2:]),
        )
        self.assertEqual(
            [p["proposed_division"] for p in initial_assignment_review(ctx)["players"]],
            ["A", "A", "B", "B"],
        )
        self.rejected("INITIAL_ASSIGNMENT_LOCKED", ctx, body(ctx))

    def test_public_review_excludes_all_private_source_and_audit_metadata(self):
        ctx = context()
        ctx.update(audit=dict(reason="SECRET"), snapshot="SECRET")
        self.assertNotIn("SECRET", str(initial_assignment_review(ctx)))


if __name__ == "__main__":
    unittest.main()
