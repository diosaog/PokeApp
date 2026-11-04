import { useEffect, useState } from "react";
import { ShieldCheck, Skull } from "lucide-react";
import { api } from "../api/client";
import type { Model } from "../api/types";
import { queries, useApp, useRead } from "../state";
import { CommandState, Modal, useCommand } from "../ui";

// 079: the League starts from the League itself. Any active participant
// prepares and opens J1 (everyone against everyone), and each trainer
// confirms their own observed death history. Administración keeps only the
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
    "falta que confirme su historial de muertes",
    "confirma tu historial de muertes",
  ],
  death_history_wipe_reconciliation_required: [
    "cambió su contador de revividos tras wipe: falta que lo confirme",
    "cambiaste tu contador de revividos tras wipe: confírmalo",
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

const countLine = (c: Model<"DeathCounts">) => (
  <ul className="death-counts">
    <li>
      <strong>{c.actual_deaths}</strong> muertes reales
    </li>
    <li>
      <strong>{c.wipe_deaths}</strong> revividos tras wipe
    </li>
    <li>
      <strong>{c.segment_deaths}</strong> muertes de progresión actuales
    </li>
  </ul>
);

function blockerText(data: OwnDeaths) {
  switch (data.confirm_blocker) {
    case "save_missing":
      return "Registra tu partida oficial desde PokeApp Launcher para poder confirmarlo.";
    case "death_history_pending_sync":
      return "Tu última sincronización todavía se está incorporando. Vuelve a mirarlo en unos segundos.";
    case "death_history_admin_required":
      return "Tu historial necesita una revisión de Administración: es un caso excepcional (muertes anteriores al seguimiento, una caja cambiada o más revividos tras wipe que muertes).";
    default:
      return null;
  }
}

/**
 * The trainer's OWN death history. Only the values PokeApp observed in the
 * official save can be confirmed, exactly as shown; nothing is typed.
 * `inline` renders just the action (Liga › General, next to the blocker).
 */
export function OwnDeathHistory({ inline = false }: { inline?: boolean }) {
  const { season } = useApp();
  const path = ownDeathPath(season);
  const query = useRead<OwnDeaths>(path, !!season);
  const [open, setOpen] = useState(false);
  const data = query.data;
  // Auxiliary card: a failed read stays quiet here (Liga › General keeps
  // listing what is missing), never a second alert on the profile.
  if (!data || data.known || data.confirm_blocker === "death_history_closed")
    return null;
  if (inline)
    return data.can_confirm ? (
      <>
        <button className="button small" onClick={() => setOpen(true)}>
          <ShieldCheck size={15} aria-hidden="true" /> Confirmar mi historial
        </button>
        {open && <ConfirmDeaths data={data} onClose={() => setOpen(false)} />}
      </>
    ) : null;
  return (
    <section className="own-death-history" aria-labelledby="own-death-title">
      <h2 id="own-death-title">
        <Skull size={17} aria-hidden="true" /> Historial de muertes de la Liga
      </h2>
      {data.can_confirm && data.proposed ? (
        <>
          <p>
            Tus puntos oficiales aparecen como «—» hasta que confirmes tu
            historial de muertes, incluso si tienes cero muertes. Esta
            confirmación también es necesaria para abrir la jornada. PokeApp ha
            observado en tu partida oficial (Caja {data.dead_box_number}):
          </p>
          {countLine(data.proposed)}
          <button className="button primary" onClick={() => setOpen(true)}>
            <ShieldCheck size={16} aria-hidden="true" /> Confirmar historial de
            muertes
          </button>
        </>
      ) : (
        <p className="muted">{blockerText(data)}</p>
      )}
      {open && <ConfirmDeaths data={data} onClose={() => setOpen(false)} />}
    </section>
  );
}

function ConfirmDeaths({
  data,
  onClose,
}: {
  data: OwnDeaths;
  onClose: () => void;
}) {
  const { season } = useApp();
  const cmd = useCommand([ownDeathPath(season), readinessPath(season)]);
  const proposed = data.proposed!;
  const busy = cmd.pending || cmd.uncertain;
  // Closes on a confirmed answer, also after «Reintentar la misma solicitud».
  useEffect(() => {
    if (cmd.success && !cmd.pending) onClose();
  }, [cmd.success, cmd.pending, onClose]);
  return (
    <Modal
      title="Confirmar mi historial de muertes"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p>
        Se registrarán exactamente estos valores, observados por PokeApp en tu
        partida oficial (Caja {data.dead_box_number}):
      </p>
      {countLine(proposed)}
      <p className="muted">
        Si no son correctos, no confirmes: avisa a Administración para que lo
        revise con su evidencia. Solo puedes confirmar tu propio historial.
      </p>
      <button
        className="button primary"
        disabled={busy}
        onClick={() =>
          void cmd.execute(
            ownDeathPath(season),
            {
              expected_revision: data.revision,
              source_sha256: data.source_sha256!,
              ...proposed,
            } satisfies Model<"OwnDeathHistoryBody">,
            "PUT",
          )
        }
      >
        Confirmar estos valores
      </button>
      <CommandState command={cmd} />
    </Modal>
  );
}
