import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { LockKeyhole } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import { Card, Empty, Heading, Loading, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import { TrainerPhoto, StatPill } from "../pokemon/presentation";
import { GameProgress } from "./progress";
import { Collection } from "./collection";
import { PokemonDetailModal } from "./pokemon-details";
import { participantLabel } from "./admin-labels";

export function TrainerProfilePage() {
  const { season } = useApp(),
    { trainerId = "" } = useParams();
  return (
    <>
      <Link className="text-link" to="/entrenadores">
        ← Entrenadores
      </Link>
      <WithSeason>
        <Profile key={`${season}:${trainerId}`} trainer={trainerId} />
      </WithSeason>
    </>
  );
}
function Profile({ trainer }: { trainer: string }) {
  const { season, me } = useApp(),
    own = trainer === me?.trainer_id,
    overview = useOverview();
  const league = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season,
  );
  const rival = useRead<Model<"ScoutingRead">>(
    `/v1/read/seasons/${season}/scouting?trainer_id=${encodeURIComponent(trainer)}`,
    !!season && !own,
  );
  const pc = useRead<Model<"PCRead">>(
    `/v1/read/seasons/${season}/pc`,
    !!season && own,
  );
  const [selected, setSelected] = useState<
    NonNullable<Model<"ScoutingRead">["team"]>[number] | null
  >(null);
  const player = overview.data?.players.find((p) => p.trainer_id === trainer),
    row = league.data?.rows.find((r) => r.trainer_id === trainer);
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
      <Card
        className={`profile-identity ${player.status !== "active" ? "inactive-trainer" : ""}`}
      >
        <TrainerPhoto name={player.display_name} />
        <div>
          <div className="tags">
            {own && <Tag>TÚ</Tag>}
            {player.status !== "active" && (
              <Tag>{participantLabel(player.status)}</Tag>
            )}
          </div>
          <div className="mini-stats">
            <StatPill label="Puntos" value={row?.total_points} />
            <StatPill label="Monedas" value={row?.coin_balance} />
            <StatPill label="Muertos" value={row?.dead_count ?? "—"} />
          </div>
          <GameProgress progress={player.progress} compact />
          {own && (
            <Link className="text-link" to="/tienda">
              Ver mi inventario →
            </Link>
          )}
        </div>
      </Card>
      <Notice error={league.error} />
      {own ? (
        <>
          <Notice error={pc.error} />
          {pc.isPending ? (
            <Loading />
          ) : pc.data?.status === "ready" ? (
            <Collection
              key={pc.data.save?.id}
              slots={pc.data.pokemon}
              showDead
            />
          ) : (
            <Empty>
              Tu equipo y tus cajas aparecerán al sincronizar tu partida.{" "}
              <Link to="/saves">Abrir Saves y Launcher →</Link>
            </Empty>
          )}
        </>
      ) : (
        <>
          <Card>
            <div className="section-row">
              <h2>Equipo</h2>
              <Tag>Equipo de la jornada</Tag>
            </div>
            {rival.isPending ? (
              <Loading />
            ) : rival.error ? (
              <Notice error={rival.error} />
            ) : rival.data?.team?.length ? (
              <div className="public-party">
                {rival.data.team.map((pokemon, i) => (
                  <Pokemon
                    key={i}
                    pokemon={pokemon}
                    onClick={() => setSelected(pokemon)}
                  />
                ))}
              </div>
            ) : (
              <Empty>Este entrenador aún no ha fijado su equipo.</Empty>
            )}
          </Card>
          <div className="private-sections">
            <Card>
              <LockKeyhole size={20} />
              <h2>Cajas</h2>
              <p>Las cajas de este entrenador son privadas.</p>
            </Card>
            <Card>
              <LockKeyhole size={20} />
              <h2>Muertos</h2>
              <p>
                {row?.dead_count == null
                  ? "Sin observar"
                  : `${row.dead_count} Pokémon muertos`}
                . El detalle de la caja es privado.
              </p>
            </Card>
          </div>
        </>
      )}
      {selected && (
        <PokemonDetailModal
          visibility="public"
          pokemon={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
