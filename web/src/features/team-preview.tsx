import { Fragment, useState } from "react";
import type { Model } from "../api/types";
import { pokemonName, pokemonTitle } from "../pokemon/localization";
import {
  ItemIcon,
  MovePopover,
  IVBars,
  PokemonSprite,
  PokemonStatusFlags,
  TypeBadge,
  typeClass,
  SpriteGeneration,
  gameGeneration,
} from "../pokemon/presentation";
import { useApp, useOverview, useRead } from "../state";
import { LockStatus } from "./lock-status";
import { Card, Empty, Field, Heading, Loading, Notice, Tag, date } from "../ui";
import { Pokemon, WithSeason } from "./core";
import { FixTeamButton } from "./fix-team";

type Entry = Model<"TeamPreviewRead">["teams"][number];
type ShownPokemon = Model<"PokemonRead"> | Model<"PrivatePokemonRead">;

// 079: Team Preview is always available. Without an official Team Lock the
// trainer's current synchronized party is shown, clearly provisional; an
// official lock is never replaced or mixed with it.
const unavailableText: Record<
  NonNullable<Entry["unavailable_reason"]>,
  string
> = {
  no_team_lock: "No registró Team Lock en esta jornada.",
  no_linked_save: "Aún no tiene una partida vinculada a la Liga.",
  no_synced_save: "Aún no ha sincronizado ninguna partida.",
  processing:
    "Su partida se está procesando. Vuelve a mirar en unos instantes.",
  unsupported_payload:
    "Su última partida no incluye un equipo compatible. Debe volver a sincronizar.",
  ineligible_personal_save:
    "No hay una partida de la Liga disponible para consultar.",
  empty_party: "Su partida sincronizada no tiene Pokémon en el equipo.",
};

type Mode = "spectator" | "battle";
type Selection = { mode: Mode; first?: string; second?: string };

export function BattlePage() {
  const { season } = useApp();
  return (
    <div className="battle-page">
      <Heading eyebrow="BATALLAS" title="Team Preview">
        Equipos de la jornada. Todo lo que necesitas antes de combatir.
      </Heading>
      <WithSeason>
        <Preview key={season} season={season} />
      </WithSeason>
    </div>
  );
}

function Preview({ season }: { season: string }) {
  const { me } = useApp();
  // Each team is drawn in the art of the save its trainer competes with.
  const overview = useOverview();
  const generationOf = (trainer: string) =>
    gameGeneration(
      overview.data?.players.find((p) => p.trainer_id === trainer)?.progress
        ?.game,
    );
  const [selection, setSelection] = useState<Selection>({ mode: "spectator" });
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
  const ready = !query.isPending && !query.error && data ? data : null;
  const spectator = selection.mode === "spectator";
  return (
    <>
      <div className="battle-controls">
        <div className="tabs" role="tablist" aria-label="Modo de Team Preview">
          {(["spectator", "battle"] as const).map((mode) => (
            <button
              key={mode}
              role="tab"
              aria-selected={selection.mode === mode}
              onClick={() => {
                setSelection({ mode, first: first || undefined });
              }}
            >
              {mode === "spectator" ? "Espectador" : "Batalla"}
            </button>
          ))}
        </div>
        {ready && (
          <>
            <Tag>
              {ready.day
                ? `J${ready.day.number} · Team Locks`
                : "Sin jornada preparada · equipos actuales"}
            </Tag>
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
                  {ready.trainers.map((t) => (
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
                    {ready.trainers
                      .filter((t) => t.trainer_id !== first)
                      .map((t) => (
                        <option key={t.trainer_id} value={t.trainer_id}>
                          {t.display_name}
                        </option>
                      ))}
                  </select>
                </Field>
              )}
              {ready.season.status === "active" &&
                ready.trainers.some(
                  (t) =>
                    t.trainer_id === me?.trainer_id && t.status === "active",
                ) && <FixTeamButton />}
            </div>
          </>
        )}
        <p className="battle-mode-hint">
          {spectator
            ? "Compara dos equipos públicos."
            : "Consulta un equipo. Tus detalles privados solo aparecen al elegirte a ti."}
        </p>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice error={query.error} />
      ) : (
        data && (
          <>
            {!data.trainers.length ? (
              <Empty>Aún no hay participantes.</Empty>
            ) : (
              <div className={spectator ? "battle-grid spectator-matchup" : ""}>
                {data.teams.map((entry, index) => (
                  <Fragment key={entry.trainer_id}>
                    {spectator && index === 1 && (
                      <div className="spectator-vs" aria-label="Contra">
                        <span>VS</span>
                      </div>
                    )}
                    <Card
                      className={`battle-side${spectator ? (index === 0 ? " matchup-left" : " matchup-right") : ""}`}
                    >
                      <h2>
                        {
                          data.trainers.find(
                            (t) => t.trainer_id === entry.trainer_id,
                          )?.display_name
                        }
                      </h2>
                      <TeamEntry
                        entry={entry}
                        generation={generationOf(entry.trainer_id)}
                        compact={spectator}
                      />
                    </Card>
                  </Fragment>
                ))}
              </div>
            )}
          </>
        )
      )}
    </>
  );
}

function PrivateDetails({ pokemon }: { pokemon: Model<"PrivatePokemonRead"> }) {
  return (
    <div>
      <h3>IVs</h3>
      <IVBars values={pokemon.ivs} />
    </div>
  );
}

function TeamEntry({
  entry,
  generation,
  compact = false,
}: {
  entry: Entry;
  generation: ReturnType<typeof gameGeneration>;
  // Spectator: both teams face each other on one screen (public fields only).
  compact?: boolean;
}) {
  const self = entry.visibility === "self";
  const Team = compact ? MatchupRoster : Roster;
  if (entry.lock)
    return (
      <>
        <div className="team-source is-official">
          <Tag>
            {self
              ? "Team Lock oficial · tus detalles privados"
              : "Team Lock oficial"}
          </Tag>
        </div>
        <p>
          <LockStatus status={entry.lock.timing_status ?? "unknown"} /> ·{" "}
          {date(entry.lock.locked_at)}
        </p>
        <Team team={entry.lock.team} self={self} generation={generation} />
      </>
    );
  if (entry.provisional)
    return (
      <>
        <div className="team-source is-provisional">
          <Tag>Provisional · equipo actual sin fijar</Tag>
        </div>
        <p className="muted">
          {entry.provisional.source === "personal"
            ? "Última partida personal sincronizada; aún no está vinculada a la Liga. No es un Team Lock."
            : "Equipo actual de su partida oficial. No es un Team Lock: puede cambiar hasta que lo fije."}
        </p>
        <Team
          team={entry.provisional.team}
          self={self}
          generation={generation}
        />
      </>
    );
  return (
    <Empty>
      {entry.unavailable_reason
        ? unavailableText[entry.unavailable_reason]
        : "Sin equipo disponible."}
    </Empty>
  );
}

function Roster({
  team,
  self,
  generation,
}: {
  team: ShownPokemon[];
  self: boolean;
  generation: ReturnType<typeof gameGeneration>;
}) {
  return (
    <SpriteGeneration value={generation}>
      <div className="battle-roster">
        {team.map((pokemon, index) => (
          <article
            className={`battle-pokemon ${typeClass(pokemon.types?.[0])}`}
            key={index}
          >
            <div className="battle-identity">
              <Pokemon pokemon={pokemon} />
              <span className="held-item">
                {pokemon.item && (
                  <ItemIcon
                    name={pokemonName(
                      "item",
                      pokemon.item,
                      pokemon.item_generation ?? undefined,
                    )}
                  />
                )}
                {pokemon.item
                  ? pokemonName(
                      "item",
                      pokemon.item,
                      pokemon.item_generation ?? undefined,
                    )
                  : "Sin objeto"}
              </span>
              {self && "ability" in pokemon && (
                <dl className="battle-private">
                  <dt>Habilidad</dt>
                  <dd>
                    {pokemon.ability
                      ? pokemonName("ability", pokemon.ability)
                      : "—"}
                  </dd>
                  <dt>Naturaleza</dt>
                  <dd>
                    {pokemon.nature
                      ? pokemonName("nature", pokemon.nature)
                      : "—"}
                  </dd>
                </dl>
              )}
            </div>
            <div className="battle-moves" aria-label="Movimientos">
              {Array.from({ length: 4 }, (_, i) =>
                pokemon.moves?.[i] ? (
                  <MovePopover
                    key={i}
                    name={pokemon.moves[i].name}
                    pp={pokemon.moves[i].pp}
                  />
                ) : (
                  <span className="move-vacant" key={i}>
                    No disponible
                  </span>
                ),
              )}
            </div>
            {self && "ability" in pokemon && (
              <details className="battle-values">
                <summary>Ver IVs</summary>
                <PrivateDetails pokemon={pokemon} />
              </details>
            )}
          </article>
        ))}
      </div>
    </SpriteGeneration>
  );
}

// Spectator face-off: the twelve Pokémon of both teams fit one desktop screen.
// Each row keeps exactly the public card's data (sprite, nickname, species,
// level, types, item, public status flags and the four moves with their PP and
// type colour), only laid out densely. Spectator reads are always public: no
// private field (ability, nature, IVs) is ever drawn here.
function MatchupRoster({
  team,
  generation,
}: {
  team: ShownPokemon[];
  self: boolean;
  generation: ReturnType<typeof gameGeneration>;
}) {
  return (
    <SpriteGeneration value={generation}>
      <div className="battle-roster matchup-roster">
        {team.map((pokemon, index) => {
          const item = pokemon.item
            ? pokemonName(
                "item",
                pokemon.item,
                pokemon.item_generation ?? undefined,
              )
            : null;
          return (
            <article
              className={`battle-pokemon matchup-pokemon ${typeClass(pokemon.types?.[0])}`}
              key={index}
            >
              <span className="matchup-sprite">
                <PokemonSprite
                  species={pokemon.species}
                  form={pokemon.form}
                  shiny={pokemon.is_shiny}
                />
              </span>
              <div className="matchup-identity">
                <strong>{pokemonTitle(pokemon)}</strong>
                <span className="matchup-species">
                  {pokemon.nickname
                    ? pokemonName("species", pokemon.species)
                    : "Pokémon"}{" "}
                  · Nv. {pokemon.level ?? "—"}
                  {!!pokemon.form && ` · Forma ${pokemon.form}`}
                </span>
                {!!pokemon.types?.length && (
                  <span className="matchup-types">
                    {pokemon.types.map((t) => (
                      // A tight row shows only the type icon; the name stays
                      // in the badge for assistive technology and on hover.
                      <span
                        className="matchup-type"
                        key={t}
                        title={pokemonName("type", t)}
                      >
                        <TypeBadge type={t} />
                      </span>
                    ))}
                  </span>
                )}
                <span className="held-item">
                  {item && <ItemIcon name={item} />}
                  {item ?? "Sin objeto"}
                </span>
                <PokemonStatusFlags flags={pokemon.status_flags} />
              </div>
              <div className="battle-moves" aria-label="Movimientos">
                {Array.from({ length: 4 }, (_, i) =>
                  pokemon.moves?.[i] ? (
                    <MovePopover
                      key={i}
                      name={pokemon.moves[i].name}
                      pp={pokemon.moves[i].pp}
                    />
                  ) : (
                    <span className="move-vacant" key={i}>
                      No disponible
                    </span>
                  ),
                )}
              </div>
            </article>
          );
        })}
      </div>
    </SpriteGeneration>
  );
}
