"""Consequence review of sporting groups; transport order cannot award a place."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from itertools import combinations

from app.domain.services.league import rank_division
from app.domain.services.legacy_league import legacy_rank_division

RULE = "wins_adjusted_deaths_v1"
LEGACY_RULE = "legacy_pre_10_5d"
NET_RULE = "wins_segment_deaths_v2"
NET_SCORING = "league_net_v1"


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
    if inputs["config"].get("scoring_mode") == NET_SCORING:
        return _net_consequence_order(inputs, matches, rule, resolution)
    players = {p["id"]: p for p in inputs["players"]}
    cfg = inputs["config"]
    single_round_robin = cfg.get("scoring_mode") == "single_round_robin_v1"
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
                "points": [2 * group.wins if single_round_robin else cfg["scoring_json"][str(offset + i)] for i in positions],
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
                "single_league_prize": [
                    "shield" if single_round_robin and i == 1 else
                    "steal" if single_round_robin and i == sizes["A"] else None
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


def _battle_order(decision, ids):
    """Require actual extra 1v1 outcomes for every contested pair.

    A cyclic or incomplete set of results does not establish an order. These
    records are audit evidence only: normal-match wins and points never use it.
    """
    battles = decision.get("battles")
    required = {frozenset(pair) for pair in combinations(ids, 2)}
    seen, audit = set(), []
    if not isinstance(battles, list) or len(battles) != len(required):
        raise ValueError("Missing extra 1v1 evidence")
    positions = {pid: index for index, pid in enumerate(ids)}
    for battle in battles:
        a, b, winner = (battle.get(k) for k in ("player_a_id", "player_b_id", "winner_id"))
        pair = frozenset((a, b))
        evidence = battle.get("evidence", "")
        played = datetime.fromisoformat(battle.get("played_at", "").replace("Z", "+00:00"))
        if (
            pair not in required or pair in seen or winner not in pair
            or not isinstance(evidence, str) or not 1 <= len(evidence.strip()) <= 500
            or played.tzinfo is None or played.utcoffset() is None
            or played > datetime.now(timezone.utc)
        ):
            raise ValueError("Invalid extra 1v1 evidence")
        loser = b if winner == a else a
        if positions[winner] > positions[loser]:
            raise ValueError("Battle results do not establish the requested order")
        seen.add(pair)
        audit.append(dict(battle, evidence=evidence.strip()))
    return sorted(audit, key=lambda b: sorted((b["player_a_id"], b["player_b_id"])))


def _net_consequence_order(inputs, matches, rule, resolution):
    if rule != NET_RULE:
        raise ValueError("New League requires its frozen segment-death ranking rule")
    players = {p["id"]: p for p in inputs["players"]}
    cfg = inputs["config"]
    canonical = dict(
        rule=rule, season_id=inputs["season_id"], day_id=inputs["day_id"],
        number=inputs["number"], results_revision=inputs.get("results_revision"),
        config=cfg,
        players=sorted((dict(p) for p in players.values()), key=lambda p: p["id"]),
        matches=sorted(matches.values(), key=lambda m: m["id"]),
    )
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    review = dict(input_hash=digest, ranking_rule=rule, groups=[])
    global_results = {(m["player_a_id"], m["player_b_id"]): m["winner_id"] for m in matches.values()}
    ranking = rank_division(list(players), global_results,
                            dead_counts={pid: p["segment_deaths"] for pid, p in players.items()})
    sizes = {d: sum(p["division"] == d for p in players.values()) for d in ("A", "B")}
    moving = 0 if inputs["number"] == cfg["total_matchdays"] else min(
        cfg["promotion_relegation_count"], sizes["A"], sizes["B"])
    position, division_offsets, groups = 1, {"A": 0, "B": 0}, []
    for group in ranking.groups:
        ids = list(group.display_members)
        end = position + len(ids) - 1
        effects = []
        if len(ids) > 1:
            if position <= 3:
                effects.append("podium")
            if position == 1 or end == len(players):
                effects.append("matchday_prize")
            for division in ("A", "B"):
                count = sum(players[p]["division"] == division for p in ids)
                boundary = sizes["A"] - moving if division == "A" else moving
                if moving and division_offsets[division] < boundary < division_offsets[division] + count:
                    effects.append("movement")
                    break
        item = dict(division=players[ids[0]]["division"], player_ids=ids,
                    position=position, position_end=end, wins=group.wins,
                    # Compatibility alias; explicitly actual segment deaths here.
                    adjusted_deaths=group.adjusted_deaths,
                    segment_deaths=group.adjusted_deaths, consequences=effects)
        if len(ids) > 1:
            review["groups"].append(item)
        groups.append(item)
        for division in division_offsets:
            division_offsets[division] += sum(players[p]["division"] == division for p in ids)
        position = end + 1
    required = {frozenset(g["player_ids"]): g for g in review["groups"] if g["consequences"]}
    decisions = {}
    if resolution is not None:
        if resolution.get("input_hash") != digest:
            raise RankingDecisionRequired("RANKING_REVIEW_STALE", review)
        for decision in resolution.get("orders", []):
            ids = decision.get("player_ids", [])
            key = frozenset(ids)
            reason = decision.get("reason", "")
            if (key not in required or key in decisions or len(set(ids)) != len(ids)
                or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500):
                raise RankingDecisionRequired("INVALID_TIE_RESOLUTION", review)
            try:
                battles = _battle_order(decision, ids)
            except (ValueError, TypeError, AttributeError, KeyError):
                raise RankingDecisionRequired("INVALID_TIE_RESOLUTION", review) from None
            decisions[key] = dict(player_ids=ids, reason=reason.strip(), battles=battles)
    if set(decisions) != set(required):
        raise RankingDecisionRequired("RANKING_TIE_UNRESOLVED", review)
    ordered, rows, audit = {"A": [], "B": []}, {}, []
    for group in groups:
        ids = group["player_ids"]
        decision = decisions.get(frozenset(ids))
        allocation = decision["player_ids"] if decision else ids
        neutral = len(ids) > 1 and decision is None
        status = "unresolved_neutral" if neutral else "externally_resolved" if decision else "unique"
        starts = {d: len(ordered[d]) + 1 for d in ordered}
        for index, pid in enumerate(allocation):
            division = players[pid]["division"]
            division_position = starts[division] if neutral else len(ordered[division]) + 1
            rows[pid] = dict(position=group["position"] if neutral else group["position"] + index,
                division_position=division_position,
                metadata=dict(ranking_rule=rule, allocation_position=group["position"] + index,
                    position_end=group["position_end"] if neutral else group["position"] + index,
                    tie_status=status, tie_size=len(ids), wins=group["wins"],
                    losses=sum(m["winner_id"] != pid and pid in (m["player_a_id"], m["player_b_id"])
                               for m in matches.values()),
                    actual_segment_deaths=group["segment_deaths"]))
            ordered[division].append(pid)
        if len(ids) > 1:
            audit.append(dict(group, status=status))
    return ConsequenceOrder(ordered, rows, dict(rule=rule, input_hash=digest, groups=audit,
        resolutions=[decisions[key] for key in sorted(decisions, key=lambda k: sorted(k))]))
