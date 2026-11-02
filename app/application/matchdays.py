"""Pure close planning; SQL rechecks the input fingerprint under mutation locks."""

from dataclasses import asdict
from decimal import Decimal, InvalidOperation, localcontext
from itertools import combinations
import random

from app.application.daily_ranking import NET_RULE, NET_SCORING, RULE, consequence_order
from app.domain.league import PenaltySummary
from app.domain.seasons import SeasonRules, SeasonVersion
from app.domain.services.league import calculate_division_movements, last_b_steal_award
from app.domain.services.rewards import build_standings_from_rankings
from app.domain.services.shop import discount_price, select_shop_promotions


def plan_close(
    context: dict,
    corrections: list[dict] | None = None,
    tie_resolution: dict | None = None,
) -> dict:
    inputs = context["inputs"]
    cfg = inputs["config"]
    net_league = cfg.get("scoring_mode") == NET_SCORING
    single_round_robin = cfg.get("scoring_mode") == "single_round_robin_v1"
    death_rate = Decimal(str(cfg.get("death_penalty_per_mon", "0.2")))
    common_coins = None
    if single_round_robin or net_league:
        rewards = set(cfg["coin_rewards_json"].values())
        if (len(rewards) != 1 or (single_round_robin and
            (cfg["total_matchdays"] != 1 or set(cfg["division_sizes"]) != {"A"}))):
            raise ValueError("League requires one common configured coin reward")
        common_coins = next(iter(rewards))
    players = {p["id"]: p for p in inputs["players"]}
    matches = {m["id"]: dict(m) for m in inputs["matches"]}
    for change in corrections or []:
        match = matches[change["match_id"]]
        winner = change["winner_season_player_id"]
        if winner not in (match["player_a_id"], match["player_b_id"]):
            raise ValueError("Invalid corrected winner")
        match["winner_id"] = winner
    for match in matches.values():
        if match["winner_id"] not in (match["player_a_id"], match["player_b_id"]):
            raise ValueError("Incomplete results")
    if net_league:
        _validate_net_inputs(inputs, players, matches)
    ordering = consequence_order(
        inputs, matches, context.get("ranking_rule", NET_RULE if net_league else RULE), tie_resolution
    )
    ranks = ordering.allocations
    version = SeasonVersion(
        id=cfg["id"],
        season_id=inputs["season_id"],
        name=cfg["name"],
        effective_matchday=cfg["effective_from_matchday"],
        max_matchdays=cfg["total_matchdays"],
        participant_ids=tuple(players),
        # One league has no B: its config is division_sizes {A}.
        division_sizes=tuple(
            cfg["division_sizes"][d] for d in ("A", "B") if d in cfg["division_sizes"]
        ),
        promotion_relegation_count=cfg["promotion_relegation_count"],
        points_by_position={int(k): v for k, v in cfg["scoring_json"].items()},
        coins_by_position={int(k): v for k, v in cfg["coin_rewards_json"].items()},
        # Persisted configuration also carries prospective progress rewards.
        # The sporting planner consumes only its two League rules; progress
        # settlement remains owned by the observed-save reward service.
        rules=SeasonRules(
            team_lock_required=cfg["rules_json"]["team_lock_required"],
            last_b_gets_steal=cfg["rules_json"]["last_b_gets_steal"],
        ),
    )
    penalties = {
        p["id"]: PenaltySummary(
            dead_count=p["dead_count"],
            dead_points_penalty=0 if net_league else float(death_rate * p["dead_count"]),
            points_reduction=0 if net_league else p["points_reduction"],
            coins_reduction=p["coins_reduction"],
        )
        for p in players.values()
    }
    standings = [
        asdict(s)
        for s in build_standings_from_rankings(
            matchday_id=inputs["day_id"],
            rank_a=ranks["A"],
            rank_b=ranks["B"],
            version=version,
            penalties_by_trainer=penalties,
        )
    ]
    # V2 SQL supplies decimal sanctions as text to preserve arbitrary cumulative
    # precision through JSON. Rewards and the legacy domain remain unchanged.
    for standing in standings:
        if standing["trainer_id"] in ordering.sporting_rows:
            standing.update(ordering.sporting_rows[standing["trainer_id"]])
        if single_round_robin:
            standing["points_awarded"] = 2 * sum(
                m["winner_id"] == standing["trainer_id"] for m in matches.values()
            )
            standing["coins_awarded"] = common_coins
        elif net_league:
            player = players[standing["trainer_id"]]
            wins = standing["metadata"]["wins"]
            units = player["death_penalty_tenths"]
            previous_units = player["prior_death_penalty_tenths"]
            sanction = Decimal(str(player["points_reduction"]))
            previous_sanction = Decimal(str(player["prior_points_reduction"]))
            # Serialize exact decimal text; old domain floats never participate
            # in the new contract's arithmetic or cumulative reconciliation.
            death_penalty = Decimal(f"{units}e-1")
            previous_death_penalty = Decimal(f"{previous_units}e-1")
            values = (death_penalty, previous_death_penalty, sanction, previous_sanction, Decimal(wins))
            # SQL numeric sanctions are not limited to binary-float precision
            # or Decimal's process-wide 28-digit default context.
            with localcontext() as exact:
                exact.prec = max(1, max(v.adjusted() for v in values)
                                 - min(v.as_tuple().exponent for v in values) + 5)
                contribution_penalty = death_penalty - previous_death_penalty + sanction - previous_sanction
                contribution = Decimal(wins) - contribution_penalty
            standing["points_awarded"] = wins
            standing["coins_awarded"] = common_coins
            standing["score"] = str(contribution)
            standing["penalties"].update(dead_points_penalty=str(death_penalty),
                                         points_reduction=str(sanction))
            standing["metadata"].update(
                actual_deaths=player["actual_deaths"], wipe_deaths=player["wipe_deaths"],
                death_penalty_tenths=units, death_snapshot_id=player["death_snapshot_id"],
                prior_death_penalty_tenths=previous_units,
                prior_points_reduction=str(previous_sanction),
                point_penalties=str(contribution_penalty),
                net_points=str(contribution),
            )
        value = players[standing["trainer_id"]]["points_reduction"]
        if isinstance(value, str):
            standing["penalties"]["points_reduction"] = value
    final = inputs["number"] == cfg["total_matchdays"]
    movement = calculate_division_movements(
        ranks["A"], ranks["B"], 0 if final else cfg["promotion_relegation_count"]
    )
    award = None if net_league else last_b_steal_award(
        ranks["B"], enabled=cfg["rules_json"]["last_b_gets_steal"]
    )
    promotions = []
    if not final and not context["existing_next_promotions"] and corrections is None:
        catalog = {}
        for item in context["catalog"]:
            if item["enabled"]:
                catalog.setdefault(item["category"], []).append(
                    dict(item, price=item["base_price"])
                )
        counts = {}
        purchased = set()
        for purchase in context["purchase_history"]:
            purchased.add(purchase["name"])
            round_counts = counts.setdefault(purchase["number"], {})
            round_counts[purchase["name"]] = (
                round_counts.get(purchase["name"], 0) + purchase["quantity"]
            )
        if award:
            purchased.add(
                next(
                    i["name"]
                    for i in context["catalog"]
                    if i["code"] == "robar_pokemon"
                )
            )
        # Stable server seed makes a recomputed plan reproducible; no client RNG.
        selected = select_shop_promotions(
            catalog,
            closed_round=inputs["number"],
            purchase_counts=counts,
            discount_history=context["promotion_history"],
            purchased_items=purchased,
            rng=random.Random(inputs["day_id"]),
        )
        for item in selected:
            price = discount_price(
                item["base_price"], item["discount_kind"], item=item["name"]
            )
            if price < item["base_price"]:
                promotions.append(
                    dict(
                        shop_item_id=item["id"],
                        promotion_type=item["discount_kind"],
                        base_price=item["base_price"],
                        effective_price=price,
                        stock_total=1 if item["discount_kind"] == "mega" else 2,
                    )
                )
    result = dict(
        ranking=ordering.audit,
        standings=standings,
        matches=list(matches.values()),
        new_divisions={"A": list(movement.new_a), "B": list(movement.new_b)},
        last_b_player_id=award.trainer_id if award else None,
        promotions=promotions,
    )
    if single_round_robin or net_league:
        global_order = sorted(standings, key=lambda s: s["metadata"]["allocation_position"]) if net_league else []
        first = global_order[0]["trainer_id"] if net_league else ranks["A"][0]
        last = global_order[-1]["trainer_id"] if net_league else ranks["A"][-1]
        result["single_league_rewards"] = [
            dict(code="blindar_pokemon", season_player_id=first),
            dict(code="robar_pokemon", season_player_id=last),
        ]
        if net_league:
            for standing in standings:
                standing["metadata"]["placement_rewards"] = [
                    reward["code"] for reward in result["single_league_rewards"]
                    if reward["season_player_id"] == standing["trainer_id"]
                ]
    return result


def _validate_net_inputs(inputs, players, matches):
    """Missing history is unknown, never an inferred zero or penalty counter."""
    if len(players) != len(inputs["players"]) or len(players) < 2:
        raise ValueError("Invalid League roster")
    expected = {frozenset(pair) for pair in combinations(players, 2)}
    actual = [frozenset((m["player_a_id"], m["player_b_id"])) for m in matches.values()]
    if len(matches) != len(inputs["matches"]) or len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("League requires the complete global round robin")
    cfg = inputs["config"]
    if (set(cfg["coin_rewards_json"]) != {str(i) for i in range(1, len(players) + 1)}
        or any(type(v) is not int or v < 0 for v in cfg["coin_rewards_json"].values())):
        raise ValueError("Invalid common configured coin reward")
    if cfg.get("death_penalty_per_mon") != "0.1":
        raise ValueError("Official ordinary-death rate must be 0.1")
    for player in players.values():
        fields = ("actual_deaths", "wipe_deaths", "segment_deaths", "death_penalty_tenths",
                  "prior_death_penalty_tenths")
        if any(type(player.get(k)) is not int or player[k] < 0 for k in fields):
            raise ValueError("Authoritative historical death evidence is required")
        if (player["wipe_deaths"] > player["actual_deaths"]
            or player["segment_deaths"] > player["actual_deaths"]
            or player["death_penalty_tenths"] != player["actual_deaths"] + player["wipe_deaths"]
            or player.get("dead_count") != player["death_penalty_tenths"]
            or not isinstance(player.get("death_snapshot_id"), str)
            or not player["death_snapshot_id"]
            or player.get("division") not in ("A", "B")):
            raise ValueError("Inconsistent historical death evidence")
        for field in ("points_reduction", "prior_points_reduction"):
            try:
                value = Decimal(str(player[field]))
            except InvalidOperation:
                raise ValueError("Invalid cumulative sanction") from None
            if not value.is_finite() or value < 0:
                raise ValueError("Invalid cumulative sanction")
