import type { Model } from "../api/types";
import { queries, useApp, useRead } from "../state";
import { invalidationFor } from "../read-invalidation";
import { Card, Loading, Notice, Tag, date } from "../ui";

const regions = {
  hoenn: "Hoenn",
  kanto: "Kanto",
  sinnoh: "Sinnoh",
  johto: "Johto",
  unova: "Teselia",
};

export function GameProgress({
  progress,
}: {
  progress?: Model<"ProgressRead">;
}) {
  if (!progress || progress.state !== "observed") {
    return <p>Progreso no observado · Pendiente de sincronizar save.</p>;
  }
  return (
    <div>
      <Tag>Progreso observado</Tag>
      <p>{progress.badges_count} medallas observadas</p>
      {progress.regions?.map((region) => (
        <div key={region.region}>
          <strong>{regions[region.region]}</strong>
          <div
            className="badge-strip"
            aria-label={`Medallas de ${regions[region.region]}`}
          >
            {Array.from({ length: 8 }, (_, i) => {
              const earned = region.earned_badges.includes(i + 1);
              const label = `Medalla ${i + 1} de ${regions[region.region]}: ${earned ? "conseguida" : "no conseguida"}`;
              return (
                <span key={i} role="img" aria-label={label} title={label}>
                  {earned ? "◆" : "◇"}
                </span>
              );
            })}
          </div>
        </div>
      ))}
      <p>
        {progress.champion_defeated === true
          ? "Campeón del juego derrotado · Juego completado."
          : progress.champion_defeated === false
            ? "Campeón del juego aún no derrotado."
            : "Victoria ante el Campeón del juego: sin observar."}
      </p>
      {progress.observed_at && (
        <p className="muted">
          Observado en PokeApp el {date(progress.observed_at)}
        </p>
      )}
    </div>
  );
}

export function MyProgress() {
  const { season, me } = useApp();
  const query = useRead<Model<"ProgressRead">>(
    `/v1/read/seasons/${season}/progress`,
    !!season,
  );
  return (
    <Card>
      <h2>Progreso en tu juego</h2>
      <p>
        Medallas → Liga Pokémon → derrotar al Campeón. Ocho medallas no bastan
        para completar el juego.
      </p>
      {query.error ? (
        <Notice error={query.error} />
      ) : query.isPending ? (
        <Loading />
      ) : (
        <GameProgress progress={query.data} />
      )}
      <button
        className="button secondary"
        disabled={query.isFetching}
        onClick={() =>
          void queries.invalidateQueries({
            predicate: invalidationFor(
              me?.trainer_id,
              `/v1/seasons/${season}/progress`,
            ),
          })
        }
      >
        Actualizar progreso
      </button>
      <p className="muted">
        Estas son observaciones del save registrado en PokeApp. No determinan el
        título de tu Liga competitiva.
      </p>
    </Card>
  );
}
