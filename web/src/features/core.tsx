import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Coins,
  ShieldCheck,
  Swords,
  Trophy,
  Box,
  HardDrive,
  Sparkles,
  Crown,
  ShoppingBag,
} from "lucide-react";
import type { Model, Overview } from "../api/types";
import { useApp, useRead, useOverview, usePC } from "../state";
import { Inventory } from "./inventory";
import { ParticipantResults } from "./league-results";
import { InitialAssignment } from "./initial-assignment";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Heading,
  Loading,
  Modal,
  Notice,
  Submit,
  Tag,
  date,
  useCommand,
} from "../ui";

export function WithSeason({ children }: { children: ReactNode }) {
  const { season } = useApp();
  return season ? (
    <>{children}</>
  ) : (
    <Empty>
      Selecciona una temporada para continuar. Si aún no hay ninguna, un
      administrador puede crearla.
    </Empty>
  );
}
function OverviewState({
  children,
}: {
  children: (data: Overview) => ReactNode;
}) {
  const query = useOverview();
  return (
    <WithSeason>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice error={query.error} />
      ) : (
        query.data && children(query.data)
      )}
    </WithSeason>
  );
}
export function playerName(data: Overview, id: string | null) {
  return (
    data.players.find((p) => p.id === id)?.display_name || "Por determinar"
  );
}
const currentDay = (data: Overview) =>
  data.days.find((d) => d.id === data.season.current_matchday_id);
export function Pokemon({
  pokemon,
  onClick,
}: {
  pokemon: Model<"PokemonRead">;
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="mon-emblem" aria-hidden="true">
        {pokemon.species.slice(0, 2).toUpperCase()}
      </div>
      <div>
        <strong>{pokemon.nickname || pokemon.species}</strong>
        <span className="muted">
          {pokemon.nickname ? pokemon.species : "Pokémon"} · Nv.{" "}
          {pokemon.level ?? "—"}
        </span>
        <div className="tags">
          {pokemon.types?.map((t) => (
            <Tag key={t}>{t}</Tag>
          ))}
          {pokemon.is_shiny && <Sparkles size={15} />}
        </div>
      </div>
      {onClick && <ArrowUpRight size={18} />}
    </>
  );
  return onClick ? (
    <button className="pokemon" onClick={onClick}>
      {body}
    </button>
  ) : (
    <div className="pokemon">{body}</div>
  );
}
export function HomePage() {
  const { me } = useApp();
  const pc = usePC();
  return (
    <>
      <Heading
        eyebrow="TU CENTRO DE COMPETICIÓN"
        title={`A por la siguiente, ${me?.display_name}.`}
      >
        Todo listo para tu próxima jornada.
      </Heading>
      <OverviewState>
        {(data) => {
          const day = currentDay(data),
            player = data.players.find((p) => p.trainer_id === me?.trainer_id),
            match = data.matches.find(
              (m) =>
                m.matchday_id === day?.id &&
                !m.winner_id &&
                (m.player_a_id === player?.id || m.player_b_id === player?.id),
            ),
            lock = data.locks.find(
              (l) =>
                l.trainer_id === me?.trainer_id && l.matchday_id === day?.id,
            );
          const membership = data.memberships.find(
            (m) =>
              m.season_player_id === player?.id &&
              day &&
              m.effective_from_matchday_number <= day.number &&
              (m.effective_to_matchday_number == null ||
                m.effective_to_matchday_number >= day.number) &&
              (m.eligibility_ends_before_matchday_number == null ||
                day.number < m.eligibility_ends_before_matchday_number),
          );
          return (
            <>
              <div className="home-grid">
                <section className="hero card">
                  <span className="eyebrow">
                    <i className="live-dot" />{" "}
                    {day ? `JORNADA ${day.number}` : "TEMPORADA"} ·{" "}
                    {data.season.name}
                  </span>
                  <div className="hero-content">
                    <Tag>PRÓXIMA BATALLA</Tag>
                    <h2>
                      {match
                        ? playerName(
                            data,
                            match.player_a_id === player?.id
                              ? match.player_b_id
                              : match.player_a_id,
                          )
                        : "Tu próximo desafío te espera."}
                    </h2>
                    <p>
                      {match
                        ? "Un rival. Una oportunidad de subir. Prepara tu equipo y entra en la jornada."
                        : "No tienes un enfrentamiento pendiente en la jornada actual."}
                    </p>
                    <Link className="button primary" to="/battle">
                      {match ? "Preparar batalla" : "Ver la jornada"}
                      <ArrowUpRight size={18} />
                    </Link>
                  </div>
                  <Swords className="hero-art" aria-hidden="true" />
                </section>
                <Card className="readiness">
                  <ShieldCheck size={27} />
                  <span className="eyebrow">TU EQUIPO</span>
                  <h2>{lock ? "Equipo fijado." : "¿Listo para combatir?"}</h2>
                  <p>
                    {lock
                      ? "El Team Lock de esta jornada está registrado."
                      : "Revisa tu save disponible y confirma el Team Lock antes de jugar."}
                  </p>
                  <Link className="text-link" to="/battle">
                    Revisar Team Preview <ArrowUpRight size={16} />
                  </Link>
                </Card>
              </div>
              <div className="stat-grid">
                <Card>
                  <Coins />
                  <span className="eyebrow">MONEDAS</span>
                  <strong className="stat-number">
                    {data.balance ?? "—"} <small>PK₽</small>
                  </strong>
                  <Link to="/tienda">Visitar la tienda →</Link>
                </Card>
                <Card>
                  <Trophy />
                  <span className="eyebrow">DIVISIÓN</span>
                  <strong className="stat-number">
                    {data.divisions.find(
                      (d) => d.id === membership?.division_id,
                    )?.code ?? "—"}
                  </strong>
                  <Link to="/liga">Ver clasificación →</Link>
                </Card>
                <Card>
                  <HardDrive />
                  <span className="eyebrow">SAVE EN POKEAPP</span>
                  <strong className="stat-word">
                    {pc.data?.save
                      ? "Disponible"
                      : pc.isPending
                        ? "Consultando…"
                        : "Sin save actual"}
                  </strong>
                  <Link to="/saves">Ver estado →</Link>
                </Card>
              </div>
              <div className="section-row">
                <h2>Tu siguiente movimiento</h2>
                <span className="caption">FUERA DEL CAMPO</span>
              </div>
              <div className="quick-grid">
                <Link className="card action-card" to="/pc">
                  <Box />
                  <div>
                    <h3>Tu PC, a mano</h3>
                    <p>Consulta tu equipo y tus cajas.</p>
                  </div>
                  <ArrowUpRight />
                </Link>
                <Link className="card action-card" to="/copa">
                  <Crown />
                  <div>
                    <h3>Una Copa. Otra historia.</h3>
                    <p>Rondas, clasificación y Top Cut.</p>
                  </div>
                  <ArrowUpRight />
                </Link>
              </div>
              <Notice error={pc.error} />
            </>
          );
        }}
      </OverviewState>
    </>
  );
}
function LeagueState({
  children,
}: {
  children: (data: Model<"LeagueGeneralRead">) => ReactNode;
}) {
  const { season } = useApp();
  const query = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season,
  );
  return (
    <WithSeason>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice error={query.error} />
      ) : (
        query.data && children(query.data)
      )}
    </WithSeason>
  );
}
function dailyPosition(row: Model<"StandingRead">, division = false) {
  const start = division ? row.division_position : row.position;
  if (row.tie_status === "unresolved_neutral" && row.position_end != null) {
    const end = start + row.position_end - row.position;
    return `${start}.º–${end}.º · empate`;
  }
  return String(start);
}
function LeagueDay({ dayId }: { dayId: string }) {
  const { me } = useApp();
  return (
    <OverviewState>
      {(data) => {
        const snapshot = data.snapshots.find((s) => s.matchday_id === dayId);
        const canRecord =
          data.season.status === "active" &&
          data.season.current_matchday_id === dayId &&
          data.days.some((d) => d.id === dayId && d.status === "open") &&
          data.players.some(
            (p) => p.trainer_id === me?.trainer_id && p.status === "active",
          );
        return (
          <>
            <Tag>
              {snapshot
                ? `Oficial · revisión ${snapshot.revision}`
                : "Aún sin clasificación oficial"}
            </Tag>
            {snapshot ? (
              <>
                <div className="podium">
                  {[...snapshot.standings]
                    .sort((a, b) => a.position - b.position)
                    .filter((s) => s.position <= 3)
                    .map((s) => (
                      <Card key={s.season_player_id}>
                        <Trophy />
                        <span className="eyebrow">
                          POSICIÓN {dailyPosition(s)}
                        </span>
                        <h2>{playerName(data, s.season_player_id)}</h2>
                        <strong>
                          {s.points_awarded} <small>puntos de jornada</small>
                        </strong>
                      </Card>
                    ))}
                </div>
                {["A", "B"].map((division) => (
                  <Card key={division}>
                    <h2>División {division}</h2>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Pos.</th>
                            <th>Entrenador</th>
                            <th>Puntos de jornada</th>
                          </tr>
                        </thead>
                        <tbody>
                          {snapshot.standings
                            .filter((s) => s.division === division)
                            .sort(
                              (a, b) =>
                                a.division_position - b.division_position,
                            )
                            .map((s) => (
                              <tr key={s.season_player_id}>
                                <td>{dailyPosition(s, true)}</td>
                                <td>{playerName(data, s.season_player_id)}</td>
                                <td>{s.points_awarded}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                ))}
              </>
            ) : (
              <Empty>
                La clasificación aparecerá cuando se cierre esta jornada.
              </Empty>
            )}
            <h2>Enfrentamientos</h2>
            {canRecord ? (
              <ParticipantResults
                key={`${data.season.id}:${dayId}`}
                data={data}
                dayId={dayId}
              />
            ) : (
              <>
                <div className="match-grid">
                  {data.matches
                    .filter((m) => m.matchday_id === dayId)
                    .map((m) => (
                      <Card key={m.id}>
                        <Tag>{m.status}</Tag>
                        <h3>
                          {playerName(data, m.player_a_id)}{" "}
                          <span className="muted">vs</span>{" "}
                          {playerName(data, m.player_b_id)}
                        </h3>
                        <p>
                          {m.winner_id
                            ? `Victoria de ${playerName(data, m.winner_id)}`
                            : "Resultado pendiente"}
                        </p>
                      </Card>
                    ))}
                </div>
              </>
            )}
          </>
        );
      }}
    </OverviewState>
  );
}
function LeagueGeneral({ data }: { data: Model<"LeagueGeneralRead"> }) {
  if (!data.rows.length) return <Empty>Aún no hay participantes.</Empty>;
  const states: Record<string, string> = {
    retired: "Retirado",
    abandoned: "Abandono",
    disqualified: "Descalificado",
  };
  return (
    <Card>
      <h2>Clasificación general</h2>
      <p>
        Puntos acumulados de las jornadas oficiales, con sus penalizaciones. Las
        monedas son el saldo actual. El orden entre puntos iguales no resuelve
        un desempate.
      </p>
      <div
        className="table-scroll"
        tabIndex={0}
        aria-label="Clasificación general, tabla desplazable"
      >
        <table className="league-standings">
          <thead>
            <tr>
              <th>Entrenador</th>
              <th>Puntos totales</th>
              <th>Monedas</th>
              <th>Pokémon muertos</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => {
              const source = data.days.find(
                (d) => d.id === row.points_source_matchday_id,
              );
              return (
                <tr key={row.season_player_id}>
                  <td>
                    {row.display_name}
                    {states[row.status] && (
                      <span className="muted"> · {states[row.status]}</span>
                    )}
                  </td>
                  <td>
                    {row.total_points}
                    <small className="muted standings-source">
                      {row.points_source_matchday_id
                        ? source
                          ? `Hasta J${source.number}`
                          : "Captura oficial"
                        : "Sin jornadas oficiales"}
                    </small>
                  </td>
                  <td>{row.coin_balance}</td>
                  <td>
                    {row.dead_count ?? "Desconocido"}
                    {row.dead_count_observed_at && (
                      <small className="muted standings-source">
                        {date(row.dead_count_observed_at)}
                      </small>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted">
        Muertos: ocupantes observados de la Caja 8 del save seleccionado. Sin
        una observación completa, el recuento es desconocido. Esta columna no
        incluye revividos ni modifica puntos ya cerrados.
      </p>
    </Card>
  );
}
export function LeaguePage() {
  const [selected, setSelected] = useState({ season: "", day: "" });
  return (
    <>
      <Heading eyebrow="LA CARRERA POR EL TÍTULO" title="Cada punto cuenta.">
        Resultados oficiales, congelados al cerrar cada jornada.
      </Heading>
      <LeagueState>
        {(data) => {
          const days = data.days
              .filter(
                (d) =>
                  d.status === "closed" ||
                  d.id === data.season.current_matchday_id,
              )
              .sort((a, b) => a.number - b.number),
            day =
              selected.season === data.season.id
                ? days.find((d) => d.id === selected.day)
                : undefined;

          return (
            <>
              {data.season.initial_assignment_rule === "observed_deaths_v1" &&
                !data.days.length && <InitialAssignment />}
              <nav className="tabs" aria-label="Vistas de Liga">
                <button
                  aria-pressed={!day}
                  onClick={() =>
                    setSelected({ season: data.season.id, day: "" })
                  }
                >
                  GENERAL
                </button>
                {days.map((d) => (
                  <button
                    key={d.id}
                    aria-pressed={day?.id === d.id}
                    onClick={() =>
                      setSelected({ season: data.season.id, day: d.id })
                    }
                  >
                    J{d.number}
                  </button>
                ))}
              </nav>
              {!day ? (
                <LeagueGeneral data={data} />
              ) : (
                <>
                  <LeagueDay dayId={day.id} />
                </>
              )}
            </>
          );
        }}
      </LeagueState>
    </>
  );
}
export function BattlePage() {
  const { me, season } = useApp(),
    pc = usePC(),
    cmd = useCommand(),
    [confirm, setConfirm] = useState(false),
    [selected, setSelected] = useState("");
  return (
    <>
      <Heading eyebrow="BATTLE · TEAM PREVIEW" title="Conoce el campo.">
        El equipo público es el fijado para esta jornada.
      </Heading>
      <OverviewState>
        {(data) => {
          const day = currentDay(data),
            matches = data.matches.filter((m) => m.matchday_id === day?.id),
            own = data.players.find((p) => p.trainer_id === me?.trainer_id),
            match =
              matches.find((m) => m.id === selected) ||
              matches.find(
                (m) => m.player_a_id === own?.id || m.player_b_id === own?.id,
              ) ||
              matches[0];
          return (
            <>
              <div className="toolbar">
                <Field label="Enfrentamiento">
                  <select
                    value={match?.id || ""}
                    onChange={(e) => setSelected(e.target.value)}
                  >
                    {matches.map((m) => (
                      <option key={m.id} value={m.id}>
                        {playerName(data, m.player_a_id)} vs{" "}
                        {playerName(data, m.player_b_id)}
                      </option>
                    ))}
                  </select>
                </Field>
                <button
                  className="button primary"
                  disabled={
                    !pc.data?.save ||
                    pc.data.status !== "ready" ||
                    !day ||
                    data.season.status !== "active"
                  }
                  onClick={() => setConfirm(true)}
                >
                  <ShieldCheck size={18} />
                  Fijar mi equipo
                </button>
              </div>
              <CommandState command={cmd} />
              <Notice error={pc.error} />
              {match ? (
                <div className="battle-grid">
                  {[match.player_a_id, match.player_b_id].map((id, index) => {
                    const player = data.players.find((p) => p.id === id),
                      lock = data.locks.find(
                        (l) =>
                          l.trainer_id === player?.trainer_id &&
                          l.matchday_id === day?.id,
                      );
                    return (
                      <Card key={id} className={`battle-side side-${index}`}>
                        <span className="eyebrow">
                          {index ? "RIVAL" : "CAMPO A"}
                        </span>
                        <h2>{playerName(data, id)}</h2>
                        {lock ? (
                          <>
                            <Tag>
                              {lock.is_late
                                ? "Team Lock tardío"
                                : "Team Lock confirmado"}
                            </Tag>
                            {lock.public_team_snapshot.map((p, i) => (
                              <div key={i}>
                                <Pokemon pokemon={p} />
                                <div className="moves">
                                  {p.moves?.map((m) => (
                                    <span key={m.name}>{m.name}</span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </>
                        ) : (
                          <Empty>
                            Este entrenador todavía no tiene un Team Lock
                            público.
                          </Empty>
                        )}
                      </Card>
                    );
                  })}
                </div>
              ) : (
                <Empty>No hay enfrentamientos en la jornada actual.</Empty>
              )}
              {confirm && day && pc.data?.save && (
                <Modal
                  title="Confirmar Team Lock"
                  onClose={() => {
                    if (!cmd.pending && !cmd.uncertain) setConfirm(false);
                  }}
                >
                  <p>
                    Se fijará el equipo del save actual. El servidor comprobará
                    la jornada, los seis Pokémon y tu elegibilidad.
                  </p>
                  <button
                    className="button primary"
                    disabled={cmd.pending || cmd.uncertain}
                    onClick={async () => {
                      if (
                        await cmd.execute(
                          `/v1/seasons/${season}/matchdays/${day.id}/team-lock`,
                          { save_file_id: pc.data!.save!.id },
                          "PUT",
                        )
                      )
                        setConfirm(false);
                    }}
                  >
                    Confirmar mi equipo
                  </button>
                  <CommandState command={cmd} />
                </Modal>
              )}
            </>
          );
        }}
      </OverviewState>
    </>
  );
}
export function TrainersPage() {
  return (
    <>
      <Heading eyebrow="LOS PROTAGONISTAS" title="Entrenadores.">
        Una liga. Muchas formas de llegar a lo más alto.
      </Heading>
      <OverviewState>
        {(data) => (
          <div className="trainer-grid">
            {data.players.map((p) => (
              <Card key={p.id}>
                <div className="trainer-top">
                  <div className="avatar large">
                    {p.display_name.slice(0, 2).toUpperCase()}
                  </div>
                  <Tag>{p.status}</Tag>
                </div>
                <h2>{p.display_name}</h2>
                <p>
                  {p.badges_count == null
                    ? "Progreso no observado / pendiente de sincronizar save"
                    : `${p.badges_count} medallas registradas`}
                </p>
                {p.badges_count != null && (
                  <div
                    className="badge-strip"
                    aria-label={`${p.badges_count} medallas`}
                  >
                    {Array.from(
                      { length: Math.min(p.badges_count, 16) },
                      (_, i) => (
                        <span key={i}>◆</span>
                      ),
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </OverviewState>
    </>
  );
}
export function PCPage() {
  const pc = usePC(),
    [selected, setSelected] = useState<Model<"SlotRead"> | null>(null),
    [search, setSearch] = useState("");
  return (
    <>
      <Heading
        eyebrow="TU COLECCIÓN PRIVADA"
        title="Siempre hay un próximo equipo."
      >
        Explora los Pokémon de tu save actual en PokeApp.
      </Heading>
      <WithSeason>
        <Notice error={pc.error} />
        {pc.isPending ? (
          <Loading />
        ) : pc.data?.status === "ready" ? (
          <>
            <Field label="Buscar Pokémon">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Especie o apodo"
                type="search"
              />
            </Field>
            <div className="pokemon-grid">
              {pc.data.pokemon
                .filter((s) =>
                  `${s.pokemon.species} ${s.pokemon.nickname}`
                    .toLowerCase()
                    .includes(search.toLowerCase()),
                )
                .map((s, i) => (
                  <Card key={i}>
                    <span className="eyebrow">{s.location}</span>
                    <Pokemon
                      pokemon={s.pokemon}
                      onClick={() => setSelected(s)}
                    />
                  </Card>
                ))}
            </div>
            {pc.data.pokemon.length === 0 && (
              <Empty>Este save no contiene Pokémon disponibles.</Empty>
            )}
          </>
        ) : (
          <Empty>
            {pc.data?.status === "unsupported_payload"
              ? "Este save usa un formato que todavía no puede mostrarse."
              : "No hay un save actual analizado disponible."}{" "}
            <Link to="/saves">Ver Saves y Launcher →</Link>
          </Empty>
        )}
      </WithSeason>
      {selected && (
        <Modal
          title={selected.pokemon.nickname || selected.pokemon.species}
          onClose={() => setSelected(null)}
        >
          <Tag>{selected.location}</Tag>
          <Pokemon pokemon={selected.pokemon} />
          <dl className="details">
            <dt>Habilidad</dt>
            <dd>{selected.pokemon.ability || "—"}</dd>
            <dt>Naturaleza</dt>
            <dd>{selected.pokemon.nature || "—"}</dd>
            <dt>Objeto</dt>
            <dd>{selected.pokemon.item || "—"}</dd>
          </dl>
          <h3>Movimientos</h3>
          <div className="moves">
            {selected.pokemon.moves?.map((m) => (
              <span key={m.name}>
                {m.name} {m.pp != null && `· ${m.pp} PP`}
              </span>
            ))}
          </div>
          {(["ivs", "evs"] as const).map((k) => (
            <div key={k}>
              <h3>{k.toUpperCase()}</h3>
              {selected.pokemon[k] ? (
                <dl className="stats-list">
                  {Object.entries(selected.pokemon[k]!).map(([stat, value]) => (
                    <div key={stat}>
                      <dt>{stat}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p>No disponibles.</p>
              )}
            </div>
          ))}
        </Modal>
      )}
    </>
  );
}
export function SavesPage() {
  const pc = usePC();
  return (
    <>
      <Heading eyebrow="TU PARTIDA, BAJO CONTROL" title="Saves y Launcher.">
        El estado del save en PokeApp y el Launcher local son independientes.
      </Heading>
      <div className="quick-grid">
        <Card>
          <HardDrive />
          <h2>Save actual en PokeApp</h2>
          <Notice error={pc.error} />
          {pc.data?.save ? (
            <>
              <Tag>{pc.data.save.parser_status}</Tag>
              <p>Registrado el {date(pc.data.save.uploaded_at)}</p>
              <Link className="button" to="/pc">
                Abrir mi PC
              </Link>
            </>
          ) : (
            <p>
              {pc.isPending
                ? "Consultando…"
                : "No hay un save actual disponible para esta temporada."}
            </p>
          )}
        </Card>
        <Card>
          <Box />
          <h2>Launcher local</h2>
          <Tag>Base funcional · distribución pendiente</Tag>
          <p>
            La lectura y sincronización local están implementadas. La conexión
            de subida a PokeApp y un instalador público todavía no están
            disponibles.
          </p>
          <p className="muted">
            Esta página no puede detectar si el Launcher está abierto. El diario
            local no actualiza automáticamente este PC ni tu Team Lock.
          </p>
        </Card>
      </div>
    </>
  );
}
export function ShopPage() {
  const { season } = useApp(),
    query = useRead<Model<"ShopRead">>(
      `/v1/read/seasons/${season}/shop`,
      !!season,
    ),
    cmd = useCommand(),
    [item, setItem] = useState<Model<"ItemRead"> | null>(null),
    [base, setBase] = useState(false);
  const promo = query.data?.promotions.find(
    (p) => p.shop_item_id === item?.id && p.status === "active",
  );
  return (
    <>
      <Heading eyebrow="PREPARA TU PRÓXIMA JUGADA" title="Un pequeño impulso.">
        La tienda de tu temporada. Cada compra cuenta.
      </Heading>
      <WithSeason>
        <Notice error={query.error} />
        {query.isPending ? (
          <Loading />
        ) : (
          query.data && (
            <>
              <div className="wallet">
                <Coins />
                <strong>{query.data.balance ?? "—"} PK₽</strong>
                <span>Saldo disponible</span>
              </div>
              <CommandState command={cmd} />
              <div className="shop-grid">
                {query.data.items.map((i) => {
                  const p = query.data!.promotions.find(
                    (p) => p.shop_item_id === i.id && p.status === "active",
                  );
                  return (
                    <Card key={i.id} className="shop-card">
                      <div className="shop-icon">
                        <ShoppingBag />
                      </div>
                      <span className="eyebrow">{i.category}</span>
                      <h2>{i.name}</h2>
                      <p>{i.description}</p>
                      {p && (
                        <Tag>
                          Promoción ·{" "}
                          {p.stock_total == null
                            ? "Sin límite"
                            : Math.max(0, p.stock_total - p.stock_used)}{" "}
                          disponibles
                        </Tag>
                      )}
                      <div className="shop-bottom">
                        <strong>
                          {p?.effective_price ?? i.base_price}{" "}
                          <small>PK₽</small>
                        </strong>
                        <button
                          className="button"
                          onClick={() => {
                            setItem(i);
                            setBase(false);
                          }}
                        >
                          Comprar
                        </button>
                      </div>
                    </Card>
                  );
                })}
              </div>
              {!query.data.items.length && (
                <Empty>No hay artículos disponibles.</Empty>
              )}
            </>
          )
        )}
      </WithSeason>
      <WithSeason>
        <Inventory />
      </WithSeason>
      {item && (
        <Modal
          title={`Comprar ${item.name}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setItem(null);
          }}
        >
          <p>
            {promo ? promo.effective_price : item.base_price} PK₽ · El saldo,
            los bloqueos y el stock se verifican al confirmar.
          </p>
          {!promo && (
            <label className="check">
              <input
                type="checkbox"
                checked={base}
                onChange={(e) => setBase(e.target.checked)}
              />
              Confirmo la compra al precio base de {item.base_price} PK₽.
            </label>
          )}
          <button
            className="button primary"
            disabled={cmd.pending || cmd.uncertain || (!promo && !base)}
            onClick={async () => {
              if (
                await cmd.execute(
                  promo
                    ? `/v1/seasons/${season}/shop/promotions/${promo.id}/purchases`
                    : `/v1/seasons/${season}/shop/purchases`,
                  promo ? {} : { item_id: item.id, confirm_base_price: base },
                )
              )
                setItem(null);
            }}
          >
            Confirmar compra
          </button>
          <CommandState command={cmd} />
        </Modal>
      )}
    </>
  );
}
export function HallPage() {
  const [offset, setOffset] = useState(0),
    query = useRead<Model<"HallPage">>(`/v1/read/hall?offset=${offset}`),
    trainers = useRead<Model<"TrainerRead">[]>("/v1/read/trainers");
  const name = (id: string | null) =>
    trainers.data?.find((t) => t.id === id)?.display_name ||
    "Entrenador histórico";
  return (
    <>
      <Heading eyebrow="LOS NOMBRES QUE PERMANECEN" title="Hall de la Fama.">
        La temporada termina. La historia se queda.
      </Heading>
      <Notice error={query.error} />
      <Notice error={trainers.error} />
      {query.isPending ? (
        <Loading />
      ) : query.data?.items.length ? (
        <div className="hall-grid">
          {query.data.items.map((h) => {
            const champion = h.cup_sides?.find(
                (s) => s.id === h.champion_side_id,
              ),
              finalist = h.cup_sides?.find((s) => s.id === h.finalist_side_id);
            return (
              <Card key={h.id} className="hall-card">
                <Trophy className="hall-trophy" />
                <span className="eyebrow">
                  {h.competition_type === "league"
                    ? "CAMPEÓN DE LIGA"
                    : champion?.members.length === 2
                      ? "CAMPEONES · DOBLES"
                      : "CAMPEÓN DE COPA"}
                </span>
                <h2>{champion?.name || name(h.champion_trainer_id)}</h2>
                {champion && (
                  <p className="champion-members">
                    {champion.members.map((m) => m.display_name).join(" & ")}
                  </p>
                )}
                <div className="hall-line" />
                {(h.competition_type !== "league" || h.finalist_trainer_id) && (
                  <p>
                    Finalista:{" "}
                    {finalist
                      ? finalist.members.map((m) => m.display_name).join(" & ")
                      : name(h.finalist_trainer_id)}
                  </p>
                )}
                <p className="caption">CERTIFICADO · {date(h.finalized_at)}</p>
                {h.cup_id && (
                  <Link
                    to={`/copa/${h.cup_id}?season=${h.season_id}`}
                    className="text-link"
                  >
                    Ver esta Copa <ArrowUpRight size={16} />
                  </Link>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <Empty>
          El Hall espera su próxima historia. Los títulos aparecerán tras su
          certificación oficial.
        </Empty>
      )}
      <div className="toolbar">
        {offset > 0 && (
          <button onClick={() => setOffset(Math.max(0, offset - 50))}>
            Anterior
          </button>
        )}
        {query.data?.next_offset != null && (
          <button onClick={() => setOffset(query.data!.next_offset!)}>
            Siguiente
          </button>
        )}
      </div>
    </>
  );
}
