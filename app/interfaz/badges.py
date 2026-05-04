from __future__ import annotations

from app.entrenadores.badges import count_badges


def coins_from_badges(sav_json: dict) -> int:
    """Count badges (max 8) and return coins: 4 per badge."""
    return int(count_badges(sav_json)) * 4
