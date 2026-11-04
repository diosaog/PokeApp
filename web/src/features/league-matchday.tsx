import { useEffect, useState } from "react";
import { CalendarCheck, CalendarPlus, Flag } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { CommandState, Modal, Notice, form, useCommand } from "../ui";
import { DailyTieFields, readTieResolution, tieReview } from "./daily-ties";
import {
  OwnDeathHistory,
  prepareFirstMatchday,
  readinessPath,
  readinessText,
  trainerReasonText,
  type Readiness,
} from "./league-start";

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

/**
 * Liga › General, right below the standings: the next matchday's opening
 * control. Always present while the League is in play (079): the server's
 * readiness says whether J<n> can open and, if not, exactly why, per
 * trainer. An all-vs-all J1 that does not exist yet is prepared by the same
 * confirmation (idempotent), never through Administración.
 */
export function OpenMatchday({
  data,
  onShowDay,
}: {
  data: Model<"LeagueGeneralRead">;
  onShowDay: (dayId: string) => void;
}) {
  const { me } = useApp();
  const season = data.season.id;
  const query = useRead<Readiness>(readinessPath(season), !!season);
  const cmd = useCommand([readinessPath(season)]);
  const [intent, setIntent] = useState<{ number: number } | null>(null);
  const [preparing, setPreparing] = useState(false),
    [prepareError, setPrepareError] = useState<unknown>(null);
  useHold(cmd.pending || cmd.uncertain || preparing);
  const ready = query.data;
  if (!ready)
    return query.error ? (
      <div className="matchday-bar">
        <Notice error={query.error} />
      </div>
    ) : null;
  if (ready.state === "open" && ready.matchday)
    return (
      <div className="matchday-bar is-open" role="status">
        <CalendarCheck size={20} aria-hidden="true" />
        <span>
          <strong>Jornada {ready.matchday.number} en curso.</strong> Registra
          los combates y ciérrala desde su pestaña.
        </span>
        <button
          className="button"
          onClick={() => onShowDay(ready.matchday!.id)}
        >
          Ir a J{ready.matchday.number}
        </button>
      </div>
    );
  if (ready.state === "completed" || ready.state === "finished")
    return (
      <div className="matchday-bar is-done" role="status">
        <Flag size={20} aria-hidden="true" />
        <span>
          {ready.state === "finished" ? (
            <>
              <strong>La Liga ha terminado.</strong> Sus jornadas y su
              clasificación quedan como historial oficial.
            </>
          ) : (
            <>
              <strong>Todas las jornadas se han jugado.</strong> Queda confirmar
              el campeón con la revisión final.
            </>
          )}
        </span>
      </div>
    );
  const number = ready.next_number ?? ready.matchday?.number ?? 1;
  const unprepared = ready.state === "unprepared";
  const blocked = ready.participants.filter((p) => p.reasons.length);
  const pairs =
    (ready.participants.length * (ready.participants.length - 1)) / 2;
  const battles = `${pairs} ${pairs === 1 ? "combate" : "combates"}`;
  const busy = cmd.pending || cmd.uncertain || preparing || query.isFetching;
  const enabled =
    ready.can_open && ready.can_operate && ready.state !== "unavailable";
  return (
    <div className={`matchday-bar ${enabled ? "is-ready" : "is-blocked"}`}>
      <CalendarPlus size={20} aria-hidden="true" />
      <span>
        <strong>Jornada {number}</strong>{" "}
        {enabled
          ? unprepared
            ? `lista: todos contra todos, ${battles}.`
            : "preparada y lista para abrirse."
          : unprepared
            ? "aún no puede empezar."
            : "preparada, pendiente de abrirse."}
        {!ready.can_operate &&
          " La abre cualquier participante activo de la Liga."}
      </span>
      <button
        className="button primary"
        disabled={busy || !enabled}
        aria-describedby={enabled ? undefined : "matchday-blockers"}
        onClick={() => {
          setPrepareError(null);
          setIntent({ number });
        }}
      >
        Abrir jornada {number}
      </button>
      {!enabled && (
        <div id="matchday-blockers" className="matchday-blockers">
          <p>Para abrirla falta:</p>
          <ul>
            {ready.reasons.map((code) => (
              <li key={code}>{readinessText(code)}</li>
            ))}
            {blocked.map((p) => {
              const own = p.trainer_id === me?.trainer_id;
              return (
                <li key={p.season_player_id} className={own ? "is-own" : ""}>
                  <strong>{own ? "Tú" : p.display_name}:</strong>{" "}
                  {p.reasons.map((r) => trainerReasonText(r, own)).join("; ")}.
                  {own && p.self_confirmable && <OwnDeathHistory inline />}
                </li>
              );
            })}
          </ul>
        </div>
      )}
      <Notice error={prepareError} />
      {!intent && <CommandState command={cmd} />}
      {intent && (
        <Modal
          title={`Abrir jornada ${intent.number}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain && !preparing) setIntent(null);
          }}
        >
          <p>
            {unprepared &&
              `Se preparará la J1 con todos contra todos (${battles}) y se abrirá. `}
            Se fijarán las muertes de la progresión con las partidas
            sincronizadas. Después cualquier participante podrá registrar los
            resultados. Si falta algo, la apertura quedará bloqueada y verás el
            motivo.
          </p>
          <button
            className="button primary"
            disabled={busy}
            onClick={async () => {
              if (busy) return;
              setPrepareError(null);
              let day = ready.matchday;
              if (unprepared) {
                setPreparing(true);
                try {
                  const prepared = await prepareFirstMatchday(season);
                  day = {
                    id: prepared.matchday_id,
                    number: prepared.number,
                    status: prepared.status,
                    revision: prepared.revision,
                  };
                } catch (error) {
                  setPrepareError(error);
                  setIntent(null);
                  return;
                } finally {
                  setPreparing(false);
                }
              }
              if (!day || day.status !== "scheduled") {
                // Someone else opened it meanwhile: show its current state.
                setIntent(null);
                void query.refetch();
                return;
              }
              if (
                await cmd.execute(`${dayPath(season, day.id)}/open`, {
                  expected_revision: day.revision,
                } satisfies Model<"OpenDayBody">)
              ) {
                setIntent(null);
                onShowDay(day.id);
              }
            }}
          >
            {preparing ? "Preparando la J1…" : "Confirmar apertura"}
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
