import type { Model } from "../api/types";
import { StatPill } from "../pokemon/presentation";
import { pointsOr } from "../points";

/**
 * Owner 2026-11-19: «Muertos» is the Locke's total deaths, the same count the
 * −0,1 penalty uses: a revived Pokémon stays counted. The current dead-box
 * occupancy (which drops on a revive) is shown only while that total is not
 * known, and an unreadable count stays unknown.
 */
export function totalDeaths(
  row?: Pick<
    Model<"LeagueStandingRead">,
    "dead_count" | "historical_deaths" | "historical_deaths_status"
  > | null,
) {
  if (!row) return undefined;
  return row.historical_deaths_status === "known" &&
    row.historical_deaths != null
    ? row.historical_deaths
    : row.dead_count;
}

export function TrainerLeagueStats({
  row,
}: {
  row?: Model<"LeagueStandingRead">;
}) {
  return (
    <div className="mini-stats">
      <StatPill label="Puntos" value={pointsOr(row?.total_points)} />
      <StatPill label="Monedas" value={row?.coin_balance} />
      <StatPill label="Muertos" value={totalDeaths(row)} />
    </div>
  );
}
