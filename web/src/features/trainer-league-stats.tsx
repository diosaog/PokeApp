import type { Model } from "../api/types";
import { StatPill } from "../pokemon/presentation";
import { points } from "./core";

export function TrainerLeagueStats({
  row,
}: {
  row?: Model<"LeagueStandingRead">;
}) {
  return (
    <div className="mini-stats">
      <StatPill
        label="Puntos"
        value={row?.total_points == null ? "—" : points(row.total_points)}
      />
      <StatPill label="Monedas" value={row?.coin_balance} />
      <StatPill label="Muertos" value={row?.dead_count} />
    </div>
  );
}
