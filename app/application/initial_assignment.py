"""Initial divisions consume observed facts, never daily wins or rewards."""

from app.domain.services.league import rank_division

RULE = "observed_deaths_v1"


class InitialAssignmentRejected(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def initial_assignment_review(context: dict) -> dict:
    from app.api.initial_assignment_models import InitialAssignmentRead

    # Explicit projection prevents source IDs/payloads/audit reasons leaking.
    result = {
        key: context[key]
        for key in (
            "season_id",
            "rule",
            "state",
            "config_version_id",
            "division_sizes",
            "setup_revision",
            "roster_revision",
            "input_hash",
            "ready",
            "blocking_reasons",
        )
    }
    result["players"] = [
        dict(
            **{
                key: row[key]
                for key in (
                    "id",
                    "trainer_id",
                    "display_name",
                    "progress_state",
                    "observed_badges",
                    "cap_reached",
                    "adjusted_deaths",
                )
            },
            proposed_division=None,
        )
        for row in context["players"]
    ]
    result["boundary_tie"] = None
    # Validate trusted facts before interpreting them. Invalid is not "unready".
    InitialAssignmentRead.model_validate(result)
    players = {p["id"]: p for p in result["players"]}
    if result["state"] == "assigned":
        assignments = context["assignments"]
        assigned = assignments["A"] + assignments["B"]
        if len(assigned) != len(players) or set(assigned) != set(players):
            raise ValueError("Invalid recorded assignments")
        for division in ("A", "B"):
            if len(assignments[division]) != result["division_sizes"][division]:
                raise ValueError("Invalid recorded capacity")
            for pid in assignments[division]:
                players[pid]["proposed_division"] = division
    elif result["ready"]:
        cutoff = result["division_sizes"]["A"]
        consumed = 0
        groups = rank_division(
            list(players),
            {},
            dead_counts={pid: p["adjusted_deaths"] for pid, p in players.items()},
        ).groups
        for group in groups:
            end = consumed + len(group.display_members)
            if consumed < cutoff < end:
                result["boundary_tie"] = dict(
                    player_ids=list(group.display_members),
                    adjusted_deaths=group.adjusted_deaths,
                    places_in_a=cutoff - consumed,
                )
            else:
                division = "A" if end <= cutoff else "B"
                for pid in group.display_members:
                    players[pid]["proposed_division"] = division
            consumed = end
    return InitialAssignmentRead.model_validate(result).model_dump(mode="json")


def plan_initial_assignment(context: dict, body: dict) -> dict:
    review = initial_assignment_review(context)
    if body["input_hash"] != review["input_hash"]:
        raise InitialAssignmentRejected("INITIAL_ASSIGNMENT_REVIEW_STALE")
    if review["state"] != "pending":
        raise InitialAssignmentRejected("INITIAL_ASSIGNMENT_LOCKED")
    if not review["ready"]:
        raise InitialAssignmentRejected("INITIAL_ASSIGNMENT_NOT_READY")
    if body["config_version_id"] != review["config_version_id"] or (
        body["expected_setup_revision"] != review["setup_revision"]
        or body["expected_roster_revision"] != review["roster_revision"]
    ):
        raise InitialAssignmentRejected("STALE_REVISION")
    boundary, resolution = review["boundary_tie"], body.get("tie_resolution")
    if resolution is not None and resolution.get("input_hash") != review["input_hash"]:
        raise InitialAssignmentRejected("INITIAL_ASSIGNMENT_REVIEW_STALE")
    if not boundary and resolution is not None:
        raise InitialAssignmentRejected("INVALID_TIE_RESOLUTION")
    allocations = {
        division: [
            p["id"] for p in review["players"] if p["proposed_division"] == division
        ]
        for division in ("A", "B")
    }
    decision = None
    if boundary:
        if resolution is None:
            raise InitialAssignmentRejected("INITIAL_BOUNDARY_TIE_UNRESOLVED")
        orders = resolution.get("orders", [])
        if len(orders) != 1:
            raise InitialAssignmentRejected("INVALID_TIE_RESOLUTION")
        decision = orders[0]
        ids, reason = decision.get("player_ids", []), decision.get("reason")
        if (
            len(ids) != len(set(ids))
            or set(ids) != set(boundary["player_ids"])
            or not isinstance(reason, str)
            or not 1 <= len(reason.strip()) <= 500
        ):
            raise InitialAssignmentRejected("INVALID_TIE_RESOLUTION")
        count = boundary["places_in_a"]
        allocations["A"].extend(ids[:count])
        allocations["B"].extend(ids[count:])
        decision = dict(player_ids=ids, reason=reason.strip())
    return dict(
        assignments={d: sorted(ids) for d, ids in allocations.items()},
        audit=dict(
            rule=RULE,
            input_hash=review["input_hash"],
            boundary_tie=boundary,
            resolution=decision,
        ),
    )
