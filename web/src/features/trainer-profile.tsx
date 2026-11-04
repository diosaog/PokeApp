import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Model } from "../api/types";
import { useApp, useMyPC, useOverview, useRead } from "../state";
import { Card, Empty, Heading, Loading, Notice, Tag } from "../ui";
import { Pokemon, WithSeason } from "./core";
import {
  SpriteGeneration,
  TrainerPhoto,
  gameGeneration,
} from "../pokemon/presentation";
import { SaveGame, gameName } from "./progress";
import { TrainerGame, useActiveSaves } from "./trainers";
import { Collection } from "./collection";
import { Inventory } from "./inventory";
import { WipeRevivals } from "./wipe-revivals";
import { PokemonDetailModal } from "./pokemon-details";
import { ShowdownExport } from "./showdown-export";
import { participantLabel } from "./admin-labels";
import { type AccountProfile } from "./account-editor";
import { TrainerLeagueStats } from "./trainer-league-stats";
import { FixTeamButton } from "./fix-team";
import { OwnDeathHistory } from "./league-start";

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
// Personal settings (name, photo, PIN, sound, animations) live in the «Mi
// perfil» dialog of the sidebar; the trainer page is about the trainer.
function AccountProfileView({ trainer }: { trainer: string }) {
  const { me, season } = useApp(),
    profile = useRead<AccountProfile>(`/v1/accounts/${trainer}`),
    overview = useOverview();
  if (profile.isPending) return <Loading />;
  if (!profile.data) return <Notice error={profile.error} />;
  const own = trainer === me?.trainer_id,
    member = overview.data?.players.some((p) => p.trainer_id === trainer);
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
          {own && <OwnSave />}
        </>
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
  // «Licencia de entrenador» (the card's printed label, see evolution.css).
  const licence = (
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
        <TrainerLeagueStats row={row} />
        <TrainerGame
          active={active.get(trainer)}
          seasonProgress={player.progress}
        />
      </div>
    </Card>
  );
  return (
    <>
      <Heading
        eyebrow={own ? "TU PERFIL" : "ENTRENADOR"}
        title={account?.display_name || player.display_name}
      />
      <div className="profile-command-center">
        {own ? (
          // The licence and, just under it, the trainer's own wipe counter.
          // Other trainers' profiles never carry this editor.
          <div className="profile-licence-column">
            {licence}
            {league.data && <WipeRevivals data={league.data} />}
            {player.status === "active" && <OwnDeathHistory />}
          </div>
        ) : (
          licence
        )}
        {own && (
          <aside className="profile-inventory">
            <Inventory />
          </aside>
        )}
      </div>
      <Notice error={league.error} />
      {own ? (
        <OwnSave league={player.status === "active"} />
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
            {collection.data?.source === "personal" && (
              <p>
                Partida personal sincronizada; todavía no está vinculada a esta
                Liga. No es un Team Lock.
              </p>
            )}
            <p>
              Revividos tras wipe en la Liga:{" "}
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
              <Empty>{collectionReason(collection.data?.reason)}</Empty>
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
    </>
  );
}

function OwnSave({ league = false }: { league?: boolean }) {
  const pc = useMyPC();
  // An active participant fixes the team shown here for the League.
  const fix = league ? <FixTeamButton shownPersonal={pc.personal} /> : null;
  return (
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
            partyCenter={fix}
            partyAction={
              // The team displayed right here, never a Team Lock snapshot.
              pc.data.save &&
              pc.data.pokemon.some((s) =>
                s.location.startsWith("Equipo · "),
              ) && <ShowdownExport save={pc.data.save} personal={pc.personal} />
            }
          />
        </SpriteGeneration>
      ) : (
        <>
          <Empty>
            Tu equipo y tus cajas aparecerán al sincronizar tu partida.{" "}
            <Link to="/saves">Abrir Saves y Launcher →</Link>
          </Empty>
          {fix}
        </>
      )}
    </>
  );
}

function collectionReason(reason?: Model<"TrainerCollectionRead">["reason"]) {
  switch (reason) {
    case "processing":
      return "La partida vinculada se está preparando. Vuelve a consultar en unos instantes.";
    case "unsupported_payload":
      return "La observación guardada no incluye un equipo y cajas compatibles. Sincroniza de nuevo desde el Launcher.";
    case "ineligible_personal_save":
      return "No hay una partida vinculada a esta Liga disponible para consultar. Las partidas personales de participantes inactivos no se publican aquí.";
    case "no_synced_save":
      return "Este participante aún no tiene una partida sincronizada ni vinculada a esta Liga.";
    default:
      return "Este participante aún no tiene una partida vinculada a la Liga.";
  }
}
