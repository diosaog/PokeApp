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
class SportingGroup:
    wins: int
    adjusted_deaths: int
    # Within a group this is transport order, never a sporting decision.
    display_members: tuple[str, ...]


@dataclass(frozen=True)
class DivisionRanking:
    groups: tuple[SportingGroup, ...]

    def unique_order(self) -> tuple[str, ...]:
        if any(len(group.display_members) != 1 for group in self.groups):
            raise ValueError("Unresolved sporting order")
        return tuple(group.display_members[0] for group in self.groups)


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


def wins_losses(
    players: list[str] | tuple[str, ...], results: MatchResults
) -> dict[str, WinLossRecord]:
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
    key = (
        (player_a, player_b)
        if (player_a, player_b) in results
        else (player_b, player_a)
    )
    winner = results.get(key)
    return winner if winner in {player_a, player_b} else None


def rank_division(
    players: list[str] | tuple[str, ...],
    results: MatchResults,
    *,
    dead_counts: Mapping[str, int],
) -> DivisionRanking:
    """Sporting equivalence classes: wins descending, adjusted deaths ascending.

    The returned object intentionally cannot be sliced as a uniquely ranked list.
    Callers must resolve consequential ties before allocating outcomes.
    """
    if len(set(players)) != len(players):
        raise ValueError("Duplicate participant")
    for player in players:
        value = dead_counts.get(player)
        if type(value) is not int or value < 0:
            raise ValueError(
                "Adjusted deaths must be authoritative nonnegative integers"
            )
    for (a, b), winner in results.items():
        if a == b or a not in players or b not in players or winner not in (a, b):
            raise ValueError("Invalid sporting result")
    records = wins_losses(players, results)
    groups: dict[tuple[int, int], list[str]] = {}
    for player in players:
        groups.setdefault((-records[player].wins, dead_counts[player]), []).append(
            player
        )
    return DivisionRanking(
        tuple(
            SportingGroup(-key[0], key[1], tuple(sorted(members)))
            for key, members in sorted(groups.items())
        )
    )


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
    total = (
        float(base_points)
        - float(dead_penalty_per_mon) * max(0, int(dead_count))
        - float(points_reduction)
    )
    return one_decimal(total)
