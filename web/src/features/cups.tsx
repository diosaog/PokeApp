import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Crown, ArrowUpRight } from "lucide-react";
import { useApp, useOverview, useRead } from "../state";
import type { Cup, Model } from "../api/types";
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
import { WithSeason } from "./core";

const formats = {
  swiss: "Suiza + Top Cut",
  elimination: "Eliminatoria",
  doubles: "Dobles",
};
function CupForm({ cup, onClose }: { cup?: Cup; onClose: () => void }) {
  const { season } = useApp(),
    overview = useOverview(),
    cmd = useCommand(),
    [format, setFormat] = useState<Model<"CupCreateBody">["format"]>(
      cup?.format || "swiss",
    ),
    [rows, setRows] = useState(cup?.sides.length || 4);
  return (
    <Modal
      title={cup ? "Editar Copa" : "Crear Copa"}
      onClose={() => {
        if (!cmd.pending && !cmd.uncertain) onClose();
      }}
    >
      <form
        onSubmit={async (event) => {
          const data = form(event);
          const body: Model<"CupCreateBody"> = {
            name: text(data, "name"),
            format,
            swiss_rounds: number(data, "rounds") || 1,
            sides: Array.from({ length: rows }, (_, i) => ({
              name: text(data, `name-${i}`),
              trainer_ids: [
                text(data, `a-${i}`),
                ...(format === "doubles" ? [text(data, `b-${i}`)] : []),
              ],
            })),
          };
          if (
            await cmd.execute(
              `/v1/admin/seasons/${season}/cups${cup ? `/${cup.id}/setup` : ""}`,
              cup ? { ...body, expected_revision: cup.revision } : body,
              cup ? "PUT" : "POST",
            )
          )
            onClose();
        }}
      >
        <Field label="Nombre de la Copa">
          <input
            name="name"
            defaultValue={cup?.name}
            required
            maxLength={120}
          />
        </Field>
        <Field label="Formato">
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as typeof format)}
          >
            {Object.entries(formats).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        {format === "swiss" && (
          <Field label="Rondas suizas">
            <input
              name="rounds"
              type="number"
              min={1}
              max={10}
              defaultValue={cup?.swiss_rounds || 3}
              required
            />
          </Field>
        )}
        <Field
          label={
            format === "doubles"
              ? "Número de equipos"
              : "Número de participantes"
          }
        >
          <input
            type="number"
            min={format === "swiss" ? 4 : 2}
            max={format === "doubles" ? 16 : 64}
            value={rows}
            onChange={(e) =>
              setRows(Math.max(0, Math.min(64, Number(e.target.value))))
            }
          />
        </Field>
        {Array.from({ length: rows }, (_, i) => (
          <fieldset key={i}>
            <legend>
              {format === "doubles" ? "Equipo" : "Participante"} {i + 1}
            </legend>
            <Field label="Nombre">
              <input
                name={`name-${i}`}
                required
                maxLength={120}
                defaultValue={cup?.sides[i]?.name}
              />
            </Field>
            {(format === "doubles" ? ["a", "b"] : ["a"]).map((slot, j) => (
              <Field key={slot} label={`Entrenador ${j + 1}`}>
                <select
                  name={`${slot}-${i}`}
                  required
                  defaultValue={cup?.sides[i]?.members[j]?.trainer_id || ""}
                >
                  <option value="">Seleccionar</option>
                  {overview.data?.players.map((p) => (
                    <option key={p.id} value={p.trainer_id}>
                      {p.display_name} · {p.status}
                    </option>
                  ))}
                </select>
              </Field>
            ))}
          </fieldset>
        ))}
        <Notice error={overview.error} />
        <CommandState command={cmd} />
        <Submit pending={cmd.pending || cmd.uncertain}>Guardar Copa</Submit>
      </form>
    </Modal>
  );
}
function CupDetail({ id }: { id: string }) {
  const { season, me } = useApp(),
    query = useRead<Cup>(`/v1/seasons/${season}/cups/${id}`, !!season),
    cmd = useCommand(),
    [edit, setEdit] = useState(false),
    [action, setAction] = useState<{ op: string; side?: string } | null>(null),
    [correction, setCorrection] = useState<number | null>(null);
  const base = `/v1/admin/seasons/${season}/cups/${id}`;
  if (query.isPending) return <Loading />;
  if (query.error) return <Notice error={query.error} />;
  const cup = query.data!,
    name = (id: string | null) =>
      cup.sides.find((s) => s.id === id)?.name || "Bye",
    active = cup.status === "active";
  return (
    <>
      <div className="toolbar">
        <Link to="/copa">← Todas las Copas</Link>
        <Tag>
          {formats[cup.format]} · {cup.status}
        </Tag>
      </div>
      <h2>{cup.name}</h2>
      <CommandState command={cmd} />
      {me?.is_admin && (
        <div className="toolbar">
          {cup.status === "draft" && (
            <>
              <button onClick={() => setEdit(true)}>
                Editar participantes
              </button>
              <button
                className="button primary"
                onClick={() => setAction({ op: "start" })}
              >
                Iniciar Copa
              </button>
            </>
          )}
          {active && (
            <button
              className="button primary"
              onClick={() => setAction({ op: "finalize" })}
            >
              Certificar campeón y finalista
            </button>
          )}
          {["active", "draft"].includes(cup.status) && (
            <button
              className="danger"
              onClick={() => setAction({ op: "discard" })}
            >
              Cancelar Copa
            </button>
          )}
        </div>
      )}
      {cup.certificate_id && (
        <Card className="certificate">
          <Crown />
          <h2>{name(cup.champion_side_id ?? null)}</h2>
          <p>
            Campeón certificado · Finalista:{" "}
            {name(cup.finalist_side_id ?? null)}
          </p>
          <Link to="/hall">Ver Hall de la Fama →</Link>
        </Card>
      )}
      <div className="cup-rounds">
        {cup.rounds.map((round) => (
          <Card key={round.number}>
            <div className="section-row">
              <h3>
                Ronda {round.number} · {round.phase}
              </h3>
              <Tag>{round.status}</Tag>
            </div>
            <form
              onSubmit={async (event) => {
                const data = form(event);
                const results: Model<"CupResultBody">[] = round.matches
                  .filter((m) => text(data, m.id))
                  .map((m) => {
                    const value = text(data, m.id);
                    return value.includes(":")
                      ? {
                          match_id: m.id,
                          score_a: Number(value[0]),
                          score_b: Number(value[2]),
                        }
                      : { match_id: m.id, winner_side_id: value };
                  });
                const body: Model<"CupResultsBody"> = {
                  expected_revision: cup.revision,
                  results,
                };
                const correct = correction === round.number;
                await cmd.execute(
                  `${base}/rounds/${round.number}/${correct ? "correct" : "results"}`,
                  correct ? { ...body, reason: text(data, "reason") } : body,
                  correct ? "POST" : "PUT",
                );
              }}
            >
              {round.matches.map((m) => (
                <div key={m.id} className="cup-match">
                  <div>
                    <span className={m.winner === m.a ? "winner" : ""}>
                      {name(m.a)}
                    </span>
                    <span className="muted">
                      {m.score_a ?? "—"} : {m.score_b ?? "—"}
                    </span>
                    <span className={m.winner === m.b ? "winner" : ""}>
                      {name(m.b)}
                    </span>
                  </div>
                  <Tag>{m.status}</Tag>
                  {me?.is_admin &&
                    active &&
                    m.a &&
                    m.b &&
                    (correction === round.number
                      ? m.status === "completed"
                      : m.status === "scheduled") &&
                    (round.status === "open" ||
                      correction === round.number) && (
                      <Field label={`Resultado ${name(m.a)} / ${name(m.b)}`}>
                        <select name={m.id} defaultValue="">
                          <option value="">Sin cambios</option>
                          {cup.format === "swiss" && round.phase === "swiss" ? (
                            <>
                              <option value={m.a}>{name(m.a)}</option>
                              <option value={m.b}>{name(m.b)}</option>
                            </>
                          ) : (
                            ["2:0", "2:1", "1:2", "0:2"].map((score) => (
                              <option key={score} value={score}>
                                {score}
                              </option>
                            ))
                          )}
                        </select>
                      </Field>
                    )}
                </div>
              ))}
              {me?.is_admin &&
                active &&
                (round.status === "open" || correction === round.number) && (
                  <>
                    {correction === round.number && (
                      <Field label="Motivo de corrección">
                        <input name="reason" required maxLength={500} />
                      </Field>
                    )}
                    <Submit pending={cmd.pending || cmd.uncertain}>
                      {correction === round.number
                        ? "Corregir resultados"
                        : "Guardar resultados"}
                    </Submit>
                  </>
                )}
            </form>
            {me?.is_admin && active && (
              <div className="toolbar">
                {round.status === "open" ? (
                  <button
                    disabled={cmd.pending || cmd.uncertain}
                    onClick={() =>
                      setAction({ op: `rounds/${round.number}/close` })
                    }
                  >
                    Cerrar ronda y continuar
                  </button>
                ) : (
                  <button
                    onClick={() =>
                      setCorrection(
                        correction === round.number ? null : round.number,
                      )
                    }
                  >
                    Corregir esta ronda
                  </button>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
      {cup.standings.length > 0 && (
        <Card>
          <h2>Clasificación</h2>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Pos.</th>
                  <th>Participante</th>
                  <th>V / D</th>
                  <th>Byes</th>
                  <th>Buchholz</th>
                </tr>
              </thead>
              <tbody>
                {cup.standings.map((s) => (
                  <tr key={s.side_id}>
                    <td>{s.position}</td>
                    <td>{name(s.side_id)}</td>
                    <td>
                      {s.wins} / {s.losses}
                    </td>
                    <td>{s.byes}</td>
                    <td>{s.buchholz}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      <h2>Participantes</h2>
      <div className="trainer-grid">
        {cup.sides.map((s) => (
          <Card key={s.id}>
            <Tag>
              Seed {s.seed} · {s.status}
            </Tag>
            <h3>{s.name}</h3>
            <p>{s.members.map((m) => m.display_name).join(" & ")}</p>
            {me?.is_admin && active && s.status === "active" && (
              <button
                className="danger"
                onClick={() =>
                  setAction({
                    op: `participants/${s.id}/disqualify`,
                    side: s.name,
                  })
                }
              >
                Descalificar
              </button>
            )}
          </Card>
        ))}
      </div>
      {edit && <CupForm cup={cup} onClose={() => setEdit(false)} />}
      {action && (
        <Modal
          title={
            action.op === "discard"
              ? "Cancelar Copa"
              : action.side
                ? `Descalificar ${action.side}`
                : "Confirmar acción de Copa"
          }
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setAction(null);
          }}
        >
          <p>
            {action.op === "discard"
              ? "La Copa quedará cancelada y conservará su historial."
              : action.op === "finalize"
                ? "Se certificarán el campeón y el finalista y se registrará el resultado en el Hall."
                : "Se aplicará el cambio a la revisión actual de la Copa."}
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                await cmd.execute(`${base}/${action.op}`, {
                  expected_revision: cup.revision,
                  ...(action.side || action.op === "discard"
                    ? { reason: text(data, "reason") }
                    : {}),
                  ...(action.op === "discard"
                    ? { confirmation: "DISCARD" }
                    : {}),
                })
              )
                setAction(null);
            }}
          >
            {(action.side || action.op === "discard") && (
              <Field label="Motivo">
                <textarea name="reason" required maxLength={500} />
              </Field>
            )}
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain}>Confirmar</Submit>
          </form>
        </Modal>
      )}
    </>
  );
}
export function CupsPage() {
  const { season, setSeason, me } = useApp(),
    params = useParams(),
    [search] = useSearchParams(),
    [create, setCreate] = useState(false);
  const id = params["*"] || "";
  const target = search.get("season");
  useEffect(() => {
    if (target && /^[a-f0-9-]{36}$/i.test(target)) setSeason(target);
  }, [target, setSeason]);
  const list = useRead<Model<"CupSummary">[]>(
    `/v1/seasons/${season}/cups`,
    !!season,
  );
  return (
    <>
      <Heading eyebrow="OTRA FORMA DE HACER HISTORIA" title="La Copa.">
        Suiza + Top Cut, eliminatoria y dobles. Sigue cada ronda.
      </Heading>
      <WithSeason>
        {id ? (
          <CupDetail key={`${season}:${id}`} id={id} />
        ) : (
          <>
            {me?.is_admin && (
              <button
                className="button primary"
                onClick={() => setCreate(true)}
              >
                Crear Copa
              </button>
            )}
            <Notice error={list.error} />
            {list.isPending ? (
              <Loading />
            ) : list.data?.length ? (
              <div className="trainer-grid">
                {list.data.map((c) => (
                  <Link
                    key={c.id}
                    className="card action-card"
                    to={`/copa/${c.id}`}
                  >
                    <Crown />
                    <div>
                      <Tag>
                        {formats[c.format]} · {c.status}
                      </Tag>
                      <h2>{c.name}</h2>
                    </div>
                    <ArrowUpRight />
                  </Link>
                ))}
              </div>
            ) : (
              <Empty>No hay Copas en esta temporada.</Empty>
            )}
          </>
        )}
      </WithSeason>
      {create && <CupForm onClose={() => setCreate(false)} />}
    </>
  );
}
