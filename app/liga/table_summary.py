from __future__ import annotations

from app.common import COIN
from app.entrenadores.trainer_flags import format_trainer_with_flags
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
            "user": format_trainer_with_flags(user),
            "points": fmt_points(pts),
            "coins": coins_for_user(user),
        }
        for i, (user, pts) in enumerate(table, start=1)
    ]


def league_round_result_groups(round_data: dict) -> list[dict]:
    groups: list[dict] = []
    for div_key, div_label in (("A", "Liga A"), ("B", "Liga B")):
        lines: list[str] = []
        for (p1, p2), winner in (round_data.get(div_key, {}) or {}).items():
            if winner in (p1, p2):
                loser = p2 if winner == p1 else p1
                lines.append(f"{winner} gano a {loser}")
            else:
                lines.append(f"{p1} vs {p2}: sin resultado")
        if lines:
            groups.append({"division": div_label, "lines": lines})
    return groups


def league_round_summary_lines(
    *,
    table: list[tuple[str, float]],
    movements: dict | None = None,
    podium: list[tuple[str, float]] | None = None,
) -> list[str]:
    lines: list[str] = []
    if podium:
        labels = ["Ganador", "Segundo puesto", "Tercer puesto"]
        for idx, (user, pts) in enumerate(podium[:3]):
            label = labels[idx] if idx < len(labels) else f"Puesto {idx + 1}"
            lines.append(f"{label}: {user} ({fmt_points(pts)} pts)")
        return lines

    top = table[:3]
    if top:
        top_label = " | ".join(
            f"{idx}. {user} ({fmt_points(pts)} pts)"
            for idx, (user, pts) in enumerate(top, start=1)
        )
        lines.append(f"Top general: {top_label}")

    movements = movements or {}
    up = [str(u) for u in movements.get("up") or [] if u]
    down = [str(u) for u in movements.get("down") or [] if u]
    if up:
        lines.append(f"Suben a Liga A: {', '.join(up)}")
    if down:
        lines.append(f"Bajan a Liga B: {', '.join(down)}")
    return lines


def league_table_rows(table: list[tuple[str, float]], *, include_coins: bool = False) -> list[dict]:
    rows: list[dict] = []
    for i, (user, pts) in enumerate(table, start=1):
        row = {
            "Pos": i,
            "Jugador": format_trainer_with_flags(user),
            "Puntos": fmt_points(pts),
        }
        if include_coins:
            row["Monedas"] = f"{COIN} {coins_for_user(user)}"
        rows.append(row)
    return rows
