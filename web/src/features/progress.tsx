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

export const gameName = (game?: string | null) =>
  (game && games[game]) || game || "desconocido";

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
      {compact &&
        !progress.regions?.length &&
        progress.native_model !== "island_challenge" && (
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
          {progress.native_model !== "island_challenge" && (
            <p>{progress.badges_count} medallas observadas</p>
          )}
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
      {progress.native_model === "island_challenge" && (
        <div>
          <strong>Recorrido insular</strong>
          <p className="muted">Sellos de las islas observados en tu partida.</p>
          <div className="badge-strip" aria-label="Sellos de las islas">
            {(
              [
                ["melemele", "Melemele"],
                ["akala", "Akala"],
                ["ulaula", "Ula-Ula"],
                ["poni", "Poni"],
              ] as const
            ).map(([id, name]) => (
              <Tag key={id}>
                {name}:{" "}
                {progress.completed_islands?.includes(id)
                  ? "conseguido"
                  : "no conseguido"}
              </Tag>
            ))}
          </div>
          {!compact && (
            <p>
              {progress.island_challenge_completed === true
                ? "Recorrido insular completado."
                : progress.island_challenge_completed === false
                  ? "Recorrido insular aún no completado."
                  : "Final del recorrido insular: sin observar."}
            </p>
          )}
        </div>
      )}
      {!compact && (
        <p>
          {progress.champion_defeated === true
            ? progress.native_model === "island_challenge"
              ? "Título de Campeón de Alola registrado."
              : "Campeón del juego derrotado · Juego completado."
            : progress.champion_defeated === false
              ? "Campeón del juego aún no derrotado."
              : "Victoria ante el Campeón del juego: sin observar."}
        </p>
      )}
      {!compact && progress.native_model === "gym_badges" && (
        <>
          <p>
            {progress.hall_of_fame_entered === true
              ? "Entrada en el Salón de la Fama registrada."
              : progress.hall_of_fame_entered === false
                ? "Sin entrada en el Salón de la Fama."
                : "Salón de la Fama: sin observar."}
          </p>
          {(progress.league_visited === true ||
            progress.league_fly_unlocked === true) && (
            <p>
              Liga Pokémon:{" "}
              {progress.league_visited === true
                ? "lugar visitado"
                : "destino de Vuelo desbloqueado"}
              .
            </p>
          )}
          <p className="muted">
            El acceso a los combates de la Liga no está verificado.
          </p>
        </>
      )}
      {!compact && progress.reward_state && (
        <p className="muted">
          {progress.reward_state === "pending_validation"
            ? "Las recompensas de progreso de este juego están pendientes de validación."
            : "El recorrido insular no da monedas por medalla; vencer al Campeón sí da la recompensa de juego completado."}
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
