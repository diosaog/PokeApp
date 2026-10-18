import type { Model } from "../api/types";
import { queries, useApp, useRead } from "../state";
import { invalidationFor } from "../read-invalidation";
import { Card, Loading, Notice, Tag, date } from "../ui";
import { gameRegion } from "../pokemon/badges";
import { BadgeIcon } from "../pokemon/presentation";

const regions: Record<string, string> = {
  kalos: "Kalos",
  hoenn: "Hoenn",
  kanto: "Kanto",
  sinnoh: "Sinnoh",
  johto: "Johto",
  unova: "Teselia",
};
const games: Record<string, string> = {
  R: "Rubí",
  S: "Zafiro",
  E: "Esmeralda",
  FR: "Rojo Fuego",
  LG: "Verde Hoja",
  D: "Diamante",
  P: "Perla",
  Pt: "Platino",
  HG: "HeartGold",
  SS: "SoulSilver",
  B: "Negro",
  W: "Blanco",
  B2: "Negro 2",
  W2: "Blanco 2",
  X: "X",
  Y: "Y",
  OR: "Rubí Omega",
  AS: "Zafiro Alfa",
  SN: "Sol",
  MN: "Luna",
  US: "Ultrasol",
  UM: "Ultraluna",
};

export function SaveGame({ game }: { game?: string | null }) {
  return game && games[game] ? (
    <p className="caption">Pokémon {games[game]}</p>
  ) : null;
}

export function GameProgress({
  progress,
  compact = false,
}: {
  progress?: Model<"ProgressRead">;
  compact?: boolean;
}) {
  if (!progress || progress.state !== "observed") {
    return (
      <div className="progress-unknown">
        <p className="muted">
          {compact
            ? "Progreso no observado"
            : "Progreso no observado · Pendiente de sincronizar save."}
        </p>
        {progress?.game && gameRegion[progress.game] && (
          <div className="badge-strip" aria-label="Medallas sin observar">
            {Array.from({ length: 8 }, (_, i) => (
              <BadgeIcon
                key={i}
                region={gameRegion[progress.game!]}
                game={progress.game}
                number={i + 1}
                earned={null}
                label={`Medalla ${i + 1}: sin observar`}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
  return (
    <div>
      {compact && !progress.regions?.length && (
        <p>
          {progress.badges_count == null
            ? "Medallas no disponibles"
            : `${progress.badges_count} medallas observadas`}
        </p>
      )}
      {!compact && (
        <>
          {progress.game && games[progress.game] && (
            <p className="game-context">Pokémon {games[progress.game]}</p>
          )}
          <Tag>Progreso observado</Tag>
          <p>{progress.badges_count} medallas observadas</p>
        </>
      )}
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
                <BadgeIcon
                  key={i}
                  game={progress.game}
                  region={region.region}
                  number={i + 1}
                  earned={earned}
                  label={label}
                />
              );
            })}
          </div>
        </div>
      ))}
      {!compact && (
        <p>
          {progress.champion_defeated === true
            ? "Campeón del juego derrotado · Juego completado."
            : progress.champion_defeated === false
              ? "Campeón del juego aún no derrotado."
              : "Victoria ante el Campeón del juego: sin observar."}
        </p>
      )}
      {!compact && progress.observed_at && (
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
    </Card>
  );
}
