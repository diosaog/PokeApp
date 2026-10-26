import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Box,
  Crown,
  HardDrive,
  Medal,
  Scale,
  ShieldCheck,
  ShoppingBag,
  Swords,
  Trophy,
  Users,
} from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, usePC, useRead } from "../state";
import { Card, Loading, Notice } from "../ui";
import {
  PokemonSprite,
  PokemonStatusFlags,
  StatPill,
  TrainerPhoto,
} from "../pokemon/presentation";
import { WithSeason, playerName } from "./core";
import { GameProgress, SaveGame } from "./progress";
import { desktopPath, insideLauncher } from "../launcher";
import { LockStatus } from "./lock-status";

// Game-style main menu: every tile is an existing route, nothing new. Each
// tile wears its area's signal colour (tile-<area>, see design/tokens.css).
const tiles = [
  ["/liga", "Liga", "Clasificación y jornadas", Trophy],
  ["/battle", "Batallas", "Team Preview y combate", Swords],
  ["/copa", "Copa", "Eliminatorias", Crown],
  ["/pc", "Mi PC", "Equipo y cajas", Box],
  ["/tienda", "Tienda", "Objetos y comodines", ShoppingBag],
  ["/entrenadores", "Entrenadores", "Rivales y scouting", Users],
  ["/hall", "Hall de la Fama", "Campeones", Medal],
  ["/juicios", "Juicios", "Decisiones de la Liga", Scale],
  ["/saves", "Saves y Launcher", "Tu partida en PokeApp", HardDrive],
] as const;
export function ArenaMenu() {
  // Inside PokeApp Launcher the save tile opens the desktop save tool itself.
  const desktop = insideLauncher();
  return (
    <nav aria-label="Menú de PokeApp">
      <ul className="arena-menu">
        {tiles.map(([to, label, detail, Icon]) => {
          const [href, name, note] =
            desktop && to === "/saves"
              ? [
                  desktopPath("partida"),
                  "Mi partida",
                  "Tu partida en este equipo",
                ]
              : [to, label, detail];
          return (
            <li key={to}>
              <Link to={href} className={`tile-${to.slice(1)}`}>
                <span className="tile-icon" aria-hidden="true">
                  <Icon size={28} strokeWidth={2.4} />
                </span>
                {name}
                <small>{note}</small>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

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
  const rival = match
    ? playerName(
        data!,
        match.player_a_id === player?.id
          ? match.player_b_id
          : match.player_a_id,
      )
    : null;
  return (
    <>
      {/* Night-stadium effects behind the whole screen: floodlight beams and
          camera flashes in the stands. Decorative only. */}
      <div className="stadium-fx" aria-hidden="true">
        <span className="beam left" />
        <span className="beam right" />
        {Array.from({ length: 9 }, (_, i) => (
          <i key={i} />
        ))}
      </div>
      {/* The stadium: who you are, how your season goes and the team you bring. */}
      <section className="home-stage" aria-labelledby="home-title">
        <div className="stage-copy">
          <TrainerPhoto name={me?.display_name || ""} />
          <div>
            <span className="eyebrow">TU CENTRO DE COMPETICIÓN</span>
            <h1 id="home-title">A por la siguiente, {me?.display_name}.</h1>
            {data && (
              <p className="stage-season">
                {data.season.name}
                {day && ` · Jornada ${day.number}`}
              </p>
            )}
          </div>
        </div>
        {data && (
          <div className="home-stats stage-hud">
            <StatPill label="Puntos" value={row?.total_points} />
            <StatPill label="Monedas" value={row?.coin_balance} />
            <StatPill label="Muertos" value={row?.dead_count} />
            <Link className="text-link" to="/liga">
              Clasificación →
            </Link>
          </div>
        )}
        <Notice error={league.error} />
        {data && (
          <div className="home-party stage-team">
            <div className="stage-team-head">
              <h2>
                <ShieldCheck size={18} aria-hidden="true" /> Tu equipo
              </h2>
              <LockStatus
                status={lock ? (lock.timing_status ?? "unknown") : "pending"}
              />
              <SaveGame game={pc.data?.save?.game} />
            </div>
            <div className="home-sprites" aria-label="Equipo de tu partida">
              {party.map((p, i) => (
                <span className="home-sprite-slot" key={i}>
                  <PokemonSprite
                    species={p.pokemon.species}
                    form={p.pokemon.form}
                    animated
                  />
                  {!!p.pokemon.form && <small>Forma {p.pokemon.form}</small>}
                  <PokemonStatusFlags flags={p.pokemon.status_flags} />
                </span>
              ))}
            </div>
            <Notice error={pc.error} />
            {!party.length && (
              <p className="stage-empty">
                {pc.isPending
                  ? "Consultando tu partida…"
                  : "Sincroniza tu partida para ver tu equipo."}
              </p>
            )}
            <p className="caption">
              {lock
                ? "Tu equipo de batalla está fijado para esta jornada."
                : "Equipo actual del juego · revisa el Team Lock antes de jugar."}
            </p>
            <div className="toolbar">
              <Link className="text-link" to="/pc">
                Abrir Mi PC →
              </Link>
              <Link className="text-link" to="/battle">
                Team Preview →
              </Link>
            </div>
          </div>
        )}
      </section>
      <ArenaMenu />
      <WithSeason>
        <Notice error={overview.error} />
        {overview.isPending ? (
          <Loading />
        ) : (
          data && (
            <div className="home-product">
              <Card className="hero home-battle">
                <span className="eyebrow">
                  {match ? "PRÓXIMA BATALLA" : "TU LIGA"}
                  {day && ` · JORNADA ${day.number}`}
                </span>
                {rival ? (
                  <div className="versus" aria-label={`Tú contra ${rival}`}>
                    <span className="versus-side">
                      <TrainerPhoto name={me?.display_name || ""} />
                      <strong>{me?.display_name}</strong>
                    </span>
                    <span className="versus-badge" aria-hidden="true">
                      VS
                    </span>
                    <span className="versus-side rival">
                      <TrainerPhoto name={rival} />
                      <strong>{rival}</strong>
                    </span>
                  </div>
                ) : (
                  <h2>Cada jornada cuenta.</h2>
                )}
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
                <Swords className="hero-art" aria-hidden="true" />
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
