import { useState } from "react";
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
import { playerName } from "./core";
import { DailyTieFields, readTieResolution, tieReview } from "./daily-ties";
import { InitialAssignment } from "./initial-assignment";
import { ChampionshipReview } from "./championship";

type Setup = Model<"SeasonSetup">;
function Configuration({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    cmd = useCommand(),
    [replacement, setReplacement] = useState("");
  const current = setup.config_versions.find((c) => c.id === replacement);
  return (
    <>
      <Card>
        <h2>Nombre de temporada</h2>
        <form
          onSubmit={(event) => {
            const data = form(event);
            void cmd.execute(
              `/v1/admin/seasons/${season}/name`,
              {
                name: text(data, "name"),
                expected_revision: setup.setup_revision,
              } satisfies Model<"RenameSeasonBody">,
              "PUT",
            );
          }}
        >
          <Field label="Nombre">
            <input
              name="name"
              required
              maxLength={120}
              defaultValue={setup.season.name}
            />
          </Field>
          <Submit pending={cmd.pending || cmd.uncertain}>Guardar nombre</Submit>
        </form>
      </Card>
      <Card>
        <h2>Configuración de competición</h2>
        <p>
          Los valores se validan frente a la plantilla actual. No se cambian
          resultados históricos.
        </p>
        <Field label="Versión a configurar">
          <select
            value={replacement}
            onChange={(event) => setReplacement(event.target.value)}
          >
            <option value="">Crear nueva versión</option>
            {setup.config_versions
              .filter((c) => !c.used)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  Reemplazar {c.name} (sin usar)
                </option>
              ))}
          </select>
        </Field>
        <form
          key={replacement}
          onSubmit={(event) => {
            const data = form(event),
              scores = text(data, "points").split(",").map(Number),
              coins = text(data, "coins").split(",").map(Number),
              positions = (values: number[]) =>
                Object.fromEntries(values.map((v, i) => [String(i + 1), v]));
            const body: Model<"ConfigVersionBody"> = {
              name: text(data, "name"),
              effective_from_matchday: number(data, "from"),
              total_matchdays: number(data, "total"),
              division_sizes: { A: number(data, "a"), B: number(data, "b") },
              movement_count: number(data, "movement"),
              scoring: positions(scores),
              coin_rewards: positions(coins),
              rules: {
                team_lock_required: data.has("lock"),
                last_b_gets_steal: data.has("steal"),
              },
              expected_config_revision: setup.config_revision,
              expected_roster_revision: setup.roster_revision,
            };
            void cmd.execute(
              `/v1/admin/seasons/${season}/config-versions${replacement ? `/${replacement}/replace-unused` : ""}`,
              replacement
                ? ({
                    ...body,
                    reason: text(data, "reason"),
                  } satisfies Model<"ReplaceConfigBody">)
                : body,
            );
          }}
        >
          <div className="form-grid">
            <Field label="Nombre de versión">
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={current?.name}
              />
            </Field>
            {[
              ["from", "Primera jornada", 1],
              ["total", "Total de jornadas", 1],
              ["a", "Participantes en A", 1],
              ["b", "Participantes en B", 1],
              ["movement", "Ascensos / descensos", 0],
            ].map(([name, label, min]) => (
              <Field key={name} label={String(label)}>
                <input
                  name={String(name)}
                  type="number"
                  min={Number(min)}
                  defaultValue={
                    (
                      {
                        from: current?.effective_from_matchday,
                        total: current?.total_matchdays,
                        a: current?.division_sizes?.A,
                        b: current?.division_sizes?.B,
                        movement: current?.movement_count,
                      } as Record<string, number | undefined>
                    )[String(name)]
                  }
                  required
                />
              </Field>
            ))}
            <Field label="Puntos por posición, separados por comas">
              <input
                name="points"
                placeholder="10,8,6,4"
                defaultValue={
                  current &&
                  Object.entries(current.scoring)
                    .sort((a, b) => Number(a[0]) - Number(b[0]))
                    .map(([, v]) => v)
                    .join(",")
                }
                pattern="[0-9]+(,[0-9]+)*"
                required
              />
            </Field>
            <Field label="Monedas por posición, separadas por comas">
              <input
                name="coins"
                placeholder="8,6,4,2"
                defaultValue={
                  current &&
                  Object.entries(current.coin_rewards)
                    .sort((a, b) => Number(a[0]) - Number(b[0]))
                    .map(([, v]) => v)
                    .join(",")
                }
                pattern="[0-9]+(,[0-9]+)*"
                required
              />
            </Field>
          </div>
          <label className="check">
            <input
              type="checkbox"
              name="lock"
              defaultChecked={current?.rules.team_lock_required ?? true}
            />
            Team Lock obligatorio
          </label>
          <label className="check">
            <input
              type="checkbox"
              name="steal"
              defaultChecked={current?.rules.last_b_gets_steal ?? false}
            />
            Último de B recibe robo
          </label>
          {replacement && (
            <Field label="Motivo de reemplazo">
              <textarea name="reason" maxLength={500} required />
            </Field>
          )}
          <Submit pending={cmd.pending || cmd.uncertain}>
            {replacement ? "Reemplazar versión sin usar" : "Crear versión"}
          </Submit>
        </form>
      </Card>
      <CommandState command={cmd} />
      <Card>
        <h2>Versiones registradas</h2>
        {setup.config_versions.map((c) => (
          <p key={c.id}>
            {c.name} · desde jornada {c.effective_from_matchday} ·{" "}
            {c.used ? "En uso / histórica" : "Sin usar"}
          </p>
        ))}
      </Card>
    </>
  );
}
function Participants({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    trainers = useRead<Model<"TrainerRead">[]>("/v1/read/trainers"),
    cmd = useCommand(),
    [target, setTarget] = useState("");
  return (
    <>
      <Card>
        <h2>Añadir entrenador</h2>
        <form
          onSubmit={(event) => {
            const data = form(event);
            void cmd.execute(`/v1/admin/seasons/${season}/participants`, {
              trainer_id: text(data, "trainer"),
              expected_roster_revision: setup.roster_revision,
            } satisfies Model<"AddParticipantBody">);
          }}
        >
          <Field label="Entrenador">
            <select name="trainer" required>
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
          <Submit pending={cmd.pending || cmd.uncertain}>
            Añadir a la temporada
          </Submit>
        </form>
        <Notice error={trainers.error} />
      </Card>
      <div className="trainer-grid">
        {setup.participants.map((p) => (
          <Card key={p.id}>
            <h3>{p.display_name}</h3>
            <Tag>{p.status}</Tag>
            <p>
              {p.stats_ready
                ? "Estadísticas disponibles"
                : "Estadísticas pendientes"}
            </p>
            <button onClick={() => setTarget(p.id)}>Gestionar estado</button>
          </Card>
        ))}
      </div>
      <CommandState command={cmd} />
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
              if (
                await cmd.execute(
                  `/v1/admin/seasons/${season}/participants/${target}/${text(data, "action")}`,
                  {
                    reason: text(data, "reason"),
                    expected_roster_revision: setup.roster_revision,
                  },
                )
              )
                setTarget("");
            }}
          >
            <Field label="Acción">
              <select name="action">
                {setup.season.status === "draft" ? (
                  <option value="remove-from-draft">Quitar del borrador</option>
                ) : (
                  <>
                    <option value="retire">Retirada</option>
                    <option value="abandon">Abandono</option>
                    <option value="disqualify">Descalificación</option>
                  </>
                )}
              </select>
            </Field>
            <Field label="Motivo">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <p>
              Se aplicarán las reglas de participación de la temporada. El
              historial se conserva.
            </p>
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain}>
              Confirmar cambio de estado
            </Submit>
          </form>
        </Modal>
      )}
    </>
  );
}
function DayAdmin({ dayId }: { dayId: string }) {
  const { season } = useApp(),
    q = useRead<Model<"DayState">>(
      `/v1/admin/seasons/${season}/matchdays/${dayId}`,
    ),
    ov = useOverview(),
    cmd = useCommand(),
    [confirm, setConfirm] = useState(false),
    [cancel, setCancel] = useState(false);
  if (q.isPending) return <Loading />;
  if (q.error) return <Notice error={q.error} />;
  const day = q.data!,
    base = `/v1/admin/seasons/${season}/matchdays/${dayId}`,
    review = tieReview(cmd.error),
    name = (id: string) => (ov.data ? playerName(ov.data, id) : id);
  return (
    <Card>
      <h2>Jornada · {day.state}</h2>
      <CommandState command={cmd} />
      {day.state === "scheduled" && (
        <button
          disabled={cmd.pending || cmd.uncertain}
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
          <fieldset disabled={cmd.pending || cmd.uncertain}>
            {day.matches.map((m) => (
              <Field
                key={m.id}
                label={
                  ov.data
                    ? `${playerName(ov.data, m.player_a_id)} / ${playerName(ov.data, m.player_b_id)}`
                    : "Enfrentamiento"
                }
              >
                <select name={m.id} defaultValue={m.winner_id || ""} required>
                  <option value="">Pendiente</option>
                  {[m.player_a_id, m.player_b_id].map((id) => (
                    <option key={id} value={id}>
                      {ov.data ? playerName(ov.data, id) : id}
                    </option>
                  ))}
                </select>
              </Field>
            ))}
            <Field label="Motivo de corrección">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <DailyTieFields review={review} name={name} />
            {day.matches.length > 0 && (
              <Submit pending={cmd.pending || cmd.uncertain}>
                Corregir jornada
              </Submit>
            )}
          </fieldset>
        </form>
      )}
      {day.state === "open" && (
        <p>
          Los resultados ordinarios se registran en <Link to="/liga">Liga</Link>
          .
        </p>
      )}
      {day.state === "open" && (
        <div className="toolbar">
          <button className="button primary" onClick={() => setConfirm(true)}>
            Cerrar jornada
          </button>
          <button onClick={() => setCancel(true)}>Cancelar edición</button>
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
              if (
                await cmd.execute(`${base}/cancel-editing`, {
                  expected_revision: day.revision,
                  reason: text(data, "reason"),
                } satisfies Model<"CancelDayBody">)
              )
                setCancel(false);
            }}
          >
            <Field label="Motivo de cancelación">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain}>
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
              if (
                await cmd.execute(`${base}/close`, {
                  expected_results_revision: day.results_revision,
                  ...(resolution ? { tie_resolution: resolution } : {}),
                } satisfies Model<"CloseDayBody">)
              )
                setConfirm(false);
            }}
          >
            <fieldset disabled={cmd.pending || cmd.uncertain}>
              <DailyTieFields review={review} name={name} />
              <Submit pending={cmd.pending || cmd.uncertain}>
                Confirmar cierre
              </Submit>
            </fieldset>
          </form>
          <CommandState command={cmd} />
        </Modal>
      )}
    </Card>
  );
}
function Competition({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    cmd = useCommand(),
    [selected, setSelected] = useState(""),
    ov = useOverview();
  const day = selected || setup.current_matchday_id || "";
  const observedInitial =
    setup.initial_assignment_rule === "observed_deaths_v1";
  return (
    <>
      {observedInitial && <InitialAssignment administrative />}
      <Card>
        <h2>Preparación de la Liga</h2>
        {!observedInitial && (
          <form
            onSubmit={(event) => {
              const data = form(event);
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
            <Field label="Versión de configuración">
              <select name="config" required>
                <option value="">Seleccionar versión</option>
                {setup.config_versions.map((c) => (
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
            <Submit pending={cmd.pending || cmd.uncertain}>
              Guardar divisiones iniciales
            </Submit>
          </form>
        )}
        {observedInitial && setup.season.status === "draft" && (
          <p>
            Activa la Liga para comenzar el primer tramo. Las divisiones y la
            primera jornada se prepararán al confirmar el reparto observado.
          </p>
        )}
        <div className="toolbar">
          {(!observedInitial || setup.current_matchday_id) && (
            <button
              disabled={cmd.pending || cmd.uncertain}
              onClick={() =>
                void cmd.execute(
                  `/v1/admin/seasons/${season}/matchdays/prepare-current`,
                  { expected_setup_revision: setup.setup_revision },
                )
              }
            >
              Preparar jornada
            </button>
          )}
          {setup.season.status === "draft" && (
            <button
              disabled={
                cmd.pending || cmd.uncertain || !setup.readiness.can_activate
              }
              onClick={() =>
                void cmd.execute(`/v1/admin/seasons/${season}/activate`, {
                  expected_setup_revision: setup.setup_revision,
                })
              }
            >
              Activar Liga
            </button>
          )}
          <Link className="button" to="/copa">
            Gestionar Copas →
          </Link>
        </div>
        <CommandState command={cmd} />
      </Card>
      <Field label="Jornada a gestionar">
        <select value={day} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Seleccionar jornada</option>
          {ov.data?.days.map((d) => (
            <option key={d.id} value={d.id}>
              Jornada {d.number} · {d.status}
            </option>
          ))}
        </select>
      </Field>
      {day && <DayAdmin key={day} dayId={day} />}
    </>
  );
}
function Risk({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    cmd = useCommand(),
    [action, setAction] = useState("");
  return (
    <Card className="risk">
      <h2>Zona de riesgo</h2>
      <p>
        Finalizar da por cerrada la Liga. Archivar congela su paquete histórico
        y registra el título en el Hall. Descartar conserva la trazabilidad.
      </p>
      <div className="toolbar">
        {[
          ["archive", "Archivar temporada"],
          ["discard", "Descartar temporada"],
        ].map(([op, label]) => (
          <button className="danger" key={op} onClick={() => setAction(op)}>
            {label}
          </button>
        ))}
      </div>
      {action && (
        <Modal
          title="Confirmar operación de temporada"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setAction("");
          }}
        >
          <p>
            Acción: <strong>{action}</strong> · {setup.season.name}. Revisa la
            temporada seleccionada.
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (text(data, "confirmation") !== setup.season.name) return;
              if (
                await cmd.execute(`/v1/admin/seasons/${season}/${action}`, {
                  expected_revision: setup.setup_revision,
                  ...(action === "discard"
                    ? { reason: text(data, "reason"), confirmation: "DISCARD" }
                    : {}),
                })
              )
                setAction("");
            }}
          >
            {action === "discard" && (
              <Field label="Motivo">
                <textarea name="reason" required maxLength={500} />
              </Field>
            )}
            <Field label={`Escribe ${setup.season.name} para confirmar`}>
              <input name="confirmation" required />
            </Field>
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain}>
              Confirmar operación
            </Submit>
          </form>
        </Modal>
      )}
    </Card>
  );
}
export function AdminPage() {
  const { season } = useApp(),
    q = useRead<Setup>(`/v1/admin/seasons/${season}/setup`, !!season),
    [tab, setTab] = useState("Resumen"),
    [create, setCreate] = useState(false),
    cmd = useCommand();
  return (
    <>
      <Heading
        eyebrow="ADMINISTRACIÓN DE TEMPORADA"
        title="El control, en su sitio."
      >
        Configuración explícita. Acciones trazables.
      </Heading>
      <button className="button" onClick={() => setCreate(true)}>
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
                <Tag>{q.data.season.status}</Tag>
                <p>
                  {q.data.participants.length} participantes ·{" "}
                  {q.data.config_versions.length} versiones de configuración
                </p>
                <h3>Preparación</h3>
                {q.data.readiness.blocking_reasons.length ? (
                  q.data.readiness.blocking_reasons.map((reason) => (
                    <p key={reason}>{reason}</p>
                  ))
                ) : (
                  <p>Sin bloqueos de preparación.</p>
                )}
              </Card>
            ) : tab === "Configuración" ? (
              <Configuration setup={q.data} />
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
                  <Link className="button" to="/liga">
                    Jornadas oficiales
                  </Link>
                  <Link className="button" to="/hall">
                    Hall de la Fama
                  </Link>
                  <Link className="button" to="/juicios">
                    Historial de juicios
                  </Link>
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
