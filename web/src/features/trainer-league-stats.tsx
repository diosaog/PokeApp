import type { Model } from "../api/types";
import { StatPill } from "../pokemon/presentation";
import { pointsOr } from "../points";

export function TrainerLeagueStats({
  row,
}: {
  row?: Model<"LeagueStandingRead">;
}) {
  return (
    <div className="mini-stats">
      <StatPill label="Puntos" value={pointsOr(row?.total_points)} />
      <StatPill label="Monedas" value={row?.coin_balance} />
      <StatPill label="Muertos" value={row?.dead_count} />
    </div>
  );
}
