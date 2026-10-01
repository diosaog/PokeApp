"""Consequence review of sporting groups; transport order cannot award a place."""

from dataclasses import dataclass
import hashlib
import json

from app.domain.services.league import rank_division
from app.domain.services.legacy_league import legacy_rank_division

RULE = "wins_adjusted_deaths_v1"
LEGACY_RULE = "legacy_pre_10_5d"


class RankingDecisionRequired(ValueError):
    def __init__(self, code: str, review: dict):
        super().__init__(code)
        self.code, self.review = code, review


@dataclass(frozen=True)
class ConsequenceOrder:
    # Safe only after each sporting tie has been checked against every outcome.
    allocations: dict[str, list[str]]
    sporting_rows: dict[str, dict]
    audit: dict


def consequence_order(
    inputs: dict, matches: dict, rule: str, resolution=None
) -> ConsequenceOrder:
    players = {p["id"]: p for p in inputs["players"]}
    cfg = inputs["config"]
    final = inputs["number"] == cfg["total_matchdays"]
    sizes = {d: sum(p["division"] == d for p in players.values()) for d in ("A", "B")}
    moving = (
        0 if final else min(cfg["promotion_relegation_count"], sizes["A"], sizes["B"])
    )
    if rule not in (RULE, LEGACY_RULE):
        raise ValueError("Unsupported frozen ranking rule")
    canonical = dict(
        rule=rule,
        season_id=inputs["season_id"],
        day_id=inputs["day_id"],
        number=inputs["number"],
        results_revision=inputs["results_revision"]
        if "results_revision" in inputs
        else None,
        config=cfg,
        players=sorted(
            (
                dict(id=p["id"], division=p["division"], dead_count=p["dead_count"])
                for p in players.values()
            ),
            key=lambda p: p["id"],
        ),
        matches=sorted(matches.values(), key=lambda m: m["id"]),
    )
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    review = dict(input_hash=digest, groups=[])
    ordered, rows, audit_groups = {}, {}, []
    group_data = []
    offset = 0
    for division in ("A", "B"):
        members = [p["id"] for p in players.values() if p["division"] == division]
        results = {
            (m["player_a_id"], m["player_b_id"]): m["winner_id"]
            for m in matches.values()
            if m["division"] == division
        }
        deaths = {pid: players[pid]["dead_count"] for pid in members}
        if rule == LEGACY_RULE:
            keys = {players[pid]["ranking_key"]: pid for pid in members}
            if len(keys) != len(members):
                raise ValueError("Non-unique historical ranking identity")
            old_results = {
                (players[a]["ranking_key"], players[b]["ranking_key"]): players[w][
                    "ranking_key"
                ]
                for (a, b), w in results.items()
            }
            ordered[division] = [
                keys[k]
                for k in legacy_rank_division(
                    list(keys),
                    old_results,
                    dead_counts={
                        players[pid]["ranking_key"]: deaths[pid] for pid in members
                    },
                )
            ]
            offset += len(members)
            continue
        position = 1
        for group in rank_division(members, results, dead_counts=deaths).groups:
            ids = list(group.display_members)
            positions = list(range(position, position + len(ids)))
            signatures = {
                "points": [cfg["scoring_json"][str(offset + i)] for i in positions],
                "coins": [cfg["coin_rewards_json"][str(offset + i)] for i in positions],
                "podium": [offset + i if offset + i <= 3 else None for i in positions],
                "movement": [
                    i > sizes["A"] - moving if division == "A" else i <= moving
                    for i in positions
                ],
                "last_b_reward": [
                    bool(
                        division == "B"
                        and cfg["rules_json"]["last_b_gets_steal"]
                        and i == sizes["B"]
                    )
                    for i in positions
                ],
            }
            effects = [
                name for name, values in signatures.items() if len(set(values)) > 1
            ]
            item = dict(
                division=division,
                player_ids=ids,
                position=offset + position,
                position_end=offset + positions[-1],
                wins=group.wins,
                adjusted_deaths=group.adjusted_deaths,
                consequences=effects,
            )
            if len(ids) > 1:
                review["groups"].append(item)
            group_data.append((item, position))
            position += len(ids)
        offset += len(members)
    if rule == LEGACY_RULE:
        if resolution is not None:
            raise RankingDecisionRequired("INVALID_TIE_RESOLUTION", review)
        return ConsequenceOrder(ordered, {}, dict(rule=rule, groups=[], resolutions=[]))
    required = {
        frozenset(g["player_ids"]): g for g in review["groups"] if g["consequences"]
    }
    decisions = {}
    if resolution is not None:
        if resolution.get("input_hash") != digest:
            raise RankingDecisionRequired("RANKING_REVIEW_STALE", review)
        for decision in resolution.get("orders", []):
            ids = decision["player_ids"]
            key = frozenset(ids)
            reason = decision.get("reason", "").strip()
            if (
                key not in required
                or key in decisions
                or len(set(ids)) != len(ids)
                or not 1 <= len(reason) <= 500
            ):
                raise RankingDecisionRequired("INVALID_TIE_RESOLUTION", review)
            decisions[key] = dict(player_ids=ids, reason=reason)
    if set(decisions) != set(required):
        raise RankingDecisionRequired("RANKING_TIE_UNRESOLVED", review)
    ordered = {"A": [], "B": []}
    for item, div_start in group_data:
        ids = item["player_ids"]
        decision = decisions.get(frozenset(ids))
        allocation = decision["player_ids"] if decision else ids
        neutral = len(ids) > 1 and decision is None
        status = (
            "unresolved_neutral"
            if neutral
            else "externally_resolved"
            if decision
            else "unique"
        )
        for index, pid in enumerate(allocation):
            rows[pid] = dict(
                position=item["position"] if neutral else item["position"] + index,
                division_position=div_start if neutral else div_start + index,
                metadata=dict(
                    ranking_rule=RULE,
                    allocation_position=item["position"] + index,
                    position_end=item["position_end"]
                    if neutral
                    else item["position"] + index,
                    tie_status=status,
                    tie_size=len(ids),
                    wins=item["wins"],
                    adjusted_deaths=item["adjusted_deaths"],
                ),
            )
        ordered[item["division"]].extend(allocation)
        if len(ids) > 1:
            audit_groups.append(dict(item, status=status))
    return ConsequenceOrder(
        ordered,
        rows,
        dict(
            rule=RULE,
            input_hash=digest,
            groups=audit_groups,
            resolutions=[
                decisions[key] for key in sorted(decisions, key=lambda k: sorted(k))
            ],
        ),
    )
