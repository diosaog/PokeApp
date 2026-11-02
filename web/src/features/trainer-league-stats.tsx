import { ApiError, errorText } from "../api/client";
import type { Model } from "../api/types";
import { StatPill } from "../pokemon/presentation";
import { points } from "./core";

const historyReasons = new Set([
  "death_history_baseline_required",
  "death_history_source_unavailable",
  "death_history_source_changed",
  "death_history_observation_gap",
  "death_history_dead_box_changed",
  "death_history_wipe_reconciliation_required",
  "death_history_wipe_state_unavailable",
  "death_history_unmapped_revival",
  "death_history_revision_conflict",
  "death_history_inconsistent",
  "death_history_start_unproven",
]);

// Cards and profiles use the same League evidence. Current dead-box occupancy
// and personal-save progress cannot substitute for permanent death history.
export function TrainerLeagueStats({
  row,
}: {
  row?: Model<"LeagueStandingRead">;
}) {
  const knownDeaths =
    row?.historical_deaths_status === "known" && row.historical_deaths != null;
  const historyReason = row?.historical_deaths_source;
  const unlinked = row?.league_save_status === "unlinked";
  return (
    <>
      <div className="mini-stats">
        <StatPill
          label="Puntos netos"
          value={row?.total_points == null ? "—" : points(row.total_points)}
        />
        <StatPill label="Monedas" value={row?.coin_balance} />
        <StatPill
          label="Muertes históricas"
          value={knownDeaths ? row.historical_deaths : "—"}
        />
      </div>
      <p className="caption">
        Liga seleccionada: puntos netos, saldo disponible y muertes históricas.
      </p>
      {unlinked && (
        <p className="caption">
          Sin partida vinculada a esta Liga. El entrenador debe seleccionar esta
          Liga y sincronizar su partida original desde su propio Launcher; el
          progreso personal no acredita premios ni muertes de Liga.
        </p>
      )}
      {row?.league_save_status === "unavailable" && (
        <p className="caption">
          No se ha podido comprobar la vinculación de la partida a esta Liga.
        </p>
      )}
      {row && !knownDeaths && !unlinked && (
        <p className="caption">
          {row.historical_deaths != null &&
            `${row.historical_deaths} muertes registradas; total sin confirmar. `}
          {historyReason && historyReasons.has(historyReason)
            ? errorText(new ApiError(409, historyReason))
            : "Historial de muertes pendiente de confirmar en la Liga."}
        </p>
      )}
      {row?.total_points == null && row && (
        <p className="caption">Puntos netos pendientes de confirmar.</p>
      )}
    </>
  );
}
