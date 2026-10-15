import { useId, useState } from "react";
import { Award, CircleHelp, Package, UserRound } from "lucide-react";
import { catalogId, pokemonName } from "./localization";
import itemIds from "./visual-items.json";

const base = "/visuals/v1";
const items = new Set(itemIds);
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
export function TrainerPhoto({ name }: { name: string }) {
  const portrait = portraits[normalize(name)];
  return (
    <div className="trainer-photo">
      {portrait ? (
        <img
          src={`${base}/trainers/${portrait}.png`}
          alt={`Retrato de ${name}`}
          loading="lazy"
        />
      ) : (
        <UserRound aria-label="Sin foto" />
      )}
    </div>
  );
}
export function PokemonSprite({
  species,
  large = false,
}: {
  species: string;
  large?: boolean;
}) {
  const id = catalogId("species", species);
  const [failed, setFailed] = useState<string | null>(null);
  return id && failed !== species ? (
    <img
      className={`pokemon-sprite ${large ? "large" : ""}`}
      src={`${base}/pokemon/${id}.png`}
      width={96}
      height={96}
      alt={pokemonName("species", species)}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(species)}
    />
  ) : (
    <CircleHelp
      className="pokemon-sprite unresolved"
      aria-label="Imagen no disponible"
    />
  );
}
const shopArt: Record<string, string> = {
  blindar_pokemon: "Blindar.png",
  robbery_shield_voucher: "Blindar.png",
  revivir_pokemon: "Revivir.png",
  robar_pokemon: "robar.png",
  recaptura: "recaptura.png",
};
export function ItemIcon({ name, code }: { name: string; code?: string }) {
  const id = catalogId("item", name),
    [failed, setFailed] = useState<string | null>(null);
  const path =
    code && shopArt[code]
      ? `${base}/shop/${shopArt[code]}`
      : id && items.has(id)
        ? `${base}/items/${id}.png`
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
export function TypeBadge({ type }: { type: string }) {
  const id = catalogId("type", type),
    slug = id == null ? null : typeSlugs[id];
  return (
    <span className={`type-badge type-${slug || "unknown"}`}>
      {slug && (
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
const sinnoh = [
  "Lignito",
  "Bosque",
  "Adoquin",
  "Cienaga",
  "Reliquia",
  "Mina",
  "Carambano",
  "Faro",
];
export function BadgeIcon({
  region,
  number,
  earned,
  label,
}: {
  region: string;
  number: number;
  earned: boolean;
  label: string;
}) {
  return (
    <span
      className={`game-badge ${earned ? "earned" : "unearned"}`}
      role="img"
      aria-label={label}
      title={label}
    >
      {region === "sinnoh" ? (
        <img
          alt=""
          src={`${base}/medallas/Medalla_${sinnoh[number - 1]}.png`}
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
let reference: Promise<Record<string, MoveReference>> | undefined;
export function MovePopover({
  name,
  pp,
}: {
  name: string;
  pp?: number | null;
}) {
  const id = useId(),
    move = catalogId("move", name);
  const [info, setInfo] = useState<MoveReference | null>(null);
  const [loaded, setLoaded] = useState(false);
  async function load() {
    if (loaded) return;
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
      setInfo(move == null ? null : (values[move] ?? null));
      setLoaded(true);
    } catch {
      setInfo(null);
    }
  }
  return (
    <>
      <button
        type="button"
        className="move-button"
        popoverTarget={id}
        onClick={() => void load()}
        aria-label={`Ver ${pokemonName("move", name)}`}
      >
        <span>{pokemonName("move", name)}</span>
        {pp != null && <small>{pp} PP</small>}
        <CircleHelp size={13} />
      </button>
      <div id={id} popover="auto" className="move-popover">
        <div className="section-row">
          <h3>{pokemonName("move", name)}</h3>
          <button
            className="icon-button"
            popoverTarget={id}
            popoverTargetAction="hide"
            aria-label="Cerrar movimiento"
          >
            ×
          </button>
        </div>
        <p className="caption">Referencia Pokémon X/Y</p>
        {info ? (
          <>
            <div className="tags">
              <TypeBadge type={info.type} />
              <span className="move-category">
                <img
                  src={`${base}/categories/${info.category}.png`}
                  width={32}
                  height={14}
                  alt=""
                />
                {
                  { Physical: "Físico", Special: "Especial", Status: "Estado" }[
                    info.category
                  ]
                }
              </span>
            </div>
            <div className="mini-stats">
              <StatPill label="Potencia" value={info.power || "—"} />
              <StatPill
                label="Precisión"
                value={info.accuracy == null ? "—" : `${info.accuracy}%`}
              />
            </div>
            <p>{info.description || "Descripción no disponible para X/Y."}</p>
          </>
        ) : (
          <p>Información no disponible.</p>
        )}
      </div>
    </>
  );
}
