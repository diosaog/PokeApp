import { useEffect, useState } from "react";
import { CalendarCheck, CalendarPlus, Flag } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { CommandState, Modal, Notice, form, useCommand } from "../ui";
import { DailyTieFields, readTieResolution, tieReview } from "./daily-ties";

// Ordinary matchday operations of any active, eligible participant of this
// season (server-checked since 041 by league_operation_principal). The
// existing transactional SQL lifecycle does the work: opening freezes the
// progression death segment and prepares the round robin; closing freezes
// the official standings and grants their points, coins and prizes once.
// Exceptional actions (cancel, corrections) stay in Administración.

const dayPath = (season: string, day: string) =>
  `/v1/seasons/${season}/matchdays/${day}`;

function useHold(active: boolean) {
  const { holdAdminNavigation } = useApp();
  useEffect(() => {
    if (active && holdAdminNavigation) return holdAdminNavigation();
  }, [active, holdAdminNavigation]);
}

/** Liga › General, right below the standings: open the next matchday. */
export function OpenMatchday({
  data,
  onShowDay,
}: {
  data: Model<"LeagueGeneralRead">;
  onShowDay: (dayId: string) => void;
}) {
  const { me } = useApp();
  const day = data.days.find((d) => d.id === data.season.current_matchday_id);
  const eligible =
    data.season.status === "active" &&
    data.rows.some(
      (p) => p.trainer_id === me?.trainer_id && p.status === "active",
    );
  const base = day ? dayPath(data.season.id, day.id) : "";
  const query = useRead<Model<"DayState">>(
    base,
    eligible && day?.status === "scheduled",
  );
  const cmd = useCommand();
  const [intent, setIntent] = useState<{
    revision: number;
    base: string;
  } | null>(null);
  useHold(cmd.pending || cmd.uncertain);
  if (!day || day.status === "closed" || data.season.status !== "active")
    return null;
  if (day.status === "open")
    return (
      <div className="matchday-bar is-open" role="status">
        <CalendarCheck size={20} aria-hidden="true" />
        <span>
          <strong>Jornada {day.number} en curso.</strong> Registra los combates
          y ciérrala desde su pestaña.
        </span>
        <button className="button" onClick={() => onShowDay(day.id)}>
          Ir a J{day.number}
        </button>
      </div>
    );
  const state = query.data;
  const ready = eligible && state?.state === "scheduled";
  const stale =
    !!intent &&
    (intent.base !== base ||
      state?.state !== "scheduled" ||
      intent.revision !== state.revision);
  const busy = cmd.pending || cmd.uncertain || query.isFetching;
  return (
    <div className="matchday-bar">
      <CalendarPlus size={20} aria-hidden="true" />
      <span>
        <strong>Jornada {day.number}</strong> preparada.
        {!eligible && " La abre cualquier participante activo de la Liga."}
      </span>
      {eligible && (
        <button
          className="button primary"
          disabled={busy || !ready}
          onClick={() => setIntent({ revision: state!.revision, base })}
        >
          Abrir jornada {day.number}
        </button>
      )}
      <Notice error={query.error} />
      {!intent && <CommandState command={cmd} />}
      {intent && (
        <Modal
          title={`Abrir jornada ${day.number}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setIntent(null);
          }}
        >
          <p>
            Se fijarán las muertes de la progresión con las partidas
            sincronizadas y se prepararán los combates. Después cualquier
            participante podrá registrar los resultados. Si falta evidencia, la
            apertura quedará bloqueada y verás el motivo.
          </p>
          {stale && (
            <p role="alert">
              La jornada cambió. Revisa su estado antes de confirmar.
            </p>
          )}
          <button
            className="button primary"
            disabled={busy || stale}
            onClick={async () => {
              if (busy || stale) return;
              if (
                await cmd.execute(`${intent.base}/open`, {
                  expected_revision: intent.revision,
                } satisfies Model<"OpenDayBody">)
              ) {
                setIntent(null);
                onShowDay(day.id);
              }
            }}
          >
            Confirmar apertura
          </button>
          <CommandState command={cmd} />
        </Modal>
      )}
    </div>
  );
}

/** Liga › J<n>, at the bottom of the matchday: close it once all is played. */
export function CloseMatchday({
  seasonId,
  dayId,
  number,
  single,
  name,
}: {
  seasonId: string;
  dayId: string;
  number?: number;
  single: boolean;
  name: (id: string) => string;
}) {
  const base = dayPath(seasonId, dayId),
    query = useRead<Model<"DayState">>(base),
    cmd = useCommand([base]),
    [intent, setIntent] = useState<{ revision: number } | null>(null);
  useHold(cmd.pending || cmd.uncertain);
  const state = query.data;
  if (!state) return <Notice error={query.error} />;
  if (state.state !== "open" || state.current_matchday_id !== dayId)
    return null;
  const pending = state.matches.filter((m) => !m.winner_id);
  // Every scheduled battle has a winner; the server validates it again.
  const complete = pending.length === 0;
  const busy = cmd.pending || cmd.uncertain || query.isFetching;
  const stale = !!intent && intent.revision !== state.results_revision;
  const review = tieReview(cmd.error);
  return (
    <section className="matchday-close" aria-labelledby="matchday-close-title">
      <div>
        <h2 id="matchday-close-title">
          <Flag size={18} aria-hidden="true" /> Cerrar la J{number}
        </h2>
        <p className={complete ? "is-ready" : "muted"}>
          {complete
            ? state.matches.length
              ? "Todos los combates tienen resultado: la jornada está lista para cerrarse."
              : "No hay combates pendientes: la jornada está lista para cerrarse."
            : `Faltan ${pending.length} ${pending.length === 1 ? "combate" : "combates"} por registrar.`}
        </p>
      </div>
      <button
        className="button primary"
        disabled={busy || !complete}
        onClick={() => setIntent({ revision: state.results_revision })}
      >
        Cerrar jornada {number}
      </button>
      {!intent && <CommandState command={cmd} />}
      {intent && (
        <Modal
          title={`Cerrar jornada ${number ?? ""}`.trim()}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setIntent(null);
          }}
        >
          <p>
            Se cerrará la Jornada {number} con estos resultados: se congelará su
            clasificación oficial y se aplicarán puntos, muertes del tramo,
            monedas, premios y movimientos. Después solo Administración podrá
            corregirla con el procedimiento auditado.
          </p>
          <ul className="matchday-close-summary">
            {state.matches.map((m) => (
              <li key={m.id}>
                {name(m.player_a_id)} vs {name(m.player_b_id)} ·{" "}
                <strong>
                  {m.winner_id ? `gana ${name(m.winner_id)}` : "sin resultado"}
                </strong>
              </li>
            ))}
          </ul>
          {stale && (
            <p role="alert">
              Los resultados han cambiado. Cierra esta confirmación y vuelve a
              revisarlos.
            </p>
          )}
          <form
            onSubmit={async (event) => {
              const values = form(event);
              if (busy || stale) return;
              const resolution = readTieResolution(values, review);
              if (
                await cmd.execute(`${base}/close`, {
                  expected_results_revision: intent.revision,
                  ...(resolution ? { tie_resolution: resolution } : {}),
                } satisfies Model<"ParticipantCloseDayBody">)
              )
                setIntent(null);
            }}
          >
            <fieldset disabled={busy || stale}>
              <DailyTieFields review={review} name={name} single={single} />
              <button className="button primary" disabled={busy || stale}>
                Confirmar cierre
              </button>
            </fieldset>
          </form>
          <CommandState command={cmd} />
        </Modal>
      )}
    </section>
  );
}
