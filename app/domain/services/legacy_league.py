"""Frozen pre-D ordering, only for V1 and explicit corrections of old snapshots."""

from typing import Mapping
from app.domain.services.league import MatchResults, wins_losses, head_to_head


def legacy_rank_division(
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
        ranking.extend(
            sorted(group, key=lambda player: (int(dead.get(player, 0)), player))
        )
    return ranking
