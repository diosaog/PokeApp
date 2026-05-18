from __future__ import annotations

PLAYER_JOIN_ROUND = {
    "Barto": 2,
}


def counts_for_league_reward(user: str, tramo: int) -> bool:
    join_round = PLAYER_JOIN_ROUND.get(str(user), 1)
    return int(tramo) >= int(join_round)
