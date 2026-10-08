import { useEffect, useState, type ComponentProps } from "react";
import { Link } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Heading,
  Loading,
  Modal,
  Notice,
  Submit,
  Tag,
  form,
  number,
  text,
  useCommand,
} from "../ui";
import { DailyTieFields, readTieResolution, tieReview } from "./daily-ties";
import { InitialAssignment } from "./initial-assignment";
import { Rules } from "./rules";
import { LockStatus } from "./lock-status";
import { ChampionshipReview } from "./championship";
import {
  dayLabel,
  participantLabel,
  readinessLabel,
  seasonLabel,
} from "./admin-labels";

type Setup = Model<"SeasonSetup">;
function AdminLink(props: ComponentProps<typeof Link>) {
  const { adminOperationPending } = useApp();
  return (
    <Link
      {...props}
      aria-disabled={adminOperationPending || undefined}
      onClick={(event) => {
        if (adminOperationPending) event.preventDefault();
        else props.onClick?.(event);
      }}
    />
  );
}
function useAdminCommand() {
  const command = useCommand(),
    { holdAdminNavigation } = useApp();
  useEffect(() => {
    if ((command.pending || command.uncertain) && holdAdminNavigation)
      return holdAdminNavigation();
  }, [command.pending, command.uncertain, holdAdminNavigation]);
  return command;
}
function Participants({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    trainers = useRead<Model<"TrainerRead">[]>("/v1/read/trainers"),
    overview = useOverview(),
    cmd = useAdminCommand(),
    [target, setTarget] = useState(""),
    [targetRevision, setTargetRevision] = useState(setup.roster_revision);
  const busy = cmd.pending || cmd.uncertain,
    canAdd =
      setup.season.status === "draft" &&
      !setup.first_matchday &&
      setup.memberships.length === 0,
    canRemove =
      canAdd &&
      setup.config_versions.length === 0 &&
      setup.divisions.length === 0,
    currentDay = overview.data?.days.find(
      (d) => d.id === setup.current_matchday_id,
    ),
    currentHasResults = overview.data?.matches.some(
      (m) => m.matchday_id === setup.current_matchday_id && !!m.winner_id,
    ),
    canChange =
      setup.season.status === "active" &&
      currentDay?.status === "scheduled" &&
      !currentHasResults,
    selected = setup.participants.find((p) => p.id === target),
    allowed =
      selected?.status === "active" &&
      targetRevision === setup.roster_revision &&
      (setup.season.status === "draft" ? canRemove : canChange);
  return (
    <>
      <Card>
        <h2>Añadir entrenador</h2>
        <form
          onSubmit={(event) => {
            const data = form(event);
            if (!canAdd || busy) return;
            void cmd.execute(`/v1/admin/seasons/${season}/participants`, {
              trainer_id: text(data, "trainer"),
              expected_roster_revision: setup.roster_revision,
            } satisfies Model<"AddParticipantBody">);
          }}
        >
          <Field label="Entrenador">
            <select name="trainer" required disabled={!canAdd || busy}>
              <option value="">Seleccionar</option>
              {trainers.data
                ?.filter(
                  (t) => !setup.participants.some((p) => p.trainer_id === t.id),
                )
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.display_name}
                  </option>
                ))}
            </select>
          </Field>
          <Submit pending={busy || !canAdd}>Añadir a la temporada</Submit>
        </form>
        {!canAdd && (
          <p>
            Solo se pueden añadir entrenadores durante el borrador, antes de
            preparar las divisiones y la primera jornada.
          </p>
        )}
        <Notice error={trainers.error} />
      </Card>
      <p>
        Las retiradas, abandonos y descalificaciones de Liga se registran antes
        de abrir la jornada actual y conservan el historial. La descalificación
        de Liga no descalifica automáticamente de la Copa.
      </p>
      {!canChange && setup.season.status === "active" && (
        <p>
          Los cambios de participación estarán disponibles con la jornada actual
          preparada y sin resultados.
        </p>
      )}
      <Notice error={overview.error} />
      <div className="trainer-grid">
        {setup.participants.map((p) => (
          <Card key={p.id}>
            <h3>{p.display_name}</h3>
            <Tag>{participantLabel(p.status)}</Tag>
            <p>
              {p.stats_ready
                ? "Estadísticas disponibles"
                : "Estadísticas pendientes"}
            </p>
            <button
              disabled={
                busy ||
                p.status !== "active" ||
                !(setup.season.status === "draft" ? canRemove : canChange)
              }
              onClick={() => {
                setTargetRevision(setup.roster_revision);
                setTarget(p.id);
              }}
            >
              Gestionar estado
            </button>
          </Card>
        ))}
      </div>
      {!target && <CommandState command={cmd} />}
      {target && (
        <Modal
          title={`Estado de ${setup.participants.find((p) => p.id === target)?.display_name}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setTarget("");
          }}
        >
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (busy || !allowed) return;
              if (
                await cmd.execute(
                  `/v1/admin/seasons/${season}/participants/${target}/${text(data, "action")}`,
                  {
                    reason: text(data, "reason"),
                    expected_roster_revision: targetRevision,
                  },
                )
              )
                setTarget("");
            }}
          >
            {targetRevision !== setup.roster_revision && (
              <p role="alert">
                La plantilla ha cambiado. Cierra esta confirmación y vuelve a
                revisar al participante.
              </p>
            )}
            <fieldset disabled={busy || !allowed}>
              <Field label="Acción">
                <select name="action">
                  {setup.season.status === "draft" ? (
                    <option value="remove-from-draft">
                      Quitar del borrador
                    </option>
                  ) : (
                    <>
                      <option value="retire">Retirada</option>
                      <option value="abandon">Abandono</option>
                      <option value="disqualify">
                        Descalificación de la Liga
                      </option>
                    </>
                  )}
                </select>
              </Field>
              <Field label="Motivo">
                <textarea name="reason" required maxLength={500} />
              </Field>
              <p>
                Se aplicarán las reglas de participación de la temporada. El
                historial se conserva. La descalificación afecta a la Liga; no
                implica una descalificación automática de la Copa. Esta decisión
                no puede deshacerse desde esta pantalla.
              </p>
              <Submit pending={busy || !allowed}>
                Confirmar cambio de estado
              </Submit>
            </fieldset>
            <CommandState command={cmd} />
          </form>
        </Modal>
      )}
    </>
  );
}
function DayAdmin({ dayId, setup }: { dayId: string; setup: Setup }) {
  const { season } = useApp(),
    q = useRead<Model<"DayState">>(
      `/v1/admin/seasons/${season}/matchdays/${dayId}`,
    ),
    ov = useOverview(),
    cmd = useAdminCommand(),
    [confirm, setConfirm] = useState(false),
    [cancel, setCancel] = useState(false),
    [confirmedResults, setConfirmedResults] = useState<number | null>(null),
    [cancelRevision, setCancelRevision] = useState<number | null>(null);
  if (q.isPending) return <Loading />;
  if (q.error)
    return (
      <>
        <Notice error={q.error} />
        <CommandState command={cmd} />
      </>
    );
  const day = q.data!,
    base = `/v1/admin/seasons/${season}/matchdays/${dayId}`,
    review = tieReview(cmd.error),
    name = (id: string) =>
      setup.participants.find((p) => p.id === id)?.display_name ??
      "Entrenador pendiente de consultar",
    displayDay = ov.data?.days.find((d) => d.id === dayId),
    currentDay = ov.data?.days.find((d) => d.id === setup.current_matchday_id),
    active = setup.season.status === "active",
    canOperate = active && setup.current_matchday_id === dayId,
    canCorrect =
      active &&
      (setup.current_matchday_id === dayId ||
        (currentDay?.status === "scheduled" &&
          displayDay?.number === currentDay.number - 1)),
    busy = cmd.pending || cmd.uncertain,
    canClose =
      canOperate &&
      day.state === "open" &&
      confirmedResults === day.results_revision,
    canCancel =
      canOperate && day.state === "open" && cancelRevision === day.revision;
  return (
    <Card>
      <h2>
        Jornada{displayDay ? ` ${displayDay.number}` : ""} ·{" "}
        {dayLabel(day.state)}
      </h2>
      {!active && (
        <p>
          Consulta histórica: esta temporada ya no admite cambios de jornada.
        </p>
      )}
      {!confirm && !cancel && <CommandState command={cmd} />}
      {day.state === "scheduled" && (
        <button
          disabled={busy || !canOperate}
          onClick={() =>
            void cmd.execute(`${base}/open`, {
              expected_revision: day.revision,
            } satisfies Model<"OpenDayBody">)
          }
        >
          Abrir jornada
        </button>
      )}
      {day.state === "closed" && (
        <form
          key={`${day.revision}:${day.results_revision}`}
          onSubmit={(event) => {
            const data = form(event);
            if (busy || !canCorrect || !data.has("confirm")) return;
            const results = day.matches.map((m) => ({
              match_id: m.id,
              winner_season_player_id: text(data, m.id) || null,
            }));
            const resolution = readTieResolution(data, review);
            void cmd.execute(`${base}/correct`, {
              expected_snapshot_revision: day.snapshot_revision,
              reason: text(data, "reason"),
              results,
              ...(resolution ? { tie_resolution: resolution } : {}),
            } satisfies Model<"CorrectDayBody">);
          }}
        >
          <fieldset disabled={busy || !canCorrect}>
            <p>
              Una corrección modifica los resultados oficiales y sus
              consecuencias mediante el procedimiento auditado. Indica el motivo
              y revisa cada ganador.
            </p>
            {day.matches.map((m) => (
              <Field
                key={m.id}
                label={`${name(m.player_a_id)} / ${name(m.player_b_id)}`}
              >
                <select name={m.id} defaultValue={m.winner_id || ""} required>
                  <option value="">Pendiente</option>
                  {[m.player_a_id, m.player_b_id].map((id) => (
                    <option key={id} value={id}>
                      {name(id)}
                    </option>
                  ))}
                </select>
              </Field>
            ))}
            <Field label="Motivo de corrección">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <DailyTieFields review={review} name={name} />
            <label className="check">
              <input name="confirm" type="checkbox" required />
              He revisado los ganadores y confirmo esta corrección excepcional.
            </label>
            {day.matches.length > 0 && (
              <Submit pending={busy || !canCorrect}>Corregir jornada</Submit>
            )}
          </fieldset>
          {!canCorrect && (
            <p>
              Solo se puede corregir la última jornada cerrada mientras la Liga
              sigue en curso y la siguiente aún no ha empezado.
            </p>
          )}
        </form>
      )}
      {day.state === "open" && (
        <p>
          Los resultados ordinarios se registran en{" "}
          <AdminLink to="/liga">Liga</AdminLink>.
        </p>
      )}
      {day.state === "open" && (
        <div className="toolbar">
          <button
            className="button primary"
            disabled={busy || !canOperate}
            onClick={() => {
              setConfirmedResults(day.results_revision);
              setConfirm(true);
            }}
          >
            Cerrar jornada
          </button>
          <button
            disabled={busy || !canOperate}
            onClick={() => {
              setCancelRevision(day.revision);
              setCancel(true);
            }}
          >
            Cancelar edición
          </button>
        </div>
      )}
      {cancel && (
        <Modal
          title="Cancelar edición de jornada"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setCancel(false);
          }}
        >
          <p>
            Se descartarán los resultados provisionales y la jornada volverá al
            estado programado.
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (busy || !canCancel || cancelRevision === null) return;
              if (
                await cmd.execute(`${base}/cancel-editing`, {
                  expected_revision: cancelRevision,
                  reason: text(data, "reason"),
                } satisfies Model<"CancelDayBody">)
              )
                setCancel(false);
            }}
          >
            {!canCancel && (
              <p role="alert">
                La jornada ha cambiado. Cierra esta confirmación y revisa sus
                datos actuales.
              </p>
            )}
            <Field label="Motivo de cancelación">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <CommandState command={cmd} />
            <Submit pending={busy || !canCancel}>
              Confirmar cancelación de edición
            </Submit>
          </form>
        </Modal>
      )}
      {confirm && (
        <Modal
          title="Cerrar jornada"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setConfirm(false);
          }}
        >
          <p>
            Se congelarán los resultados y se aplicarán puntos, monedas y
            movimientos. Revisa todos los ganadores antes de continuar.
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event),
                resolution = readTieResolution(data, review);
              if (busy || !canClose || confirmedResults === null) return;
              if (
                await cmd.execute(`${base}/close`, {
                  expected_results_revision: confirmedResults,
                  ...(resolution ? { tie_resolution: resolution } : {}),
                } satisfies Model<"CloseDayBody">)
              )
                setConfirm(false);
            }}
          >
            {!canClose && (
              <p role="alert">
                Los resultados han cambiado. Cierra esta confirmación y vuelve a
                revisar los ganadores.
              </p>
            )}
            <fieldset disabled={busy || !canClose}>
              <DailyTieFields review={review} name={name} />
              <Submit pending={busy || !canClose}>Confirmar cierre</Submit>
            </fieldset>
          </form>
          <CommandState command={cmd} />
        </Modal>
      )}
    </Card>
  );
}
function Competition({ setup }: { setup: Setup }) {
  const { season, adminOperationPending } = useApp(),
    cmd = useAdminCommand(),
    [selected, setSelected] = useState(setup.current_matchday_id || ""),
    [activate, setActivate] = useState(false),
    [activationRevision, setActivationRevision] = useState(
      setup.setup_revision,
    ),
    ov = useOverview();
  const day = selected || setup.current_matchday_id || "";
  const observedInitial =
    setup.initial_assignment_rule === "observed_deaths_v1";
  const busy = cmd.pending || cmd.uncertain,
    legacyEditable = setup.season.status === "draft" && !setup.first_matchday,
    canAssign = legacyEditable && setup.memberships.length === 0,
    canPrepare =
      legacyEditable &&
      "memberships_complete" in setup.readiness.checks &&
      setup.readiness.checks.has_roster &&
      setup.readiness.checks.has_valid_config &&
      setup.readiness.checks.memberships_complete,
    canActivate =
      setup.season.status === "draft" && setup.readiness.can_activate;
  return (
    <>
      {observedInitial && <InitialAssignment administrative />}
      <Card>
        <h2>Preparación de la Liga</h2>
        {!observedInitial && (
          <form
            onSubmit={(event) => {
              const data = form(event);
              if (busy || !canAssign) return;
              const assignments = { A: [] as string[], B: [] as string[] };
              setup.participants.forEach((p) => {
                const d = text(data, p.id);
                if (d === "A" || d === "B") assignments[d].push(p.id);
              });
              void cmd.execute(
                `/v1/admin/seasons/${season}/initial-divisions`,
                {
                  config_version_id: text(data, "config"),
                  assignments,
                  expected_roster_revision: setup.roster_revision,
                  expected_setup_revision: setup.setup_revision,
                } satisfies Model<"InitialDivisionsBody">,
                "PUT",
              );
            }}
          >
            <fieldset disabled={busy || !canAssign}>
              <Field label="Versión de configuración">
                <select name="config" required>
                  <option value="">Seleccionar versión</option>
                  {setup.config_versions
                    .filter((c) => c.effective_from_matchday === 1)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              </Field>
              <div className="form-grid">
                {setup.participants.map((p) => (
                  <Field key={p.id} label={p.display_name}>
                    <select name={p.id} required>
                      <option value="">Seleccionar división</option>
                      <option>A</option>
                      <option>B</option>
                    </select>
                  </Field>
                ))}
              </div>
              <Submit pending={busy || !canAssign}>
                Guardar divisiones iniciales
              </Submit>
            </fieldset>
          </form>
        )}
        {observedInitial && setup.season.status === "draft" && (
          <p>
            Activa la Liga para comenzar el primer tramo. Las divisiones y la
            primera jornada se prepararán al confirmar el reparto observado.
          </p>
        )}
        <div className="toolbar">
          {!observedInitial && (
            <button
              disabled={busy || !canPrepare}
              onClick={() =>
                void cmd.execute(
                  `/v1/admin/seasons/${season}/matchdays/prepare-current`,
                  { expected_setup_revision: setup.setup_revision },
                )
              }
            >
              Preparar primera jornada
            </button>
          )}
          {setup.season.status === "draft" && (
            <button
              disabled={busy || !canActivate}
              onClick={() => {
                setActivationRevision(setup.setup_revision);
                setActivate(true);
              }}
            >
              Activar Liga
            </button>
          )}
          <AdminLink className="button" to="/copa">
            Gestionar Copas →
          </AdminLink>
        </div>
        {!activate && <CommandState command={cmd} />}
      </Card>
      {activate && (
        <Modal
          title="Activar Liga"
          onClose={() => {
            if (!busy) setActivate(false);
          }}
        >
          <p>
            Comenzará la Liga {setup.season.name}. Revisa la plantilla y la
            configuración antes de confirmar.
          </p>
          <button
            className="button primary"
            disabled={
              busy ||
              !canActivate ||
              activationRevision !== setup.setup_revision
            }
            onClick={async () => {
              if (
                busy ||
                !canActivate ||
                activationRevision !== setup.setup_revision
              )
                return;
              if (
                await cmd.execute(`/v1/admin/seasons/${season}/activate`, {
                  expected_setup_revision: activationRevision,
                })
              )
                setActivate(false);
            }}
          >
            Confirmar activación
          </button>
          {activationRevision !== setup.setup_revision && (
            <p role="alert">
              La preparación ha cambiado. Cierra esta confirmación y revisa de
              nuevo la temporada.
            </p>
          )}
          <CommandState command={cmd} />
        </Modal>
      )}
      <Field label="Jornada a gestionar">
        <select
          disabled={adminOperationPending}
          value={day}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Seleccionar jornada</option>
          {ov.data?.days.map((d) => (
            <option key={d.id} value={d.id}>
              Jornada {d.number} · {dayLabel(d.status)}
            </option>
          ))}
        </select>
      </Field>
      <Notice error={ov.error} />
      {day && <DayAdmin key={day} dayId={day} setup={setup} />}
      {day && ov.data && (
        <Card>
          <h2>Equipos fijados para la jornada</h2>
          <p>
            El primer equipo fijado determina si llegó a tiempo. Puedes
            reemplazarlo mientras la jornada esté abierta.
          </p>
          <div className="trainer-grid">
            {setup.participants.map((p) => {
              const lock = ov.data.locks.find(
                (item) =>
                  item.trainer_id === p.trainer_id && item.matchday_id === day,
              );
              return (
                <div key={p.id}>
                  <h3>{p.display_name}</h3>
                  <LockStatus
                    status={
                      lock ? (lock.timing_status ?? "unknown") : "pending"
                    }
                  />
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </>
  );
}
function Risk({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    cmd = useAdminCommand(),
    [action, setAction] = useState(""),
    [actionRevision, setActionRevision] = useState(setup.setup_revision);
  const labels: Record<string, string> = {
      archive: "Archivar temporada",
      discard: "Descartar temporada",
    },
    allowed: Record<string, boolean> = {
      archive: setup.season.status === "finished",
      discard: setup.season.status === "draft",
    },
    busy = cmd.pending || cmd.uncertain;
  return (
    <Card className="risk">
      <h2>Zona de riesgo</h2>
      <p>
        Finalizar da por cerrada la Liga. Archivar congela su paquete histórico
        y registra el título en el Hall. Descartar conserva la trazabilidad.
      </p>
      <p>
        Archivar está disponible después de finalizar la Liga. Solo se puede
        descartar un borrador.
      </p>
      <div className="toolbar">
        {[
          ["archive", "Archivar temporada"],
          ["discard", "Descartar temporada"],
        ].map(([op, label]) => (
          <button
            className="danger"
            key={op}
            disabled={busy || !allowed[op]}
            onClick={() => {
              setActionRevision(setup.setup_revision);
              setAction(op);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {action && (
        <Modal
          title={labels[action]}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setAction("");
          }}
        >
          <p>
            Acción: <strong>{labels[action]}</strong> · {setup.season.name}.
            Revisa la temporada seleccionada.
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                busy ||
                !allowed[action] ||
                actionRevision !== setup.setup_revision ||
                text(data, "confirmation") !== setup.season.name
              )
                return;
              if (
                await cmd.execute(`/v1/admin/seasons/${season}/${action}`, {
                  expected_revision: actionRevision,
                  ...(action === "discard"
                    ? { reason: text(data, "reason"), confirmation: "DISCARD" }
                    : {}),
                })
              )
                setAction("");
            }}
          >
            {actionRevision !== setup.setup_revision && (
              <p role="alert">
                La temporada ha cambiado. Cierra esta confirmación y revisa su
                estado actual.
              </p>
            )}
            {action === "discard" && (
              <Field label="Motivo">
                <textarea name="reason" required maxLength={500} />
              </Field>
            )}
            <Field label={`Escribe ${setup.season.name} para confirmar`}>
              <input name="confirmation" required />
            </Field>
            <CommandState command={cmd} />
            <Submit
              pending={
                busy ||
                !allowed[action] ||
                actionRevision !== setup.setup_revision
              }
            >
              Confirmar operación
            </Submit>
          </form>
        </Modal>
      )}
    </Card>
  );
}
export function AdminPage() {
  const { season, adminOperationPending } = useApp(),
    q = useRead<Setup>(`/v1/admin/seasons/${season}/setup`, !!season),
    [tab, setTab] = useState("Resumen"),
    [create, setCreate] = useState(false),
    cmd = useAdminCommand();
  return (
    <>
      <Heading eyebrow="ADMINISTRACIÓN DE TEMPORADA" title="Organizar mi Liga">
        Prepara la temporada, revisa sus reglas y gestiona las decisiones
        excepcionales.
      </Heading>
      <button
        className="button"
        disabled={adminOperationPending}
        onClick={() => setCreate(true)}
      >
        Crear temporada
      </button>
      <div className="tabs" role="tablist" aria-label="Administración">
        {[
          "Resumen",
          "Configuración",
          "Entrenadores",
          "Competición",
          "Historial",
          "Zona de riesgo",
        ].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            disabled={adminOperationPending}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <Notice error={q.error} />
      {!season ? (
        <Empty>Crea o selecciona una temporada.</Empty>
      ) : q.isPending ? (
        <Loading />
      ) : (
        q.data && (
          <div key={`${season}:${tab}`} role="tabpanel">
            {tab === "Resumen" ? (
              <Card>
                <h2>{q.data.season.name}</h2>
                <Tag>{seasonLabel(q.data.season.status)}</Tag>
                <p>{q.data.participants.length} participantes</p>
                <h3>Preparación</h3>
                {q.data.readiness.blocking_reasons.length ? (
                  q.data.readiness.blocking_reasons.map((reason) => (
                    <p key={reason}>{readinessLabel(reason)}</p>
                  ))
                ) : (
                  <p>Sin bloqueos de preparación.</p>
                )}
              </Card>
            ) : tab === "Configuración" ? (
              <Rules setup={q.data} />
            ) : tab === "Entrenadores" ? (
              <Participants setup={q.data} />
            ) : tab === "Competición" ? (
              <Competition setup={q.data} />
            ) : tab === "Zona de riesgo" ? (
              <>
                <ChampionshipReview seasonName={q.data.season.name} />
                <Risk setup={q.data} />
              </>
            ) : (
              <Card>
                <h2>Historia oficial</h2>
                <p>
                  Consulta las jornadas congeladas y los campeones certificados.
                  Las correcciones conservan su trazabilidad en el servidor.
                </p>
                <div className="toolbar">
                  <AdminLink className="button" to="/liga">
                    Jornadas oficiales
                  </AdminLink>
                  <AdminLink className="button" to="/hall">
                    Hall de la Fama
                  </AdminLink>
                  <AdminLink className="button" to="/juicios">
                    Historial de juicios
                  </AdminLink>
                </div>
              </Card>
            )}
          </div>
        )
      )}
      {create && (
        <Modal
          title="Crear temporada"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setCreate(false);
          }}
        >
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                await cmd.execute("/v1/admin/seasons", {
                  name: text(data, "name"),
                } satisfies Model<"CreateSeasonBody">)
              )
                setCreate(false);
            }}
          >
            <Field label="Nombre de temporada">
              <input name="name" required maxLength={120} />
            </Field>
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain}>
              Crear borrador
            </Submit>
          </form>
        </Modal>
      )}
    </>
  );
}
