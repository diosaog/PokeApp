import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import { Card, Empty, Heading, Loading, Modal, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import { GameProgress } from "./progress";
import { LockStatus } from "./lock-status";
import { PokemonDetails, type DetailPokemon } from "./pokemon-details";
import { participantLabel } from "./admin-labels";

export function TrainerProfilePage() {
  const { season } = useApp(),
    { trainerId = "" } = useParams();
  return (
    <>
      <Link to="/entrenadores">← Entrenadores</Link>
      <WithSeason>
        <Profile key={`${season}:${trainerId}`} trainer={trainerId} />
      </WithSeason>
    </>
  );
}
function Profile({ trainer }: { trainer: string }) {
  const { season, me } = useApp(),
    own = trainer === me?.trainer_id;
  const overview = useOverview(),
    league = useRead<Model<"LeagueGeneralRead">>(
      `/v1/read/seasons/${season}/league`,
      !!season,
    );
  const publicTeam = useRead<Model<"ScoutingRead">>(
    `/v1/read/seasons/${season}/scouting?trainer_id=${encodeURIComponent(trainer)}`,
    !!season && !own,
  );
  const selfTeam = useRead<Model<"TeamPreviewRead">>(
    `/v1/read/seasons/${season}/team-preview?mode=battle&trainer_id=${encodeURIComponent(trainer)}`,
    !!season && own,
  );
  const [selected, setSelected] = useState<DetailPokemon | null>(null);
  const player = overview.data?.players.find((p) => p.trainer_id === trainer),
    row = league.data?.rows.find((p) => p.trainer_id === trainer);
  const dayNumber = overview.data?.days.find(
    (d) => d.id === overview.data?.season.current_matchday_id,
  )?.number;
  const membership = overview.data?.memberships.find(
    (m) =>
      m.season_player_id === player?.id &&
      dayNumber != null &&
      m.effective_from_matchday_number <= dayNumber &&
      (m.effective_to_matchday_number == null ||
        m.effective_to_matchday_number >= dayNumber) &&
      (m.eligibility_ends_before_matchday_number == null ||
        dayNumber < m.eligibility_ends_before_matchday_number),
  );
  const division = overview.data?.divisions.find(
    (d) => d.id === membership?.division_id,
  );
  const entry = selfTeam.data?.teams.find(
    (t) => t.trainer_id === trainer && t.visibility === "self",
  );
  const mons: DetailPokemon[] = own
    ? entry?.visibility === "self"
      ? (entry.lock?.team.map((pokemon) => ({
          visibility: "self" as const,
          pokemon,
        })) ?? [])
      : []
    : (publicTeam.data?.team?.map((pokemon) => ({
        visibility: "public" as const,
        pokemon,
      })) ?? []);
  const teamQuery = own ? selfTeam : publicTeam;
  const status = own
    ? (entry?.lock?.timing_status ?? (entry?.lock ? "unknown" : "pending"))
    : (publicTeam.data?.team_lock_status ?? "pending");
  if (overview.isPending) return <Loading />;
  if (overview.error) return <Notice error={overview.error} />;
  if (!player)
    return <Empty>Este entrenador no está en la temporada seleccionada.</Empty>;
  return (
    <>
      <Heading
        eyebrow={own ? "TU PERFIL" : "ENTRENADOR"}
        title={player.display_name}
      />
      <div className="trainer-top">
        <Tag>{participantLabel(player.status)}</Tag>
        {division && <Tag>División {division.name}</Tag>}
        {own && (
          <Link className="button" to="/pc">
            Abrir mi PC
          </Link>
        )}
      </div>
      <Notice error={league.error} />
      {row && (
        <div className="quick-grid">
          <Card>
            <span>Puntos totales</span>
            <h2>{row.total_points}</h2>
          </Card>
          <Card>
            <span>Pokémon muertos</span>
            <h2>{row.dead_count ?? "Sin observar"}</h2>
          </Card>
          {own && (
            <Card>
              <span>Monedas</span>
              <h2>{row.coin_balance} PK₽</h2>
              <Link to="/tienda">Mi inventario →</Link>
            </Card>
          )}
        </div>
      )}
      <Card>
        <h2>Progreso</h2>
        <GameProgress progress={player.progress} />
      </Card>
      <Card>
        <h2>Equipo de la jornada</h2>
        {teamQuery.error ? (
          <Notice error={teamQuery.error} />
        ) : teamQuery.isPending ? (
          <Loading />
        ) : (
          <>
            <LockStatus status={status} />
            <p>Team Lock competitivo de la jornada.</p>
            {mons.length ? (
              <div className="pokemon-grid">
                {mons.map((detail, i) => (
                  <div key={i}>
                    <Pokemon
                      pokemon={detail.pokemon}
                      onClick={() => setSelected(detail)}
                    />
                    <button
                      className="button secondary"
                      onClick={() => setSelected(detail)}
                    >
                      Ver detalles
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <Empty>
                No hay un equipo fijado disponible.
                {own && (
                  <>
                    {" "}
                    <Link to="/battle">Fijar mi equipo →</Link>
                  </>
                )}
              </Empty>
            )}
          </>
        )}
      </Card>
      {selected && (
        <Modal
          title={selected.pokemon.nickname || selected.pokemon.species}
          onClose={() => setSelected(null)}
        >
          <PokemonDetails {...selected} />
        </Modal>
      )}
    </>
  );
}
