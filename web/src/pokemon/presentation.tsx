import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import {
  Award,
  ChevronDown,
  CircleHelp,
  ImageOff,
  Package,
  UserRound,
  X,
} from "lucide-react";
import { catalogId, pokemonName, statName } from "./localization";
import itemIds from "./visual-items.json";
import moveTypes from "./move-types.json";
import catalogShopArt from "./shop-art.json";
import animatedIds from "./animated-sprites.json";
import formSprites from "./visual-forms.json";
import generationSprites from "./generation-sprites.json";
import { badgeAsset } from "./badges";
import { useReducedMotion } from "../preferences";

const base = "/visuals/v1";
const items = new Set(itemIds);
// Art of the save's own generation: X/Y renders for Gen6 games, Ultra Sun/
// Ultra Moon renders for Gen7. A screen that knows its game wraps its
// Pokémon in <SpriteGeneration value={gameGeneration(game)}>.
const generationSets: Record<string, Set<string>> = Object.fromEntries(
  Object.entries(generationSprites).map(([set, names]) => [
    set,
    new Set(names),
  ]),
);
const GENERATIONS: Record<string, number> = {
  X: 6,
  Y: 6,
  OR: 6,
  AS: 6,
  SN: 7,
  MN: 7,
  US: 7,
  UM: 7,
};
export function gameGeneration(game?: string | null) {
  return (game && GENERATIONS[game]) || null;
}
export const SpriteGeneration = createContext<number | null>(null);
const portraits: Record<string, string> = {
  anto: "ANTO",
  victor: "VICTOR",
  samu: "SAMU",
  rober: "ROBER",
  miguel: "MIGUEL",
  iker: "Iker",
  daviry: "DAVIRY",
  aaron: "AARON",
};
const normalize = (s: string) =>
  s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
export type PokemonStatusFlag = "robado" | "blindado" | "revivido";
const statusFlagLabels: Record<PokemonStatusFlag, string> = {
  robado: "ROBADO",
  blindado: "BLINDADO",
  revivido: "REVIVIDO",
};
export function PokemonStatusFlags({
  flags,
}: {
  flags?: readonly PokemonStatusFlag[];
}) {
  const visible = (flags || []).filter(
    (flag, index, values) =>
      flag in statusFlagLabels && values.indexOf(flag) === index,
  );
  return visible.length ? (
    <span className="pokemon-status-flags" aria-label="Estados del Pokémon">
      {visible.map((flag) => (
        <span key={flag} className={`pokemon-status-flag ${flag}`}>
          {statusFlagLabels[flag]}
        </span>
      ))}
    </span>
  ) : null;
}
export function TrainerPhoto({
  name,
  url,
}: {
  name: string;
  url?: string | null;
}) {
  const portrait = portraits[normalize(name)];
  const [failed, setFailed] = useState<string | null>(null);
  const uploaded = url && failed !== url ? url : null;
  return (
    <div className="trainer-photo">
      {uploaded || portrait ? (
        <img
          src={uploaded || `${base}/trainers/${portrait}.png`}
          alt={`Retrato de ${name}`}
          loading="lazy"
          onError={() => {
            if (url) setFailed(url);
          }}
        />
      ) : (
        <UserRound aria-label="Sin foto" />
      )}
    </div>
  );
}
export function PokemonSprite({
  species,
  form,
  large = false,
  animated = false,
}: {
  species: string;
  form?: number | null;
  large?: boolean;
  animated?: boolean;
}) {
  const id = catalogId("species", species);
  const generation = useContext(SpriteGeneration);
  // Only explicitly mapped forms use alternate art; an unknown form is never
  // silently shown as the base form. All asset paths are local catalog entries.
  const variant = form
    ? (formSprites as Record<string, string>)[`${id}:${form}`]
    : id;
  const ownSet = generation ? generationSets[`gen${generation}`] : undefined;
  const still = variant
    ? ownSet?.has(String(variant))
      ? `${base}/gen${generation}/${variant}.png`
      : `${base}/pokemon/${variant}.png`
    : null;
  // Existing animations depict base forms only, in Black/White-era pixel art:
  // never mixed into a Gen6/7 save's renders.
  const animationId =
    !form && id && !ownSet && animatedIds.includes(id) ? id : null;
  const ref = useRef<HTMLImageElement>(null);
  const [moving, setMoving] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [failedAnimation, setFailedAnimation] = useState<number | null>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    setMoving(false);
    if (
      !animated ||
      !animationId ||
      failed === still ||
      !ref.current ||
      typeof IntersectionObserver === "undefined" ||
      typeof window.matchMedia !== "function"
    )
      return;
    let visible = false;
    const update = () => setMoving(visible && !reduced && !document.hidden);
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      update();
    });
    observer.observe(ref.current);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, [animated, animationId, reduced, still, failed]);
  // Keep the still image on screen until the animation has downloaded, so a
  // Pokémon never blinks out while its GIF arrives.
  const [loadedAnimation, setLoadedAnimation] = useState<number | null>(null);
  useEffect(() => {
    if (
      !moving ||
      !animationId ||
      failedAnimation === animationId ||
      loadedAnimation === animationId
    )
      return;
    const preload = new Image();
    preload.onload = () => setLoadedAnimation(animationId);
    preload.onerror = () => setFailedAnimation(animationId);
    preload.src = `/visuals/animated/v1/${animationId}.gif`;
    return () => {
      preload.onload = preload.onerror = null;
    };
  }, [moving, animationId, failedAnimation, loadedAnimation]);
  const animate =
    moving &&
    !!animationId &&
    failedAnimation !== animationId &&
    loadedAnimation === animationId;
  return still && failed !== still ? (
    <img
      ref={ref}
      key={still}
      className={`pokemon-sprite ${large ? "large" : ""}`}
      src={animate ? `/visuals/animated/v1/${animationId}.gif` : still}
      width={96}
      height={96}
      alt={pokemonName("species", species)}
      loading="lazy"
      decoding="async"
      onError={() => {
        if (animate) setFailedAnimation(animationId);
        else {
          console.warn("pokemon_sprite_load_failed", still);
          setFailed(still);
        }
      }}
    />
  ) : still ? (
    <ImageOff
      className="pokemon-sprite unresolved"
      role="img"
      aria-label={`No se pudo cargar la imagen de ${pokemonName("species", species)}`}
    >
      <title>No se pudo cargar la imagen. Vuelve a cargar la pantalla.</title>
    </ImageOff>
  ) : (
    <CircleHelp
      className="pokemon-sprite unresolved"
      aria-label={
        form ? "Imagen de esta forma no disponible" : "Imagen no disponible"
      }
    />
  );
}
const shopArt: Record<string, string> = {
  blindar_pokemon: "Blindar.png",
  robbery_shield_voucher: "Blindar.png",
  revivir_pokemon: "Revivir.png",
  robar_pokemon: "robar.png",
  recaptura: "recaptura.png",
  captura_extra: "captura-extra.png",
  fosil: "fosil.png",
  menta_naturaleza: "menta.svg",
};
export function ItemIcon({ name, code }: { name: string; code?: string }) {
  const id = catalogId("item", name),
    [failed, setFailed] = useState<string | null>(null);
  const path =
    code && shopArt[code]
      ? `${base}/shop/${shopArt[code]}`
      : id && items.has(id)
        ? `${base}/items/${id}.png`
        : code && code in catalogShopArt
          ? `${base}/${catalogShopArt[code as keyof typeof catalogShopArt]}`
          : null;
  return path && failed !== path ? (
    <img
      className="item-icon"
      src={path}
      alt=""
      width={40}
      height={40}
      loading="lazy"
      onError={() => setFailed(path)}
    />
  ) : (
    <Package className="item-icon unavailable" aria-label="Objeto" />
  );
}
const typeSlugs = [
  "normal",
  "fighting",
  "flying",
  "poison",
  "ground",
  "rock",
  "bug",
  "ghost",
  "steel",
  "fire",
  "water",
  "grass",
  "electric",
  "psychic",
  "ice",
  "dragon",
  "dark",
  "fairy",
];
export function typeClass(type?: string) {
  const id = type ? catalogId("type", type) : null;
  return `type-${id == null ? "unknown" : typeSlugs[id] || "unknown"}`;
}
export function TypeBadge({ type }: { type: string }) {
  const slug = typeClass(type).slice(5);
  return (
    <span className={`type-badge ${typeClass(type)}`}>
      {slug !== "unknown" && (
        <img
          src={`${base}/types/${slug}-icon.svg`}
          alt=""
          width={14}
          height={14}
        />
      )}
      {pokemonName("type", type)}
    </span>
  );
}
export function BadgeIcon({
  region,
  number,
  earned,
  label,
  game,
}: {
  game?: string | null;
  region: string;
  number: number;
  earned: boolean | null;
  label: string;
}) {
  const asset = badgeAsset(region, number, game);
  return (
    <span
      className={`game-badge ${earned === null ? "unknown" : earned ? "earned" : "unearned"}`}
      role="img"
      aria-label={label}
      title={label}
    >
      {asset ? (
        <img
          alt=""
          src={`/visuals/badges/v1/${asset}.png`}
          width={30}
          height={30}
          loading="lazy"
        />
      ) : (
        <Award aria-hidden="true" />
      )}
    </span>
  );
}
export function StatPill({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}
export type MoveReference = {
  type: string;
  category: "Physical" | "Special" | "Status";
  power: number | null;
  accuracy: number | null;
  description: string | null;
};
const moveType = (name: string) => {
  const id = catalogId("move", name);
  return id == null ? undefined : (moveTypes as Record<string, string>)[id];
};
/** Compact static move label: Pokemon detail never opens descriptions. */
export function MoveLabel({ name }: { name: string }) {
  return (
    <div className={`move-label ${typeClass(moveType(name))}`}>
      <span className="type-dot" aria-hidden="true" />
      {pokemonName("move", name)}
    </div>
  );
}
export function IVBars({ values }: { values?: Record<string, number> | null }) {
  if (!values) return <p className="muted">IVs no disponibles.</p>;
  return (
    <div className="iv-bars" aria-label="Valores individuales">
      {["hp", "atk", "defense", "spa", "spd", "spe"].map((stat) => {
        const value = values[stat];
        const known = Number.isInteger(value) && value >= 0 && value <= 31;
        return (
          <div className={`iv-row iv-${stat}`} key={stat}>
            <span>{statName(stat)}</span>
            <span
              className="iv-track"
              role={known ? "meter" : undefined}
              aria-label={statName(stat)}
              aria-valuemin={known ? 0 : undefined}
              aria-valuemax={known ? 31 : undefined}
              aria-valuenow={known ? value : undefined}
            >
              <span
                style={{ width: known ? `${(value / 31) * 100}%` : "0%" }}
              />
            </span>
            <strong>{known ? value : "—"}</strong>
          </div>
        );
      })}
    </div>
  );
}
let reference: Promise<Record<string, MoveReference>> | undefined;
/** Local reference data only; one compact disclosure across the visible team. */
export function MovePopover({
  name,
  pp,
}: {
  name: string;
  pp?: number | null;
}) {
  const id = useId(),
    move = catalogId("move", name);
  const trigger = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<{
    move: number | null;
    info: MoveReference | null;
  } | null>(null);
  const [failed, setFailed] = useState(false);
  const info = result?.move === move ? result.info : null;
  useEffect(() => {
    setOpen(false);
    setResult(null);
    setFailed(false);
  }, [name]);
  useEffect(() => {
    if (!open) return;
    const dismiss = () => setOpen(false);
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    window.addEventListener("pokeapp:move-open", dismiss);
    window.addEventListener("keydown", escape, true);
    return () => {
      window.removeEventListener("pokeapp:move-open", dismiss);
      window.removeEventListener("keydown", escape, true);
    };
  }, [open]);
  async function load() {
    if (result?.move === move) return;
    setFailed(false);
    try {
      reference ??= fetch(`${base}/moves-xy.json`)
        .then((r) => {
          if (!r.ok) throw Error();
          return r.json();
        })
        .catch((e) => {
          reference = undefined;
          throw e;
        });
      const values = await reference;
      setResult({ move, info: move == null ? null : (values[move] ?? null) });
    } catch {
      setFailed(true);
    }
  }
  return (
    <div className={`move-disclosure ${typeClass(moveType(name))}`}>
      <button
        ref={trigger}
        type="button"
        className="move-button"
        aria-expanded={open}
        aria-controls={id}
        aria-label={`Ver ${pokemonName("move", name)}`}
        onClick={() => {
          if (!open) {
            window.dispatchEvent(new Event("pokeapp:move-open"));
            void load();
          }
          setOpen(!open);
        }}
      >
        <span className="type-dot" aria-hidden="true" />
        <span className="move-name">{pokemonName("move", name)}</span>
        {pp != null && <small>{pp} PP</small>}
        <ChevronDown size={13} aria-hidden="true" />
      </button>
      {open && (
        <div
          id={id}
          className="move-expansion"
          role="region"
          aria-label={`Detalles de ${pokemonName("move", name)}`}
        >
          <div className="move-expansion-heading">
            <span>Referencia Pokémon X/Y</span>
            <button
              className="icon-button"
              aria-label="Cerrar movimiento"
              onClick={() => {
                setOpen(false);
                trigger.current?.focus();
              }}
            >
              <X size={14} />
            </button>
          </div>
          {info ? (
            <>
              <div className="move-facts">
                <TypeBadge type={info.type} />
                <span className="move-category">
                  <img
                    src={`${base}/categories/${info.category}.png`}
                    width={32}
                    height={14}
                    alt=""
                  />
                  {
                    {
                      Physical: "Físico",
                      Special: "Especial",
                      Status: "Estado",
                    }[info.category]
                  }
                </span>
              </div>
              <div className="move-numbers">
                <span>
                  Potencia <strong>{info.power || "—"}</strong>
                </span>
                <span>
                  Precisión{" "}
                  <strong>
                    {info.accuracy == null ? "—" : `${info.accuracy}%`}
                  </strong>
                </span>
              </div>
              <p>{info.description || "Descripción no disponible para X/Y."}</p>
            </>
          ) : (
            <p role="status">
              {failed || result?.move === move
                ? "Información no disponible."
                : "Cargando movimiento…"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
