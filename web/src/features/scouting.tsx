import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { Empty, Field, Heading, Loading, Notice } from "../ui";
import { WithSeason } from "./core";
import { Profile } from "./trainer-profile";
import { TrainerPhoto } from "../pokemon/presentation";

export function ScoutingPage() {
  const { season } = useApp();
  const { state } = useLocation();
  const initial =
    state?.season === season && typeof state?.trainer === "string"
      ? state.trainer
      : "";
  return (
    <>
      <Heading eyebrow="ENTRENADORES" title="Scouting">
        Explora equipos, cajas, medallas y el recorrido de cada entrenador.
      </Heading>
      <Link className="text-link back-link" to="/entrenadores">
        Volver a entrenadores
      </Link>
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
  return (
    <>
      {/* One click on a rival portrait; the labelled list stays for keyboards. */}
      <div className="scout-roster" role="group" aria-label="Rivales">
        {data.trainers.map((t) => (
          <button
            key={t.trainer_id}
            type="button"
            className="scout-chip"
            aria-pressed={t.trainer_id === data.trainer_id}
            data-sfx="select"
            onClick={() => setSelected(t.trainer_id)}
          >
            <TrainerPhoto name={t.display_name} />
            <span>{t.display_name}</span>
          </button>
        ))}
      </div>
      <div className="scout-controls">
        <button
          disabled={query.isFetching}
          onClick={() => void query.refetch()}
        >
          Actualizar scouting
        </button>
        <p className="muted">
          La partida actual y el equipo oficial tienen su propio espacio.
        </p>
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
      </div>
      {data.trainer_id && (
        <Profile key={data.trainer_id} trainer={data.trainer_id} />
      )}
    </>
  );
}
