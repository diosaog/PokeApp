import catalog from "./catalog.es.json";

export type Category =
  "species" | "move" | "ability" | "item" | "type" | "nature";
type Names = { en: string[]; es: string[] };
const names: Record<Category | "item3", Names> = catalog.categories;

// Presentation only. Never use translated names to identify a Pokémon or a command.
const key = (value: string) =>
  value
    .replaceAll("♀", " female ")
    .replaceAll("♂", " male ")
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
const valid = (value: string | undefined): value is string =>
  !!value && !/^[\s?\-–—()0-9]+$/.test(value) && !value.includes("???");
const firstId = (category: Category) =>
  category === "type" || category === "nature" ? 0 : 1;
function labelAt(table: Names, id: number) {
  return valid(table.es[id])
    ? table.es[id]
    : valid(table.en[id])
      ? table.en[id]
      : undefined;
}

// Alias indices are built once. A name collision never arbitrarily chooses an ID.
const aliases = Object.fromEntries(
  (Object.keys(names) as (Category | "item3")[]).map((category) => {
    const index = new Map<string, string | null>();
    const table = names[category];
    for (
      let id = firstId(category === "item3" ? "item" : category);
      id < table.en.length;
      id++
    ) {
      const label = labelAt(table, id);
      if (!label) continue;
      for (const alias of [table.en[id], table.es[id]]) {
        if (!valid(alias)) continue;
        const normalized = key(alias);
        const previous = index.get(normalized);
        index.set(
          normalized,
          previous === undefined || previous === label ? label : null,
        );
      }
    }
    return [category, index];
  }),
) as Record<Category | "item3", Map<string, string | null>>;

const unavailable: Record<Category, string> = {
  species: "Especie no disponible",
  move: "Movimiento no disponible",
  ability: "Habilidad no disponible",
  item: "Objeto no disponible",
  type: "Tipo no disponible",
  nature: "Naturaleza no disponible",
};
const prefixes: Record<Category, RegExp> = {
  species: /^(?:pok[eé]mon|species|especie)\s*#?\s*(\d+)$/i,
  move: /^(?:move|movimiento)\s*#?\s*(\d+)$/i,
  ability: /^(?:ability|habilidad)\s*#?\s*(\d+)$/i,
  item: /^(?:item|objeto)\s*#?\s*(\d+)$/i,
  type: /^(?:type|tipo)\s*#?\s*(\d+)$/i,
  nature: /^(?:nature|naturaleza)\s*#?\s*(\d+)$/i,
};

export function pokemonName(
  category: Category,
  value: string | number | null | undefined,
  // Reserved for a future projection with explicit source context. Current web
  // callers MUST NOT infer generation from species, progress or the viewer's save.
  itemGeneration?: 3 | 4 | 5 | 6,
): string {
  const text = String(value ?? "").trim();
  if (!text || text === "—" || text === "-") return unavailable[category];
  const match = /^(?:#\s*)?(\d+)$/.exec(text) ?? prefixes[category].exec(text);
  if (match) {
    const id = Number(match[1]);
    if (!Number.isSafeInteger(id) || id < firstId(category))
      return unavailable[category];
    if (category === "item") {
      if (itemGeneration === 3)
        return labelAt(names.item3, id) ?? unavailable.item;
      const modern = labelAt(names.item, id);
      if (itemGeneration) return modern ?? unavailable.item;
      // PK3 IDs are not the Gen4+ national item IDs. Existing string projections
      // omit game context, so ambiguous numeric objects cannot be named safely.
      const legacy = labelAt(names.item3, id);
      if (legacy && modern && key(legacy) !== key(modern))
        return "Objeto sin identificar (falta el juego)";
      return modern ?? legacy ?? unavailable.item;
    }
    return labelAt(names[category], id) ?? unavailable[category];
  }
  const translated = aliases[category].get(key(text));
  if (translated) return translated;
  if (category === "item") {
    const legacy = aliases.item3.get(key(text));
    if (legacy) return legacy;
  }
  // Preserve existing neutral canonical names (including unknown forms/custom shop
  // names), but never expose a missing technical label as a human name.
  if (
    /[_#{}<>]|^(?:pokemon|pokémon|species|move|ability|item|type|nature)\s*\d|^[-+]?\d+(?:\.\d+)?$|^(?:unknown|null|undefined|none)$/i.test(
      text,
    )
  )
    return unavailable[category];
  return text;
}

export function pokemonTitle(pokemon: { nickname?: string; species: string }) {
  // Nicknames are user data; never translate or reinterpret them as catalog keys.
  return pokemon.nickname || pokemonName("species", pokemon.species);
}

const stats: Record<string, string> = {
  hp: "PS",
  atk: "Ataque",
  defense: "Defensa",
  spa: "At. Esp.",
  spd: "Def. Esp.",
  spe: "Velocidad",
};
export const statName = (stat: string) => stats[stat] ?? "Característica";
