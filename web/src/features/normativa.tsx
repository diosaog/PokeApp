import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import {
  Ban,
  CalendarDays,
  CircleAlert,
  Coins,
  Info,
  Minus,
  Plus,
  Radio,
  Sparkles,
  Swords,
  Trophy,
} from "lucide-react";
import {
  ItemIcon,
  PokemonSprite,
  SpriteGeneration,
} from "../pokemon/presentation";
import { badgeAsset } from "../pokemon/badges";
import { useReducedMotion } from "../preferences";
import {
  aaronClause,
  chapters,
  conductRules,
  discordRules,
  eliteNote,
  eliteTypes,
  examples,
  formatFacts,
  freeItemRules,
  levelRules,
  matchdaySteps,
  matchdayStates,
  netText,
  nuzlockeGroups,
  otherRules,
  practiceRule,
  prizes,
  robberyRules,
  ruleLegend,
  rulebookUpdated,
  rulesCanChange,
  scoreRules,
  scoreTiles,
  shopFacts,
  standings,
  stretches,
  stretchRules,
  teamPanels,
  titleTiebreak,
  titleTiebreakNote,
  tradeRules,
  wildcardRule,
  wildcards,
  type Challenge,
  type NuzlockeGroup,
  type Rule,
  type RuleKind,
} from "./normativa-content";
import "../design/normativa.css";

const ruleTags: Partial<Record<RuleKind, { label: string; Icon: typeof Ban }>> =
  {
    obligatorio: { label: "Obligatorio", Icon: CircleAlert },
    prohibido: { label: "Prohibido", Icon: Ban },
    excepcion: { label: "Excepción", Icon: Sparkles },
    aclaracion: { label: "Aclaración", Icon: Info },
  };

function RuleText({ rule }: { rule: Rule }) {
  const tag = ruleTags[rule.kind];
  return (
    <>
      <span className="nv-rule-id">{rule.id}</span>
      <p>
        {tag && (
          <span className="nv-rule-tag">
            <tag.Icon size={13} aria-hidden="true" /> {tag.label}
          </span>
        )}
        {rule.text}
      </p>
    </>
  );
}
function Rules({ rules }: { rules: Rule[] }) {
  return (
    <ol className="nv-rules">
      {rules.map((rule) => (
        <li key={rule.id} className={`nv-rule is-${rule.kind}`}>
          <RuleText rule={rule} />
        </li>
      ))}
    </ol>
  );
}

function Chapter({
  index,
  intro,
  children,
}: {
  index: number;
  intro: string;
  children: ReactNode;
}) {
  const chapter = chapters[index];
  return (
    <section
      id={`nv-${chapter.id}`}
      className={`nv-chapter nv-chapter-${chapter.id}`}
      aria-labelledby={`nv-${chapter.id}-title`}
    >
      <header className="nv-chapter-head">
        <span className="nv-numeral" aria-hidden="true">
          {chapter.numeral}
        </span>
        <div>
          <p className="nv-chapter-label">Capítulo {chapter.numeral}</p>
          <h2 id={`nv-${chapter.id}-title`}>{chapter.title}</h2>
          <p className="nv-chapter-intro">{intro}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

// ---------- Index ----------
function useActiveChapter() {
  const [active, setActive] = useState<string>(chapters[0].id);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting)
            setActive(entry.target.id.replace("nv-", ""));
      },
      { rootMargin: "-20% 0px -70% 0px" },
    );
    for (const chapter of chapters) {
      const node = document.getElementById(`nv-${chapter.id}`);
      if (node) observer.observe(node);
    }
    return () => observer.disconnect();
  }, []);
  return active;
}

function Index({ active }: { active: string }) {
  const reduced = useReducedMotion();
  const go = (event: MouseEvent<HTMLAnchorElement>, id: string) => {
    const target = document.getElementById(`nv-${id}`);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({
      behavior: reduced ? "auto" : "smooth",
      block: "start",
    });
    window.history.replaceState(window.history.state, "", `#nv-${id}`);
  };
  return (
    <nav className="nv-index" aria-label="Capítulos de la Normativa">
      <div className="nv-dex-lights" aria-hidden="true">
        <i />
        <b />
        <b />
        <b />
      </div>
      <ol>
        {chapters.map((chapter) => (
          <li key={chapter.id}>
            <a
              className="nv-index-link"
              href={`#nv-${chapter.id}`}
              aria-current={active === chapter.id ? "true" : undefined}
              onClick={(event) => go(event, chapter.id)}
            >
              <span aria-hidden="true">{chapter.numeral}</span>
              {chapter.title}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

// ---------- I. Nuzlocke art ----------
function GroupArt({ id }: { id: NuzlockeGroup["id"] }) {
  switch (id) {
    case "capturas":
      return (
        <div className="nv-art nv-art-route" aria-hidden="true">
          <span className="nv-sign">
            <ItemIcon name="Poke Ball" /> Primer encuentro
          </span>
          <span className="nv-tag-mote">Mote: Chispitas</span>
        </div>
      );
    case "caja":
      return (
        <div className="nv-art nv-art-grave" aria-hidden="true">
          <PokemonSprite species="Duskull" />
        </div>
      );
    case "clausulas":
      return (
        <div className="nv-art nv-art-line" aria-hidden="true">
          <PokemonSprite species="Froakie" />
          <PokemonSprite species="Frogadier" />
          <PokemonSprite species="Greninja" />
          <span className="nv-legend-ban">
            <PokemonSprite species="Xerneas" />
          </span>
        </div>
      );
    case "shiny":
      return (
        <div className="nv-art nv-art-shiny" aria-hidden="true">
          <PokemonSprite species="Eevee" shiny animated />
        </div>
      );
    case "tiendas":
      return (
        <div className="nv-art nv-art-shop" aria-hidden="true">
          <span>
            <ItemIcon name="Potion" />
          </span>
          <span>
            <ItemIcon name="X Attack" />
          </span>
        </div>
      );
  }
}

// ---------- II. The climb ----------
function ChallengeToken({ challenge }: { challenge: Challenge }) {
  if (challenge.badge) {
    const badge = badgeAsset("kalos", challenge.badge, "Y");
    return (
      <img
        className="nv-medal"
        src={`/visuals/badges/v1/${badge}.png`}
        alt=""
        width={48}
        height={48}
        loading="lazy"
      />
    );
  }
  if (challenge.elite)
    return (
      <span className="nv-elite" aria-hidden="true">
        {eliteTypes.map((type) => (
          <img
            key={type}
            src={`/visuals/v1/types/${type}-icon.svg`}
            alt=""
            width={21}
            height={21}
            loading="lazy"
          />
        ))}
      </span>
    );
  return (
    <span className="nv-champion" aria-hidden="true">
      <PokemonSprite species="Gardevoir" />
    </span>
  );
}

function Climb() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLOListElement>(null);
  const [state, setState] = useState<"still" | "armed" | "lit">("still");
  useEffect(() => {
    const node = ref.current;
    if (reduced || !node || typeof IntersectionObserver === "undefined") return;
    setState("armed");
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setState("lit");
        observer.disconnect();
      },
      { threshold: 0.2 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [reduced]);
  let order = 0;
  return (
    <ol className="nv-climb" ref={ref} data-state={state}>
      {stretches.map((stretch) => (
        <li
          key={stretch.number}
          className={`nv-stretch is-t${stretch.number}`}
          style={{ "--stops": stretch.challenges.length } as CSSProperties}
        >
          <ol className="nv-stops">
            {stretch.challenges.map((challenge) => {
              const last =
                challenge === stretch.challenges[stretch.challenges.length - 1];
              const step = order++;
              return (
                <li
                  key={challenge.name}
                  className="nv-stop"
                  style={
                    {
                      "--lv": challenge.level,
                      "--step": step,
                      "--type": `var(--type-${challenge.type})`,
                    } as CSSProperties
                  }
                >
                  <ChallengeToken challenge={challenge} />
                  <strong className="nv-level">
                    <span className="sr-only">Límite de nivel </span>
                    {challenge.level}
                  </strong>
                  <span className="nv-bar" aria-hidden="true">
                    {last && (
                      <span className="nv-flag">J{stretch.matchday}</span>
                    )}
                  </span>
                  <span className="nv-stop-who">
                    <strong>{challenge.name}</strong>
                    <small>{challenge.label}</small>
                  </span>
                </li>
              );
            })}
          </ol>
          <p className="nv-stretch-foot">
            <strong>Tramo {stretch.number}</strong>
            <span>
              Jornada {stretch.matchday}, nivel {stretch.cap}
            </span>
          </p>
        </li>
      ))}
    </ol>
  );
}

// ---------- IV. Score ----------
function Pips({
  wins,
  ordinary,
  wipe,
}: {
  wins: number;
  ordinary: number;
  wipe: number;
}) {
  return (
    <span className="nv-pips" aria-hidden="true">
      {Array.from({ length: wins }, (_, i) => (
        <i key={`w${i}`} className="is-win" />
      ))}
      {Array.from({ length: ordinary }, (_, i) => (
        <i key={`o${i}`} className="is-death" />
      ))}
      {Array.from({ length: wipe }, (_, i) => (
        <i key={`d${i}`} className="is-wipe" />
      ))}
    </span>
  );
}
function Stepper({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="nv-stepper">
      <span>{label}</span>
      <div>
        <button
          type="button"
          aria-label={`Quitar ${label.toLowerCase()}`}
          disabled={value === 0}
          onClick={() => onChange(value - 1)}
        >
          <Minus size={15} aria-hidden="true" />
        </button>
        <output>{value}</output>
        <button
          type="button"
          aria-label={`Añadir ${label.toLowerCase()}`}
          disabled={value === 99}
          onClick={() => onChange(value + 1)}
        >
          <Plus size={15} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
function Calculator() {
  const [wins, setWins] = useState(2),
    [ordinary, setOrdinary] = useState(1),
    [wipe, setWipe] = useState(0);
  return (
    <div className="nv-calc">
      <h3>Prueba tu marcador</h3>
      <Stepper label="Victorias" value={wins} onChange={setWins} />
      <Stepper
        label="Muertes ordinarias"
        value={ordinary}
        onChange={setOrdinary}
      />
      <Stepper label="Muertes tras wipe" value={wipe} onChange={setWipe} />
      <p className="nv-calc-result" aria-live="polite">
        <span>Puntos NET</span>
        <strong>{netText(wins, ordinary, wipe)}</strong>
      </p>
    </div>
  );
}

// ---------- Page ----------
export function NormativaPage() {
  const active = useActiveChapter();
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    // After App's own scroll-to-top for a route change.
    const frame = requestAnimationFrame(() =>
      document.getElementById(hash.slice(1))?.scrollIntoView(),
    );
    return () => cancelAnimationFrame(frame);
  }, [hash]);
  return (
    <SpriteGeneration.Provider value={6}>
      <div className="rulebook">
        <header className="nv-hero">
          <div className="nv-seal" aria-hidden="true" />
          <img
            className="nv-crest"
            src="/visuals/normativa/champions-cup.webp"
            alt="Escudo de The Champions Cup"
            width={581}
            height={568}
          />
          <div className="nv-hero-copy">
            <p className="nv-hero-kicker">
              Reglamento oficial de la ChampionsLocke
            </p>
            <h1>Normativa</h1>
            <p className="nv-hero-lead">
              Cómo se captura, cómo se compite y cómo se gana en Pokémon X e Y.
              Si una norma ha cambiado desde el reglamento original, aquí ya
              aparece la versión que se aplica hoy.
            </p>
            <p className="nv-hero-date">Actualizada el {rulebookUpdated}</p>
          </div>
        </header>

        <div className="nv-layout">
          <Index active={active} />
          <div className="nv-chapters">
            <aside className="nv-legend" aria-label="Cómo leer el reglamento">
              {ruleLegend.map((entry) => (
                <span
                  key={entry.kind}
                  className={`nv-legend-item is-${entry.kind}`}
                >
                  <strong>{entry.label}</strong>
                  <small>{entry.hint}</small>
                </span>
              ))}
            </aside>

            <Chapter
              index={0}
              intro="La base del reto. Se aplica durante toda la partida, desde la primera ruta hasta la Campeona."
            >
              <div className="nv-bento">
                {nuzlockeGroups.map((group) => (
                  <article key={group.id} className={`nv-group is-${group.id}`}>
                    <GroupArt id={group.id} />
                    <h3>{group.title}</h3>
                    <Rules rules={group.rules} />
                  </article>
                ))}
                <article className="nv-group is-acta">
                  <h3>Disposiciones finales</h3>
                  <Rules rules={[rulesCanChange]} />
                  <div className="nv-aaron">
                    <span aria-hidden="true">
                      <PokemonSprite species="Zorua" />
                    </span>
                    <div>
                      <h4>Cláusula Aarón</h4>
                      <ol className="nv-rules">
                        <li className="nv-rule is-norma">
                          <RuleText rule={aaronClause} />
                        </li>
                      </ol>
                      <p className="nv-joke">
                        Broma interna del reglamento original. No conlleva
                        ninguna sanción.
                      </p>
                    </div>
                  </div>
                </article>
              </div>
            </Chapter>

            <Chapter
              index={1}
              intro="El límite sube con cada desafío. Cada banderín marca el nivel de los combates de esa jornada."
            >
              <Climb />
              <p className="nv-climb-note">{eliteNote}</p>
              <div className="nv-two">
                <Rules rules={levelRules} />
                <aside
                  className="nv-rewards"
                  aria-label="Recompensas de progreso"
                >
                  <h3>Recompensas de progreso</h3>
                  <p>
                    <strong>4</strong>
                    <span>monedas por cada medalla</span>
                  </p>
                  <p>
                    <strong>12</strong>
                    <span>monedas más por vencer a la Campeona</span>
                  </p>
                  <small>
                    Se abonan solas cuando sincronizas tu partida oficial.
                  </small>
                </aside>
              </div>
            </Chapter>

            <Chapter
              index={2}
              intro="La aventura y la competición avanzan a la vez: cada tramo del juego termina en una jornada de Liga."
            >
              <Rules rules={stretchRules} />
              <ol className="nv-route-table">
                {stretches.map((stretch) => (
                  <li key={stretch.number} className={`is-t${stretch.number}`}>
                    <strong>Tramo {stretch.number}</strong>
                    <span>{stretch.ends}</span>
                    <b>
                      Jornada {stretch.matchday}
                      <small>
                        Nivel {stretch.cap}, {stretch.capLeader}
                      </small>
                    </b>
                  </li>
                ))}
              </ol>
              <h3 className="nv-sub">Una jornada, paso a paso</h3>
              <ol className="nv-cycle">
                {matchdaySteps.map((step) => (
                  <li key={step.title}>
                    <h4>{step.title}</h4>
                    <p>{step.text}</p>
                  </li>
                ))}
              </ol>
              <div className="nv-panels">
                {teamPanels.map((panel) => (
                  <article key={panel.id} className={`nv-panel is-${panel.id}`}>
                    <h3>{panel.title}</h3>
                    <ul>
                      {panel.points.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
              <h3 className="nv-sub">Estados de una jornada</h3>
              <ol className="nv-states">
                {matchdayStates.map((state) => (
                  <li key={state.id} className={`is-${state.id}`}>
                    <h4>{state.title}</h4>
                    <p>{state.text}</p>
                  </li>
                ))}
              </ol>
            </Chapter>

            <Chapter
              index={3}
              intro="Una sola fórmula decide la Liga. Lo que cuenta son las victorias y lo que cuesta cada muerte."
            >
              <div className="nv-board">
                <p
                  className="nv-formula"
                  aria-label="Puntos NET igual a victorias, menos 0,1 por cada muerte ordinaria, menos 0,2 por cada muerte revivida tras wipe"
                >
                  <span>Puntos NET</span>
                  <span>
                    <i>=</i>Victorias
                  </span>
                  <span>
                    <i>−</i>0,1 × muertes
                  </span>
                  <span>
                    <i>−</i>0,2 × muertes tras wipe
                  </span>
                </p>
                <ul className="nv-tiles">
                  {scoreTiles.map((tile) => (
                    <li key={tile.id} className={`is-${tile.id}`}>
                      <strong>{tile.value}</strong>
                      <span>{tile.label}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="nv-score-lab">
                <div className="nv-examples">
                  <h3>Actas de ejemplo</h3>
                  <ul>
                    {examples.map((example) => (
                      <li key={example.note}>
                        <Pips {...example} />
                        <span>{example.note}</span>
                        <strong>
                          {netText(
                            example.wins,
                            example.ordinary,
                            example.wipe,
                          )}
                        </strong>
                      </li>
                    ))}
                  </ul>
                </div>
                <Calculator />
              </div>
              <Rules rules={scoreRules} />
              <h3 className="nv-sub">Formato de competición</h3>
              <ul className="nv-format">
                {formatFacts.map((fact, index) => {
                  const Icon = [Trophy, Swords, CalendarDays][index];
                  return (
                    <li key={fact.title}>
                      <Icon size={22} aria-hidden="true" />
                      <h4>{fact.title}</h4>
                      <p>{fact.text}</p>
                    </li>
                  );
                })}
              </ul>
              <div className="nv-two">
                {standings.map((row) => (
                  <article key={row.title} className="nv-standing">
                    <h3>{row.title}</h3>
                    <p>{row.text}</p>
                    <p className="nv-detail">{row.detail}</p>
                  </article>
                ))}
              </div>
              <div className="nv-tiebreak">
                <h3>Si hay empate por el título</h3>
                <ol>
                  {titleTiebreak.map((step) => (
                    <li key={step.title}>
                      <h4>{step.title}</h4>
                      <p>{step.text}</p>
                    </li>
                  ))}
                </ol>
                <p className="nv-detail">{titleTiebreakNote}</p>
              </div>
              <h3 className="nv-sub">Premios</h3>
              <ul className="nv-prizes">
                {prizes.map((prize) => (
                  <li key={prize.id} className={`is-${prize.id}`}>
                    {prize.code ? (
                      <ItemIcon name={prize.what} code={prize.code} />
                    ) : prize.id === "todos" ? (
                      <Coins aria-hidden="true" />
                    ) : (
                      <Trophy aria-hidden="true" />
                    )}
                    <div>
                      <strong>{prize.who}</strong>
                      <span>{prize.what}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </Chapter>

            <Chapter
              index={4}
              intro="Cómo se juega cada sesión y qué se espera de cada entrenador."
            >
              <div className="nv-conduct">
                <article className="nv-live">
                  <h3>
                    <Radio size={18} aria-hidden="true" /> Directo en Discord
                  </h3>
                  <div className="nv-stream" aria-hidden="true">
                    <span>En directo</span>
                    <PokemonSprite species="Pikachu" />
                  </div>
                  <Rules rules={discordRules} />
                </article>
                <article className="nv-free">
                  <h3>Objetos sin límite</h3>
                  <div className="nv-infinite" aria-hidden="true">
                    <ItemIcon name="Rare Candy" />
                    <ItemIcon name="Heart Scale" />
                    <b>∞</b>
                  </div>
                  <Rules rules={freeItemRules} />
                </article>
                <article className="nv-respect">
                  <h3>Juego limpio</h3>
                  <Rules rules={conductRules} />
                </article>
              </div>
            </Chapter>

            <Chapter
              index={5}
              intro="Lo que puedes hacer con otros entrenadores y las cartas que cambian una partida."
            >
              <div className="nv-two">
                <div>
                  <h3 className="nv-sub">Intercambios</h3>
                  <Rules rules={tradeRules} />
                </div>
                <div>
                  <h3 className="nv-sub">Práctica y cartas</h3>
                  <Rules rules={[practiceRule, wildcardRule]} />
                </div>
              </div>
              <h3 className="nv-sub">Cartas comodín</h3>
              <ul className="nv-cards">
                {wildcards.map((card) => (
                  <li
                    key={card.code}
                    className={`nv-card ${card.active ? "is-live" : "is-waiting"}`}
                  >
                    <div className="nv-card-art">
                      <ItemIcon name={card.name} code={card.code} />
                    </div>
                    <h4>{card.name}</h4>
                    <p className="nv-card-price">
                      {card.price == null ? "Recompensa" : `${card.price} PK₽`}
                    </p>
                    <p>{card.effect}</p>
                    <p className="nv-card-note">{card.note}</p>
                    <p className="nv-card-status">{card.status}</p>
                  </li>
                ))}
              </ul>
              <h3 className="nv-sub">Normas de la carta Robo de Pokémon</h3>
              <Rules rules={robberyRules} />
              <h3 className="nv-sub">La Tienda de PokeApp</h3>
              <dl className="nv-shop">
                {shopFacts.map((fact) => (
                  <div key={fact.title}>
                    <dt>{fact.title}</dt>
                    <dd>{fact.text}</dd>
                  </div>
                ))}
              </dl>
            </Chapter>

            <Chapter
              index={6}
              intro="Reglas aprobadas después del documento original que ya forman parte de la competición."
            >
              <ul className="nv-others">
                {otherRules.map((rule) => (
                  <li key={rule.id}>
                    <span className="nv-rule-id">{rule.id}</span>
                    <div>
                      <h4>{rule.title}</h4>
                      <p>{rule.text}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Chapter>
          </div>
        </div>
      </div>
    </SpriteGeneration.Provider>
  );
}
