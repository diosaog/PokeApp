import { Link } from "react-router-dom";
import { ArrowUpRight, ShieldCheck, Swords } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, usePC, useRead } from "../state";
import { Card, Heading, Loading, Notice, Tag } from "../ui";
import { PokemonSprite, StatPill, TrainerPhoto } from "../pokemon/presentation";
import { WithSeason, playerName } from "./core";
import { GameProgress } from "./progress";
import { LockStatus } from "./lock-status";

export function HomePage() {
  const { me, season } = useApp(),
    overview = useOverview(),
    pc = usePC();
  const league = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season,
  );
  const data = overview.data,
    day = data?.days.find((d) => d.id === data.season.current_matchday_id);
  const player = data?.players.find((p) => p.trainer_id === me?.trainer_id);
  const row = league.data?.rows.find((r) => r.trainer_id === me?.trainer_id);
  const match = data?.matches.find(
    (m) =>
      m.matchday_id === day?.id &&
      !m.winner_id &&
      (m.player_a_id === player?.id || m.player_b_id === player?.id),
  );
  const lock = data?.locks.find(
    (l) => l.trainer_id === me?.trainer_id && l.matchday_id === day?.id,
  );
  const party =
    pc.data?.status === "ready"
      ? pc.data.pokemon
          .filter((p) => p.location.startsWith("Equipo · "))
          .slice(0, 6)
      : [];
  return (
    <>
      <Heading
        eyebrow="TU CENTRO DE COMPETICIÓN"
        title={`A por la siguiente, ${me?.display_name}.`}
      />
      <WithSeason>
        <Notice error={overview.error} />
        {overview.isPending ? (
          <Loading />
        ) : (
          data && (
            <div className="home-product">
              <Card className="hero home-battle">
                <span className="eyebrow">
                  {data.season.name}
                  {day && ` · JORNADA ${day.number}`}
                </span>
                <div className="hero-content">
                  <Tag>{match ? "PRÓXIMA BATALLA" : "TU LIGA"}</Tag>
                  <h2>
                    {match
                      ? playerName(
                          data,
                          match.player_a_id === player?.id
                            ? match.player_b_id
                            : match.player_a_id,
                        )
                      : "Cada jornada cuenta."}
                  </h2>
                  <p>
                    {match
                      ? "Prepara tu equipo para el próximo enfrentamiento."
                      : "No tienes un enfrentamiento pendiente en la jornada actual."}
                  </p>
                  <Link
                    className="button primary"
                    to={match ? "/battle" : "/liga"}
                  >
                    {match ? "Preparar batalla" : "Ver la jornada"}
                    <ArrowUpRight size={18} />
                  </Link>
                </div>
                <Swords className="hero-art" aria-hidden="true" />
              </Card>
              <Card className="home-stats">
                <div className="section-row">
                  <TrainerPhoto name={me?.display_name || ""} />
                  <div>
                    <span className="eyebrow">TU TEMPORADA</span>
                    <h2>{me?.display_name}</h2>
                  </div>
                </div>
                <Notice error={league.error} />
                <div className="mini-stats">
                  <StatPill label="Puntos" value={row?.total_points} />
                  <StatPill label="Monedas" value={row?.coin_balance} />
                  <StatPill label="Muertos" value={row?.dead_count} />
                </div>
                <Link className="text-link" to="/liga">
                  Ver clasificación →
                </Link>
              </Card>
              <Card className="home-party">
                <div className="section-row">
                  <h2>Tu equipo</h2>
                  <ShieldCheck size={22} />
                </div>
                <LockStatus
                  status={lock ? (lock.timing_status ?? "unknown") : "pending"}
                />
                <p className="caption">Equipo actual del juego</p>
                <div className="home-sprites" aria-label="Equipo de tu partida">
                  {party.map((p, i) => (
                    <PokemonSprite key={i} species={p.pokemon.species} />
                  ))}
                </div>
                <Notice error={pc.error} />
                {!party.length && (
                  <p>
                    {pc.isPending
                      ? "Consultando tu partida…"
                      : "Sincroniza tu partida para ver tu equipo."}
                  </p>
                )}
                <p className="muted">
                  {lock
                    ? "Tu equipo de batalla está fijado para esta jornada."
                    : "Revisa el Team Lock antes de jugar."}
                </p>
                <div className="toolbar">
                  <Link className="text-link" to="/pc">
                    Abrir Mi PC →
                  </Link>
                  <Link className="text-link" to="/battle">
                    Team Preview →
                  </Link>
                </div>
              </Card>
              <Card className="home-progress">
                <h2>Tu aventura</h2>
                <GameProgress progress={player?.progress} />
                <Link className="text-link" to="/saves">
                  Saves y Launcher →
                </Link>
              </Card>
            </div>
          )
        )}
      </WithSeason>
    </>
  );
}
