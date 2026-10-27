import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Coins, Trophy, Sparkles } from "lucide-react";
import type { Model, Overview } from "../api/types";
import { pokemonName, pokemonTitle } from "../pokemon/localization";
import {
  PokemonSprite,
  PokemonStatusFlags,
  TypeBadge,
  ItemIcon,
  TrainerPhoto,
  typeClass,
} from "../pokemon/presentation";
import { useApp, useRead, useOverview, usePC } from "../state";
import { ParticipantResults } from "./league-results";
import { InitialAssignment } from "./initial-assignment";
import { WipeRevivals } from "./wipe-revivals";
import { Collection } from "./collection";
import { SaveGame } from "./progress";
import { matchLabel } from "./admin-labels";
import { LeagueOperations } from "./league-operations";
import { TeamLockWarning } from "./team-lock-warning";
import {
  Card,
  CommandState,
  Empty,
  Heading,
  Loading,
  Modal,
  Notice,
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
export function Pokemon({
  pokemon,
  onClick,
  animated = false,
}: {
  pokemon: Pick<
    Model<"PokemonRead">,
    "species" | "nickname" | "level" | "types" | "status_flags" | "form"
  > & { is_shiny?: boolean };
  onClick?: () => void;
  animated?: boolean;
}) {
  const body = (
    <>
      <PokemonSprite
        species={pokemon.species}
        form={pokemon.form}
        animated={animated}
      />
      <div>
        <strong>{pokemonTitle(pokemon)}</strong>
        {!!pokemon.form && <small>Forma {pokemon.form}</small>}
        <span className="muted">
          {pokemon.nickname
            ? pokemonName("species", pokemon.species)
            : "Pokémon"}{" "}
          · Nv. {pokemon.level ?? "—"}
        </span>
        <div className="tags">
          {pokemon.types?.map((t) => (
            <TypeBadge key={t} type={t} />
          ))}
          {pokemon.is_shiny && <Sparkles size={15} />}
        </div>
        <PokemonStatusFlags flags={pokemon.status_flags} />
      </div>
      {onClick && <ArrowUpRight size={18} />}
    </>
  );
  // The card wears its primary type colour.
  const tone = `pokemon ${typeClass(pokemon.types?.[0])}`;
  return onClick ? (
    <button className={tone} onClick={onClick}>
      {body}
    </button>
  ) : (
    <div className={tone}>{body}</div>
  );
}
export { HomePage } from "./home";
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
// One league shows a single «Liga»; two leagues keep División A and B. The
// standings themselves count too, so a league is never hidden.
function leagueCodes(data: Overview, standings: { division: string }[]) {
  const codes = [
    ...new Set([
      ...data.divisions.map((d) => d.code),
      ...standings.map((s) => s.division),
    ]),
  ].sort();
  return codes.length ? codes : ["A", "B"];
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
              {snapshot ? "Resultado oficial" : "Aún sin clasificación oficial"}
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
                {leagueCodes(data, snapshot.standings).map(
                  (division, _, codes) => (
                    <Card key={division}>
                      <h2>
                        {codes.length === 1 ? "Liga" : `División ${division}`}
                      </h2>
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
                                  <td>
                                    {playerName(data, s.season_player_id)}
                                  </td>
                                  <td>{s.points_awarded}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </Card>
                  ),
                )}
              </>
            ) : (
              <Empty>
                La clasificación aparecerá cuando se cierre esta jornada.
              </Empty>
            )}
            {canRecord &&
              !data.locks.some(
                (lock) =>
                  lock.trainer_id === me?.trainer_id &&
                  lock.matchday_id === dayId,
              ) && <TeamLockWarning own />}
            <h2>Enfrentamientos</h2>
            {canRecord ? (
              <ParticipantResults
                key={`${data.season.id}:${dayId}`}
                data={data}
                dayId={dayId}
                dayNumber={data.days.find((day) => day.id === dayId)?.number}
              />
            ) : (
              <>
                <div className="match-grid">
                  {data.matches
                    .filter((m) => m.matchday_id === dayId)
                    .map((m) => (
                      <Card key={m.id}>
                        <Tag>{matchLabel(m.status)}</Tag>
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
    <Card className="league-table-card">
      <h2>Clasificación general</h2>
      <p>
        Puntos oficiales acumulados y saldo actual. A igualdad de puntos, el
        orden mostrado no decide el desempate.
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
                    <Link
                      className="standing-trainer"
                      to={`/entrenadores/${row.trainer_id}`}
                    >
                      <TrainerPhoto name={row.display_name} />
                      <span>{row.display_name}</span>
                    </Link>
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
                <>
                  <LeagueGeneral data={data} />
                  <LeagueOperations key={data.season.id} data={data} />
                  <WipeRevivals data={data} />
                </>
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
export { TrainersPage } from "./trainers";
export function PCPage() {
  const pc = usePC();
  return (
    <>
      <Heading eyebrow="TU PARTIDA" title="Mi PC">
        Tu equipo y tus cajas, a un movimiento de distancia.
      </Heading>
      <WithSeason>
        <Notice error={pc.error} />
        {pc.isPending ? (
          <Loading />
        ) : pc.data?.status === "ready" ? (
          <>
            <SaveGame game={pc.data.save?.game} />
            <Collection key={pc.data.save?.id} slots={pc.data.pokemon} />
          </>
        ) : (
          <Empty>
            No hay una partida disponible.{" "}
            <Link to="/saves">Sincronizar con el Launcher →</Link>
          </Empty>
        )}
      </WithSeason>
    </>
  );
}
export function ShopPage() {
  const { season, me } = useApp(),
    query = useRead<Model<"ShopRead">>(
      `/v1/read/seasons/${season}/shop`,
      !!season,
    ),
    cmd = useCommand([
      `/v1/read/seasons/${season}/shop`,
      `/v1/read/seasons/${season}/inventory`,
      `/v1/read/seasons/${season}/overview`,
      `/v1/read/seasons/${season}/league`,
    ]),
    [item, setItem] = useState<Model<"ItemRead"> | null>(null),
    [base, setBase] = useState(false),
    [category, setCategory] = useState("comodines");
  const promo = query.data?.promotions.find(
    (p) => p.shop_item_id === item?.id && p.status === "active",
  );
  return (
    <>
      <Heading eyebrow="PREPARA TU PRÓXIMA JUGADA" title="Tienda">
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
              {["finished", "archived"].includes(query.data.season_status) && (
                <p>
                  La Liga ha terminado. Puedes seguir gastando tus monedas en
                  artículos disponibles.
                </p>
              )}
              <nav className="tabs" aria-label="Categorías de tienda">
                {(
                  [
                    ["comodines", "Comodines"],
                    ["bayas", "Bayas"],
                    ["competitivos", "Competitivos"],
                    ["crianza", "Crianza"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    className={category === id ? "active" : ""}
                    aria-pressed={category === id}
                    onClick={() => setCategory(id)}
                  >
                    {label}
                  </button>
                ))}
              </nav>
              <div className="shop-grid">
                {query.data.items
                  .filter((i) => i.category === category)
                  .map((i) => {
                    const p = query.data!.promotions.find(
                      (p) => p.shop_item_id === i.id && p.status === "active",
                    );
                    const upcoming = query.data!.promotions.filter(
                      (offer) =>
                        offer.shop_item_id === i.id &&
                        offer.status === "pending",
                    );
                    return (
                      <Card key={i.id} className="shop-card">
                        <div className="shop-icon">
                          <ItemIcon name={i.name} code={i.code} />
                        </div>
                        <h2>{pokemonName("item", i.name)}</h2>
                        <p>{i.description}</p>
                        {p && (
                          <Tag>
                            Promoción activa ·{" "}
                            {p.stock_total == null
                              ? "Sin límite"
                              : Math.max(0, p.stock_total - p.stock_used)}{" "}
                            disponibles
                          </Tag>
                        )}
                        {upcoming.map((offer) => (
                          <p key={offer.id}>
                            <Tag>Próxima promoción</Tag> {offer.effective_price}{" "}
                            PK₽ · Aún no disponible
                            {offer.activates_at &&
                              ` · Desde ${date(offer.activates_at)}`}
                          </p>
                        ))}
                        <div className="shop-bottom">
                          <strong className="coin-price">
                            <Coins size={18} aria-hidden="true" />
                            {p?.effective_price ?? i.base_price}{" "}
                            <small>PK₽</small>
                          </strong>
                          <button
                            className="button primary"
                            disabled={
                              cmd.pending ||
                              cmd.uncertain ||
                              (!p &&
                                upcoming.length > 0 &&
                                i.category !== "comodines")
                            }
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
              {!query.data.items.some((i) => i.category === category) && (
                <Empty>No hay artículos disponibles.</Empty>
              )}
            </>
          )
        )}
      </WithSeason>
      <Card className="shop-inventory-link">
        <h2>Tu mochila te acompaña</h2>
        <p>Consulta tus compras, vales y canjes desde tu perfil.</p>
        <Link className="button" to={`/entrenadores/${me?.trainer_id}`}>
          Abrir mi inventario →
        </Link>
      </Card>
      {item && (
        <Modal
          title={`Comprar ${pokemonName("item", item.name)}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setItem(null);
          }}
        >
          <div className="purchase-summary">
            <ItemIcon name={item.name} code={item.code} />
            <strong>
              {promo ? promo.effective_price : item.base_price} PK₽
            </strong>
          </div>
          <p>Revisa el precio antes de confirmar tu compra.</p>
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
    trainers = useRead<Model<"TrainerRead">[]>("/v1/read/trainers"),
    seasons = useRead<Model<"SeasonPage">>("/v1/read/seasons?offset=0");
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
                <div className="hall-portraits">
                  {champion ? (
                    champion.members.map((m) => (
                      <TrainerPhoto key={m.trainer_id} name={m.display_name} />
                    ))
                  ) : (
                    <TrainerPhoto name={name(h.champion_trainer_id)} />
                  )}
                </div>
                <span className="eyebrow">
                  {h.competition_type === "league"
                    ? "CAMPEÓN DE LIGA"
                    : champion?.members.length === 2
                      ? "CAMPEONES · DOBLES"
                      : "CAMPEÓN DE COPA"}
                </span>
                <h2>{champion?.name || name(h.champion_trainer_id)}</h2>
                {seasons.data?.items.find((s) => s.id === h.season_id)
                  ?.name && (
                  <p className="hall-season">
                    {seasons.data.items.find((s) => s.id === h.season_id)!.name}
                  </p>
                )}
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
        <div className="hall-empty">
          <Trophy size={60} />
          <h2>Tu próxima historia empieza aquí.</h2>
          <p>Los campeones aparecerán cuando su título sea oficial.</p>
          <Link to="/liga" className="button">
            Volver a la Liga
          </Link>
        </div>
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
