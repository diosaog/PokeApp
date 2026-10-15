import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import { Card, Empty, Heading, Loading, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import { TrainerPhoto, StatPill } from "../pokemon/presentation";
import { GameProgress } from "./progress";
import { Collection } from "./collection";
import { Inventory } from "./inventory";
import { WipeRevivals } from "./wipe-revivals";
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
export function Profile({ trainer }: { trainer: string }) {
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
  const collection = useRead<Model<"TrainerCollectionRead">>(
    `/v1/read/seasons/${season}/trainers/${trainer}/collection`,
    !!season && !own,
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
      <div className="profile-command-center">
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
          </div>
        </Card>
        {own && (
          <aside className="profile-inventory">
            <Inventory />
          </aside>
        )}
      </div>
      <Notice error={league.error} />
      {own && league.data && (
        <details className="profile-wipe">
          <summary>Revividos tras wipe · consultar o actualizar</summary>
          <WipeRevivals data={league.data} />
        </details>
      )}
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
              <h2>Equipo oficial</h2>
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
              <Empty>
                Aún no hay Team Lock. Puedes consultar su partida sincronizada
                más abajo.
              </Empty>
            )}
          </Card>
          <Card className="live-collection-heading">
            <span className="eyebrow">PARTIDA ACTUAL</span>
            <h2>Equipo, cajas y muertos</h2>
            <p>
              Última partida sincronizada. El equipo oficial de la jornada se
              conserva por separado.
            </p>
            <p>
              Revividos tras wipe:{" "}
              <strong>
                {collection.data?.revived_after_wipe ?? "Sin observar"}
              </strong>
            </p>
          </Card>
          <Notice error={collection.error} />
          {collection.isPending ? (
            <Loading />
          ) : collection.data?.status === "ready" ? (
            <Collection
              slots={collection.data.pokemon}
              visibility="public"
              showDead
            />
          ) : (
            !collection.error && (
              <Empty>
                Este entrenador todavía no tiene una partida disponible para
                consulta.
              </Empty>
            )
          )}
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
