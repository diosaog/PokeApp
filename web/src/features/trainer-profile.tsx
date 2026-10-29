import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Model } from "../api/types";
import { queries, useApp, useMyPC, useOverview, useRead } from "../state";
import { Card, Empty, Heading, Loading, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import {
  SpriteGeneration,
  TrainerPhoto,
  StatPill,
  gameGeneration,
} from "../pokemon/presentation";
import { SaveGame, gameName } from "./progress";
import { TrainerGame, useActiveSaves } from "./trainers";
import { Collection } from "./collection";
import { Inventory } from "./inventory";
import { WipeRevivals } from "./wipe-revivals";
import { PokemonDetailModal } from "./pokemon-details";
import { participantLabel } from "./admin-labels";
import { AccountEditor, type AccountProfile } from "./account-editor";
import { PreferencesCard } from "./preferences";

export function TrainerProfilePage() {
  const { season, accountsEnabled } = useApp(),
    { trainerId = "" } = useParams();
  if (accountsEnabled)
    return <AccountProfileView key={trainerId} trainer={trainerId} />;
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
function AccountProfileView({ trainer }: { trainer: string }) {
  const { me, season, adminOperationPending } = useApp(),
    profile = useRead<AccountProfile>(`/v1/accounts/${trainer}`),
    overview = useOverview();
  const [editing, setEditing] = useState(false);
  if (profile.isPending) return <Loading />;
  if (!profile.data) return <Notice error={profile.error} />;
  const own = trainer === me?.trainer_id,
    member = overview.data?.players.some((p) => p.trainer_id === trainer);
  async function refresh() {
    await queries.invalidateQueries({
      predicate: (q) =>
        q.queryKey[0] === me?.trainer_id &&
        (String(q.queryKey[1]).startsWith("/v1/accounts") ||
          String(q.queryKey[1]) === "/v1/read/trainers" ||
          new RegExp(
            `/seasons/${season}/(overview|league|team-preview|scouting|setup)`,
          ).test(String(q.queryKey[1]))),
    });
  }
  return (
    <>
      <Link className="text-link" to="/entrenadores">
        ← Entrenadores
      </Link>
      {season && overview.isPending ? (
        <Loading />
      ) : member ? (
        <Profile trainer={trainer} account={profile.data} />
      ) : (
        <>
          <Heading
            eyebrow={own ? "TU PERFIL" : "ENTRENADOR"}
            title={profile.data.display_name}
          />
          <Card className="profile-identity">
            <TrainerPhoto
              name={profile.data.display_name}
              url={profile.data.photo_url}
            />
            {overview.error ? (
              <Notice error={overview.error} />
            ) : (
              <p>Sin participación en esta temporada.</p>
            )}
          </Card>
        </>
      )}
      {own && (
        // Personal options, at the very end of the trainer's own profile.
        <section className="profile-personal" aria-label="Opciones personales">
          <button
            className="button primary"
            disabled={adminOperationPending}
            onClick={() => setEditing(!editing)}
          >
            Editar mi perfil
          </button>
          {editing && (
            <AccountEditor profile={profile.data} refresh={refresh} />
          )}
          <PreferencesCard />
        </section>
      )}
    </>
  );
}

export function Profile({
  trainer,
  account,
}: {
  trainer: string;
  account?: AccountProfile;
}) {
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
  // Own profile: the active save, as in «Mi PC» and «Entrenadores».
  const pc = useMyPC(own);
  const active = useActiveSaves();
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
        title={account?.display_name || player.display_name}
      />
      <div className="profile-command-center">
        <Card
          className={`profile-identity ${player.status !== "active" ? "inactive-trainer" : ""}`}
        >
          <TrainerPhoto
            name={account?.display_name || player.display_name}
            url={account?.photo_url}
          />
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
            <TrainerGame
              active={active.get(trainer)}
              seasonProgress={player.progress}
            />
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
          <SaveGame game={pc.data?.save?.game} />
          {pc.seasonGame && (
            <p className="muted">
              La temporada compite con Pokémon {gameName(pc.seasonGame)}.
            </p>
          )}
          <Notice error={pc.error} />
          {pc.isPending && !pc.data ? (
            <Loading />
          ) : pc.data?.status === "ready" ? (
            <SpriteGeneration value={gameGeneration(pc.data.save?.game)}>
              <Collection
                key={pc.data.save?.id}
                slots={pc.data.pokemon}
                deadBox={pc.data.dead_box}
                showDead
                animateTeam
              />
            </SpriteGeneration>
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
              // The official team competes with the season's save.
              <SpriteGeneration value={gameGeneration(player.progress?.game)}>
                <div className="public-party">
                  {rival.data.team.map((pokemon, i) => (
                    <Pokemon
                      key={i}
                      pokemon={pokemon}
                      onClick={() => setSelected(pokemon)}
                      animated
                    />
                  ))}
                </div>
              </SpriteGeneration>
            ) : (
              <Empty>Aún no hay Team Lock.</Empty>
            )}
          </Card>
          <Card className="live-collection-heading">
            <span className="eyebrow">PARTIDA ACTUAL</span>
            <h2>Equipo, cajas y muertos</h2>
            <SaveGame game={collection.data?.game} />
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
            <SpriteGeneration value={gameGeneration(collection.data.game)}>
              <Collection
                slots={collection.data.pokemon}
                visibility="public"
                deadBox={collection.data.dead_box}
                showDead
                animateTeam
              />
            </SpriteGeneration>
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
        <SpriteGeneration value={gameGeneration(player.progress?.game)}>
          <PokemonDetailModal
            visibility="public"
            pokemon={selected}
            onClose={() => setSelected(null)}
          />
        </SpriteGeneration>
      )}
      {/* Without accounts there is no «Editar mi perfil» block: the app
          settings still close the trainer's own profile. */}
      {own && !account && <PreferencesCard />}
    </>
  );
}
