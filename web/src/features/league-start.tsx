import { Skull } from "lucide-react";
import { api } from "../api/client";
import type { Model } from "../api/types";
import { queries, useApp, useRead } from "../state";

// 079: the League starts from the League itself. Any active participant
// prepares and opens J1 (everyone against everyone), and each trainer
// gets points from observed death history automatically. Administración keeps only the
// exceptional cases (corrections, pre-tracking deaths, broken evidence).

export type Readiness = Model<"LeagueReadinessRead">;
type ReadinessReason = Readiness["reasons"][number];
type TrainerReason = Readiness["participants"][number]["reasons"][number];
type OwnDeaths = Model<"OwnDeathHistoryRead">;

export const readinessPath = (season: string) =>
  `/v1/seasons/${season}/league/readiness`;
export const ownDeathPath = (season: string) =>
  `/v1/seasons/${season}/death-history`;

export function useReadiness(enabled = true) {
  const { season } = useApp();
  return useRead<Readiness>(readinessPath(season), !!season && enabled);
}

const seasonText: Record<ReadinessReason, string> = {
  season_not_active: "La Liga no está en curso.",
  matchday_unavailable:
    "La jornada actual no está disponible. Avisa a un administrador.",
  matchday_already_prepared: "La primera jornada ya está preparada.",
  initial_assignment_required:
    "Esta temporada se juega en Liga A y Liga B: su reparto inicial lo confirma Administración.",
  initial_setup_locked:
    "La preparación inicial tiene datos incompletos. Avisa a un administrador.",
  invalid_roster:
    "Hay participantes retirados o cuentas desactivadas en la plantilla.",
  opponent_missing: "Hacen falta al menos dos participantes.",
  config_not_effective:
    "La configuración de la Liga no corresponde a la plantilla actual. Avisa a un administrador.",
};
export const readinessText = (code: ReadinessReason) => seasonText[code];

// Third person for the others, second person for the viewer.
const trainerText: Record<TrainerReason, [string, string]> = {
  trainer_disabled: [
    "su cuenta está desactivada",
    "tu cuenta está desactivada",
  ],
  save_missing: [
    "falta registrar su partida oficial desde PokeApp Launcher",
    "registra tu partida oficial: abre PokeApp Launcher y sincronízala",
  ],
  progress_unobserved: [
    "su partida aún no muestra el progreso de medallas; debe volver a sincronizar",
    "tu partida aún no muestra tu progreso de medallas; vuelve a sincronizar",
  ],
  badges_missing: [
    "necesita las dos primeras medallas para la J1",
    "necesitas las dos primeras medallas para la J1",
  ],
  death_history_baseline_required: [
    "falta una lectura válida de su historial de muertes",
    "falta una lectura válida de tu historial de muertes",
  ],
  death_history_wipe_reconciliation_required: [
    "su contador de revividos tras wipe no coincide con el historial observado",
    "tu contador de revividos tras wipe no coincide con el historial observado",
  ],
  death_history_source_unavailable: [
    "su partida no permite leer la caja de muertos; debe volver a sincronizar",
    "tu partida no permite leer la caja de muertos; vuelve a sincronizar",
  ],
  death_history_wipe_state_unavailable: [
    "no se puede verificar su contador de revividos tras wipe (lo revisa Administración)",
    "no se puede verificar tu contador de revividos tras wipe (lo revisa Administración)",
  ],
  death_history_dead_box_changed: [
    "cambió su caja de muertos (Administración revisa su historial)",
    "cambió tu caja de muertos (Administración revisa tu historial)",
  ],
  death_history_observation_gap: [
    "su historial tiene un intervalo sin evidencia (lo revisa Administración)",
    "tu historial tiene un intervalo sin evidencia (lo revisa Administración)",
  ],
  death_history_unmapped_revival: [
    "tiene un revivir sin identidad de Pokémon (lo revisa Administración)",
    "tienes un revivir sin identidad de Pokémon (lo revisa Administración)",
  ],
  death_history_inconsistent: [
    "sus recuentos de muertes no cuadran (lo revisa Administración)",
    "tus recuentos de muertes no cuadran (lo revisa Administración)",
  ],
};
export const trainerReasonText = (code: TrainerReason, own: boolean) =>
  trainerText[code][own ? 1 : 0];

/**
 * Prepares J1 of an all-vs-all League (idempotent by state: whoever did it
 * first, the answer is the same J1). Returns the matchday to act on.
 */
export async function prepareFirstMatchday(season: string) {
  const result = await api.command<Model<"FirstMatchdayRead">>(
    `/v1/seasons/${season}/league/first-matchday`,
    {},
    crypto.randomUUID(),
  );
  await queries.invalidateQueries({
    predicate: (q) =>
      new RegExp(
        `/seasons/${season}/(league|overview|matchdays|team-preview|scouting|death-history|setup|shop|initial-assignment)`,
      ).test(String(q.queryKey[1])),
  });
  return result;
}

/** Read-only source diagnostics. Observed points never need player confirmation. */
export function OwnDeathHistory({ inline = false }: { inline?: boolean }) {
  const { season } = useApp();
  const query = useRead<OwnDeaths>(ownDeathPath(season), !!season);
  const data = query.data;
  if (
    inline ||
    !data ||
    data.known ||
    data.confirm_blocker === "death_history_closed"
  )
    return null;
  const message =
    data.confirm_blocker === "death_history_admin_required"
      ? "La evidencia de tu historial es inconsistente o incompleta. Administración debe revisar ese caso."
      : data.confirm_blocker === "death_history_pending_sync"
        ? "Tu última sincronización todavía se está incorporando."
        : "Sincroniza tu partida oficial desde PokeApp Launcher para disponer de una lectura válida.";
  return (
    <section className="own-death-history" aria-labelledby="own-death-title">
      <h2 id="own-death-title">
        <Skull size={17} aria-hidden="true" /> Historial de muertes de la Liga
      </h2>
      <p>
        Los puntos se calculan automáticamente con la partida oficial y los
        registros de la Liga.
      </p>
      <p className="muted">{message}</p>
    </section>
  );
}
