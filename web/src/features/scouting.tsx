import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { Card, Empty, Field, Heading, Loading, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import { LockStatus } from "./lock-status";

export function ScoutingPage() {
  const { season } = useApp();
  const { state } = useLocation();
  const initial =
    state?.season === season && typeof state?.trainer === "string"
      ? state.trainer
      : "";
  return (
    <>
      <Heading eyebrow="ENTRENADORES" title="Equipos públicos">
        Explora el equipo fijado para la jornada. No hace falta tener un combate
        programado.
      </Heading>
      <Link to="/entrenadores">Volver a entrenadores</Link>
      <WithSeason>
        <Scouting key={season} season={season} initial={initial} />
      </WithSeason>
    </>
  );
}

function Scouting({ season, initial }: { season: string; initial: string }) {
  const [selected, setSelected] = useState(initial);
  const params = new URLSearchParams();
  if (selected) params.set("trainer_id", selected);
  const query = useRead<Model<"ScoutingRead">>(
    `/v1/read/seasons/${season}/scouting?${params}`,
    !!season,
  );
  const data = query.data;
  if (query.isPending) return <Loading />;
  if (query.error)
    return (
      <>
        <Notice error={query.error} />
        {selected && (
          <button onClick={() => setSelected("")}>
            Volver a elegir entrenador
          </button>
        )}
      </>
    );
  if (!data) return null;
  if (!data.trainers.length)
    return <Empty>No hay entrenadores publicados en esta temporada.</Empty>;
  const trainer = data.trainers.find((t) => t.trainer_id === data.trainer_id);
  return (
    <>
      <p>
        Solo información competitiva pública, también al consultar tu propio
        equipo.
      </p>
      <button disabled={query.isFetching} onClick={() => void query.refetch()}>
        Actualizar equipo público
      </button>
      <Field label="Entrenador a consultar">
        <select
          value={data.trainer_id ?? ""}
          onChange={(e) => setSelected(e.target.value)}
        >
          {data.trainers.map((t) => (
            <option key={t.trainer_id} value={t.trainer_id}>
              {t.display_name}
            </option>
          ))}
        </select>
      </Field>
      {data.day && <Tag>Jornada {data.day.number}</Tag>}
      <Card>
        <h2>{trainer?.display_name ?? "Entrenador no disponible"}</h2>
        <LockStatus
          status={data.team_lock_status ?? (data.team ? "unknown" : "pending")}
        />
        {!data.day ? (
          <Empty>
            No hay una jornada de referencia para consultar equipos públicos.
          </Empty>
        ) : data.team === null ? (
          <Empty>
            No hay un Team Lock público de este entrenador para esta jornada. Su
            equipo aún no está disponible.
          </Empty>
        ) : (
          <>
            <p>
              Equipo público fijado para esta jornada. No representa el estado
              actual de su save.
            </p>
            <div className="trainer-grid">
              {data.team.map((pokemon, index) => (
                <div key={index}>
                  <Pokemon pokemon={pokemon} />
                  {!pokemon.types?.length && <p>Tipos no publicados.</p>}
                  <p>Objeto: {pokemon.item || "No publicado"}</p>
                  {pokemon.moves?.length ? (
                    <ul
                      aria-label={`Movimientos de ${pokemon.nickname || pokemon.species}`}
                    >
                      {pokemon.moves.map((move, i) => (
                        <li key={i}>{move.name}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>Movimientos no publicados.</p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </>
  );
}
