import { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { Model } from "../api/types";
import { queries, useApp, useRead, usePC } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Heading,
  Loading,
  Modal,
  Notice,
  Tag,
  date,
  useCommand,
} from "../ui";
import { Pokemon, WithSeason } from "./core";
import { TeamLockWarning } from "./team-lock-warning";

type Mode = "spectator" | "battle";
type Selection = { mode: Mode; first?: string; second?: string };

export function BattlePage() {
  const { season } = useApp();
  return (
    <>
      <Heading eyebrow="BATALLAS" title="Team Preview">
        Consulta los equipos fijados para la jornada, aunque no tengan un
        enfrentamiento programado.
      </Heading>
      <WithSeason>
        <Preview key={season} season={season} />
      </WithSeason>
    </>
  );
}

function Preview({ season }: { season: string }) {
  const { me } = useApp();
  const [selection, setSelection] = useState<Selection>({ mode: "spectator" });
  const [confirm, setConfirm] = useState(false);
  const params = new URLSearchParams({ mode: selection.mode });
  if (selection.first) params.set("trainer_id", selection.first);
  if (selection.second) params.set("second_trainer_id", selection.second);
  const query = useRead<Model<"TeamPreviewRead">>(
    `/v1/read/seasons/${season}/team-preview?${params}`,
    !!season,
  );
  const data = query.data;
  const first =
    selection.first ??
    data?.teams[0]?.trainer_id ??
    data?.trainers[0]?.trainer_id ??
    "";
  const second = selection.second ?? data?.teams[1]?.trainer_id ?? "";
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Modo de Team Preview">
        {(["spectator", "battle"] as const).map((mode) => (
          <button
            key={mode}
            role="tab"
            aria-selected={selection.mode === mode}
            onClick={() => {
              setSelection({ mode, first: first || undefined });
              setConfirm(false);
            }}
          >
            {mode === "spectator" ? "Espectador" : "Batalla"}
          </button>
        ))}
      </div>
      <p>
        {selection.mode === "spectator"
          ? "Dos entrenadores, solo información pública, también al seleccionar tu propio equipo."
          : "Selecciona un entrenador. Solo tu propio Team Lock muestra sus detalles privados."}
      </p>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice error={query.error} />
      ) : (
        data && (
          <>
            {data.day && <Tag>J{data.day.number} · Team Locks</Tag>}
            <div className="toolbar">
              <Field
                label={
                  selection.mode === "spectator"
                    ? "Primer entrenador"
                    : "Entrenador"
                }
              >
                <select
                  value={first}
                  onChange={(e) =>
                    setSelection({
                      ...selection,
                      first: e.target.value,
                      second:
                        e.target.value === second
                          ? undefined
                          : selection.mode === "spectator"
                            ? second || undefined
                            : undefined,
                    })
                  }
                >
                  {data.trainers.map((t) => (
                    <option key={t.trainer_id} value={t.trainer_id}>
                      {t.display_name}
                    </option>
                  ))}
                </select>
              </Field>
              {selection.mode === "spectator" && (
                <Field label="Segundo entrenador">
                  <select
                    value={second}
                    onChange={(e) =>
                      setSelection({
                        mode: "spectator",
                        first,
                        second: e.target.value,
                      })
                    }
                  >
                    {data.trainers
                      .filter((t) => t.trainer_id !== first)
                      .map((t) => (
                        <option key={t.trainer_id} value={t.trainer_id}>
                          {t.display_name}
                        </option>
                      ))}
                  </select>
                </Field>
              )}
              <button
                className="button primary"
                onClick={() => setConfirm(true)}
                disabled={
                  !data.day ||
                  !["scheduled", "open"].includes(data.day.status) ||
                  data.season.status !== "active" ||
                  !data.trainers.some(
                    (t) =>
                      t.trainer_id === me?.trainer_id && t.status === "active",
                  )
                }
              >
                <ShieldCheck size={18} />
                Fijar mi equipo
              </button>
            </div>
            {!data.trainers.length ? (
              <Empty>Aún no hay participantes.</Empty>
            ) : !data.day ? (
              <Empty>
                Aún no hay una jornada disponible para consultar Team Locks.
              </Empty>
            ) : (
              <div
                className={selection.mode === "spectator" ? "battle-grid" : ""}
              >
                {data.teams.map((entry) => (
                  <Card key={entry.trainer_id} className="battle-side">
                    <h2>
                      {
                        data.trainers.find(
                          (t) => t.trainer_id === entry.trainer_id,
                        )?.display_name
                      }
                    </h2>
                    {!entry.lock ? (
                      <TeamLockWarning />
                    ) : (
                      <>
                        <Tag>
                          {entry.visibility === "self"
                            ? "Tu equipo · detalles privados"
                            : "Equipo público"}
                        </Tag>
                        <p>
                          {entry.lock.is_late
                            ? "Team Lock tardío"
                            : "Team Lock confirmado"}{" "}
                          · {date(entry.lock.locked_at)}
                        </p>
                        {entry.lock.team.map((pokemon, index) => (
                          <div key={index}>
                            <Pokemon pokemon={pokemon} />
                            <p>Objeto: {pokemon.item || "Sin objeto"}</p>
                            <div className="moves">
                              {pokemon.moves?.map((m, i) => (
                                <span key={i}>
                                  {m.name}
                                  {m.pp != null && ` · ${m.pp} PP`}
                                </span>
                              ))}
                            </div>
                            {entry.visibility === "self" && (
                              <PrivateDetails
                                pokemon={entry.lock!.team[index]}
                              />
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </Card>
                ))}
              </div>
            )}
            {confirm && data.day && (
              <LockConfirmation
                season={season}
                day={data.day.id}
                onClose={() => setConfirm(false)}
              />
            )}
          </>
        )
      )}
    </>
  );
}

function PrivateDetails({ pokemon }: { pokemon: Model<"PrivatePokemonRead"> }) {
  return (
    <>
      <dl className="details">
        <dt>Habilidad</dt>
        <dd>{pokemon.ability || "—"}</dd>
        <dt>Naturaleza</dt>
        <dd>{pokemon.nature || "—"}</dd>
      </dl>
      {(["ivs", "evs"] as const).map((key) => (
        <div key={key}>
          <h3>{key.toUpperCase()}</h3>
          {pokemon[key] ? (
            <dl className="stats-list">
              {Object.entries(pokemon[key]!).map(([stat, value]) => (
                <div key={stat}>
                  <dt>{stat}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p>No disponible en este Team Lock.</p>
          )}
        </div>
      ))}
    </>
  );
}

function LockConfirmation({
  season,
  day,
  onClose,
}: {
  season: string;
  day: string;
  onClose: () => void;
}) {
  // The live save is consulted only for the existing explicit lock command,
  // never as a replacement for a missing competitive preview.
  const pc = usePC();
  const cmd = useCommand([`/v1/read/seasons/${season}/overview`]);
  const refreshed = useRef(false);
  useEffect(() => {
    if (!cmd.success || cmd.pending || refreshed.current) return;
    refreshed.current = true;
    // This also runs after an explicit retry with an initially unknown outcome.
    void queries
      .invalidateQueries({
        predicate: (q) =>
          String(q.queryKey[1]).startsWith(
            `/v1/read/seasons/${season}/team-preview?`,
          ),
      })
      .then(onClose);
  }, [cmd.success, cmd.pending, season, onClose]);
  return (
    <Modal
      title="Confirmar Team Lock"
      onClose={() => {
        if (!cmd.pending && !cmd.uncertain) onClose();
      }}
    >
      <p>
        Se fijará el equipo del save actual. El servidor comprobará la jornada,
        los seis Pokémon y tu elegibilidad.
      </p>
      {pc.isPending ? (
        <Loading />
      ) : pc.error ? (
        <Notice error={pc.error} />
      ) : pc.data?.save && pc.data.status === "ready" ? (
        <button
          className="button primary"
          disabled={cmd.pending || cmd.uncertain}
          onClick={async () => {
            await cmd.execute(
              `/v1/seasons/${season}/matchdays/${day}/team-lock`,
              { save_file_id: pc.data!.save!.id },
              "PUT",
            );
          }}
        >
          Confirmar mi equipo
        </button>
      ) : (
        <Empty>
          No hay un save actual analizado disponible para fijar tu equipo.
        </Empty>
      )}
      <CommandState command={cmd} />
    </Modal>
  );
}
