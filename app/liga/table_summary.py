from __future__ import annotations

from app.common import COIN
from app.tienda.money import _money_available


def players_from_match_map(md: dict[tuple[str, str], str | None]) -> list[str]:
    out: list[str] = []
    for p1, p2 in md.keys():
        if p1 and p1 not in out:
            out.append(p1)
        if p2 and p2 not in out:
            out.append(p2)
    return out


def coins_for_user(user: str) -> int:
    try:
        return int(_money_available(user))
    except Exception:
        return 0


def fmt_points(value) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "0.0"


def league_table_notification_rows(table: list[tuple[str, float]]) -> list[dict]:
    return [
        {
            "pos": i,
            "user": user,
            "points": fmt_points(pts),
            "coins": coins_for_user(user),
        }
        for i, (user, pts) in enumerate(table, start=1)
    ]


def league_table_rows(table: list[tuple[str, float]], *, include_coins: bool = False) -> list[dict]:
    rows: list[dict] = []
    for i, (user, pts) in enumerate(table, start=1):
        row = {"Pos": i, "Jugador": user, "Puntos": fmt_points(pts)}
        if include_coins:
            row["Monedas"] = f"{COIN} {coins_for_user(user)}"
        rows.append(row)
    return rows
