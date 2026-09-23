"""Pure close planning; SQL rechecks the input fingerprint under mutation locks."""
from dataclasses import asdict
import random

from app.domain.league import PenaltySummary
from app.domain.seasons import SeasonRules, SeasonVersion
from app.domain.services.league import calculate_division_movements, last_b_steal_award, rank_division
from app.domain.services.rewards import build_standings_from_rankings
from app.domain.services.shop import discount_price, select_shop_promotions


def plan_close(context: dict, corrections: list[dict] | None = None) -> dict:
    inputs = context["inputs"]
    cfg = inputs["config"]
    players = {p["id"]: p for p in inputs["players"]}
    keys = {p["ranking_key"]: p["id"] for p in players.values()}
    if len(keys) != len(players):
        raise ValueError("Non-unique ranking identity")
    matches = {m["id"]: dict(m) for m in inputs["matches"]}
    for change in corrections or []:
        match = matches[change["match_id"]]
        winner = change["winner_season_player_id"]
        if winner not in (match["player_a_id"], match["player_b_id"]):
            raise ValueError("Invalid corrected winner")
        match["winner_id"] = winner
    ranks = {}
    for division in ("A", "B"):
        members = [p for p in players.values() if p["division"] == division]
        results = {}
        for match in matches.values():
            if match["division"] != division:
                continue
            winner = match["winner_id"]
            if winner not in (match["player_a_id"], match["player_b_id"]):
                raise ValueError("Incomplete results")
            results[(players[match["player_a_id"]]["ranking_key"], players[match["player_b_id"]]["ranking_key"])] = players[winner]["ranking_key"]
        ranks[division] = [keys[k] for k in rank_division(
            [p["ranking_key"] for p in members], results,
            dead_counts={p["ranking_key"]: p["dead_count"] for p in members})]
    version = SeasonVersion(id=cfg["id"], season_id=inputs["season_id"], name=cfg["name"],
        effective_matchday=cfg["effective_from_matchday"], max_matchdays=cfg["total_matchdays"],
        participant_ids=tuple(players), division_sizes=tuple(cfg["division_sizes"][d] for d in ("A", "B")),
        promotion_relegation_count=cfg["promotion_relegation_count"],
        points_by_position={int(k): v for k, v in cfg["scoring_json"].items()},
        coins_by_position={int(k): v for k, v in cfg["coin_rewards_json"].items()},
        rules=SeasonRules(**cfg["rules_json"]))
    penalties = {p["id"]: PenaltySummary(dead_count=p["dead_count"], dead_points_penalty=round(.2*p["dead_count"], 1),
        points_reduction=p["points_reduction"], coins_reduction=p["coins_reduction"]) for p in players.values()}
    standings = [asdict(s) for s in build_standings_from_rankings(matchday_id=inputs["day_id"],
        rank_a=ranks["A"], rank_b=ranks["B"], version=version, penalties_by_trainer=penalties)]
    final = inputs["number"] == cfg["total_matchdays"]
    movement = calculate_division_movements(ranks["A"], ranks["B"], 0 if final else cfg["promotion_relegation_count"])
    award = last_b_steal_award(ranks["B"], enabled=cfg["rules_json"]["last_b_gets_steal"])
    promotions = []
    if not final and not context["existing_next_promotions"] and corrections is None:
        catalog = {}
        for item in context["catalog"]:
            if item["enabled"]:
                catalog.setdefault(item["category"], []).append(dict(item, price=item["base_price"]))
        counts = {}
        purchased = set()
        for purchase in context["purchase_history"]:
            purchased.add(purchase["name"])
            round_counts = counts.setdefault(purchase["number"], {})
            round_counts[purchase["name"]] = round_counts.get(purchase["name"], 0) + purchase["quantity"]
        if award:
            purchased.add(next(i["name"] for i in context["catalog"] if i["code"] == "robar_pokemon"))
        # Stable server seed makes a recomputed plan reproducible; no client RNG.
        selected = select_shop_promotions(catalog, closed_round=inputs["number"], purchase_counts=counts,
            discount_history=context["promotion_history"], purchased_items=purchased,
            rng=random.Random(inputs["day_id"]))
        for item in selected:
            price = discount_price(item["base_price"], item["discount_kind"], item=item["name"])
            if price < item["base_price"]:
                promotions.append(dict(shop_item_id=item["id"], promotion_type=item["discount_kind"],
                    base_price=item["base_price"], effective_price=price, stock_total=1 if item["discount_kind"] == "mega" else 2))
    return dict(standings=standings, matches=list(matches.values()), new_divisions={"A":list(movement.new_a), "B":list(movement.new_b)},
        last_b_player_id=award.trainer_id if award else None, promotions=promotions)
