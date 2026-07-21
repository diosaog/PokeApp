from __future__ import annotations

import html

from app.common import COIN
from app.entrenadores.trainer_flags import (
    format_trainer_with_flags,
    status_labels_for,
    sync_trainer_robbed_flags_from_history,
)
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
    sync_trainer_robbed_flags_from_history([user for user, _ in table])
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
    sync_trainer_robbed_flags_from_history([user for user, _ in table])
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


def _trainer_status_badges_html(user: str) -> str:
    labels = status_labels_for(user)
    if not labels:
        return ""
    badges: list[str] = []
    for label in labels:
        slug = str(label or "").strip().lower()
        badges.append(
            "<span class='league-trainer-badge "
            f"league-trainer-badge--{html.escape(slug)}'>"
            f"{html.escape(str(label))}"
            "</span>"
        )
    return "<span class='league-trainer-badges'>" + "".join(badges) + "</span>"


def league_table_html(table: list[tuple[str, float]], *, include_coins: bool = False) -> str:
    sync_trainer_robbed_flags_from_history([user for user, _ in table])
    headers = ["Pos", "Jugador", "Puntos"]
    if include_coins:
        headers.append("Monedas")

    head = "".join(f"<th>{html.escape(label)}</th>" for label in headers)
    body_rows: list[str] = []
    for pos, (user, pts) in enumerate(table, start=1):
        safe_user = html.escape(str(user))
        cells = [
            f"<td class='league-table-pos'>{pos}</td>",
            (
                "<td class='league-table-player'>"
                f"<span class='league-player-name'>{safe_user}</span>"
                f"{_trainer_status_badges_html(str(user))}"
                "</td>"
            ),
            f"<td>{html.escape(fmt_points(pts))}</td>",
        ]
        if include_coins:
            cells.append(
                "<td class='league-table-coins'>"
                f"<span>{html.escape(COIN)}</span> {coins_for_user(str(user))}"
                "</td>"
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    body = "".join(body_rows) or (
        f"<tr><td colspan='{len(headers)}' class='league-table-empty'>Sin datos</td></tr>"
    )
    return f"""
<style>
.league-table-shell {{
  width: 100%;
  max-height: 520px;
  overflow: auto;
  border: 1px solid var(--bw2-edge);
  background:
    linear-gradient(120deg, rgba(245,139,60,0.08) 0 22%, transparent 22% 100%),
    #080c12;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 10px 26px rgba(0,0,0,0.24);
}}
.league-status-table {{
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  color: #e9f0f6;
  font-family: var(--font-ui);
  font-size: 18px;
}}
.league-status-table th {{
  position: sticky;
  top: 0;
  z-index: 2;
  height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(216, 223, 232, 0.24);
  border-right: 1px solid rgba(216, 223, 232, 0.14);
  background: linear-gradient(180deg, #252a33 0%, #181d25 100%);
  color: var(--bw2-text-soft);
  font-family: var(--font-pixel);
  font-size: 9px;
  text-align: left;
  font-weight: 400;
  text-transform: uppercase;
}}
.league-status-table td {{
  height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(216, 223, 232, 0.13);
  border-right: 1px solid rgba(216, 223, 232, 0.1);
  background: rgba(12, 16, 22, 0.82);
  vertical-align: middle;
}}
.league-status-table tr:nth-child(even) td {{
  background: rgba(18, 23, 31, 0.82);
}}
.league-status-table tr:last-child td {{
  border-bottom: 0;
}}
.league-status-table th:first-child,
.league-status-table td:first-child {{
  width: 72px;
  text-align: right;
}}
.league-table-player {{
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}}
.league-player-name {{
  color: #ffffff;
  font-family: var(--font-pixel);
  font-size: 10px;
  font-weight: 400;
  white-space: normal;
  overflow-wrap: anywhere;
}}
.league-trainer-badges {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}}
.league-trainer-badge {{
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 8px 3px;
  border: 1px solid rgba(255,255,255,0.18);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 0 0 1px rgba(0,0,0,0.25);
  color: #fff;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0;
  line-height: 1;
  text-transform: uppercase;
}}
.league-trainer-badge--robado {{
  background: linear-gradient(180deg, #7b2632 0%, #4c151f 100%);
  border-color: #d95b6e;
  color: #ffe8ed;
}}
.league-trainer-badge--retirado {{
  background: linear-gradient(180deg, #5b6370 0%, #313842 100%);
  border-color: #9aa5b4;
  color: #f0f3f7;
}}
.league-table-coins {{
  color: #fff4bd;
  font-size: 20px;
  font-weight: 800;
}}
.league-table-empty {{
  color: #8c95a0;
  text-align: center;
}}
</style>
<div class="league-table-shell">
  <table class="league-status-table">
    <thead><tr>{head}</tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>
"""
