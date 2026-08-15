from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


MatchResults = Mapping[tuple[str, str], str | None]


@dataclass(frozen=True)
class WinLossRecord:
    wins: int = 0
    losses: int = 0


@dataclass(frozen=True)
class DivisionMovement:
    new_a: tuple[str, ...]
    new_b: tuple[str, ...]
    promoted: tuple[str, ...]
    relegated: tuple[str, ...]


@dataclass(frozen=True)
class AwardInstruction:
    trainer_id: str
    item_name: str
    price: int = 0
    reason: str = ""


def one_decimal(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP))


def generate_pairs(players: list[str] | tuple[str, ...]) -> list[tuple[str, str]]:
    clean = [str(player) for player in players]
    return [
        (clean[i], clean[j])
        for i in range(len(clean))
        for j in range(i + 1, len(clean))
    ]


def sync_match_map(
    players: list[str] | tuple[str, ...],
    existing: MatchResults | None,
) -> dict[tuple[str, str], str | None]:
    source = existing or {}
    synced: dict[tuple[str, str], str | None] = {}
    for pair in generate_pairs(players):
        reversed_pair = (pair[1], pair[0])
        synced[pair] = source.get(pair, source.get(reversed_pair))
    return synced


def players_from_matches(results: MatchResults) -> list[str]:
    players: list[str] = []
    for player_a, player_b in results.keys():
        if player_a and player_a not in players:
            players.append(player_a)
        if player_b and player_b not in players:
            players.append(player_b)
    return players


def all_matches_filled(results: MatchResults) -> bool:
    return all(winner is not None for winner in results.values())


def wins_losses(players: list[str] | tuple[str, ...], results: MatchResults) -> dict[str, WinLossRecord]:
    raw = {str(player): {"wins": 0, "losses": 0} for player in players}
    for (player_a, player_b), winner in results.items():
        if winner is None or winner not in raw:
            continue
        loser = player_b if winner == player_a else player_a
        if loser not in raw:
            continue
        raw[winner]["wins"] += 1
        raw[loser]["losses"] += 1
    return {
        player: WinLossRecord(wins=data["wins"], losses=data["losses"])
        for player, data in raw.items()
    }


def head_to_head(player_a: str, player_b: str, results: MatchResults) -> str | None:
    key = (player_a, player_b) if (player_a, player_b) in results else (player_b, player_a)
    winner = results.get(key)
    return winner if winner in {player_a, player_b} else None


def rank_division(
    players: list[str] | tuple[str, ...],
    results: MatchResults,
    *,
    dead_counts: Mapping[str, int] | None = None,
) -> list[str]:
    records = wins_losses(players, results)
    groups: dict[int, list[str]] = {}
    for player in players:
        groups.setdefault(records[str(player)].wins, []).append(str(player))

    ranking: list[str] = []
    dead = dead_counts or {}
    for wins in sorted(groups.keys(), reverse=True):
        group = groups[wins]
        if len(group) == 1:
            ranking.extend(group)
            continue
        if len(group) == 2:
            first, second = group
            winner = head_to_head(first, second, results)
            if winner is not None:
                ranking.extend([winner, second if winner == first else first])
            else:
                ranking.extend(sorted(group))
            continue
        ranking.extend(sorted(group, key=lambda player: (int(dead.get(player, 0)), player)))
    return ranking


def calculate_division_movements(
    rank_a: list[str] | tuple[str, ...],
    rank_b: list[str] | tuple[str, ...],
    movement_count: int,
) -> DivisionMovement:
    count = min(max(0, int(movement_count)), len(rank_a), len(rank_b))
    stay_a_count = max(len(rank_a) - count, 0)
    promoted = tuple(rank_b[:count])
    relegated = tuple(rank_a[stay_a_count:])
    return DivisionMovement(
        new_a=tuple(rank_a[:stay_a_count]) + promoted,
        new_b=relegated + tuple(rank_b[count:]),
        promoted=promoted,
        relegated=relegated,
    )


def last_b_steal_award(
    rank_b: list[str] | tuple[str, ...],
    *,
    enabled: bool,
    item_name: str = "Robar Pokemon",
) -> AwardInstruction | None:
    if not enabled or not rank_b:
        return None
    return AwardInstruction(
        trainer_id=str(rank_b[-1]),
        item_name=str(item_name),
        price=0,
        reason="last_b_gets_steal",
    )


def total_points_with_penalties(
    base_points: float,
    *,
    dead_count: int = 0,
    points_reduction: float = 0.0,
    dead_penalty_per_mon: float = 0.2,
) -> float:
    total = float(base_points) - float(dead_penalty_per_mon) * max(0, int(dead_count)) - float(points_reduction)
    return one_decimal(total)
