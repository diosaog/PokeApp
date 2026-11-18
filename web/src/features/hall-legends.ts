// Hall de la Fama › Leyendas: the champions of the competitions played before
// PokeApp (owner's list, 2026-11-18). Static presentation content: these
// titles have no PokeApp season, save or account behind them, so they never
// enter the certified `hall_of_fame_entries` and change nothing in the League.
// To add one, append a title to its trainer (or a new trainer); the portrait
// comes from the trainer's name (see TrainerPhoto).

import formSprites from "../pokemon/visual-forms.json";
import { catalogId } from "../pokemon/localization";

/** Visual theme of a title, from the colours of its game. */
export type LegendTheme =
  "anil" | "rojo-fuego" | "copa-rojo-fuego" | "rubi-omega" | "platino";

export type LegendPokemon = {
  /** Species, by its Spanish or English name (resolved by the catalog). */
  species: string;
  /** PKHeX form number, only for an alternate form (e.g. Deoxys Attack = 1). */
  form?: number;
  /** Shown instead of the species when a form needs it (e.g. «Mega-Alakazam»). */
  label?: string;
  /** Held item, Spanish or English. Never shown: it only picks the Mega art. */
  item?: string;
};

export type LegendTitle = {
  id: string;
  /** «Pokémon Rojo Fuego»: the small line above the game name. */
  series: string;
  game: string;
  kind: "liga" | "copa";
  theme: LegendTheme;
  team: LegendPokemon[];
};

export type Legend = { trainer: string; titles: LegendTitle[] };

export const legends: Legend[] = [
  {
    trainer: "Samu",
    titles: [
      {
        id: "samu-anil",
        series: "Pokémon",
        game: "Añil",
        kind: "liga",
        theme: "anil",
        team: [
          { species: "Slaking" },
          { species: "Chandelure" },
          { species: "Dusknoir" },
          { species: "Kommo-o" },
          { species: "Skarmory" },
          { species: "Alakazam", form: 1, label: "Mega-Alakazam" },
        ],
      },
      {
        id: "samu-rojo-fuego",
        series: "Pokémon",
        game: "Rojo Fuego",
        kind: "liga",
        theme: "rojo-fuego",
        team: [
          { species: "Milotic" },
          { species: "Gengar" },
          { species: "Espeon" },
          { species: "Metagross" },
          { species: "Salamence" },
          { species: "Slaking" },
        ],
      },
      {
        id: "samu-copa-rojo-fuego",
        series: "Copa",
        game: "Rojo Fuego",
        kind: "copa",
        theme: "copa-rojo-fuego",
        team: [
          { species: "Dragonite" },
          { species: "Metagross" },
          { species: "Alakazam" },
          { species: "Salamence" },
          { species: "Milotic" },
          { species: "Tyranitar" },
        ],
      },
    ],
  },
  {
    trainer: "Miguel",
    titles: [
      {
        id: "miguel-rubi-omega",
        series: "Pokémon",
        game: "Rubí Omega",
        kind: "liga",
        theme: "rubi-omega",
        team: [
          { species: "Camerupt", item: "Cameruptite" },
          { species: "Gyarados", item: "Choice Band" },
          { species: "Tyranitar", item: "Mystic Water" },
          { species: "Metagross", item: "Sitrus Berry" },
          { species: "Rhydon", item: "Eviolite" },
          { species: "Dusknoir" },
        ],
      },
      {
        id: "miguel-platino",
        series: "Pokémon",
        game: "Platino",
        kind: "liga",
        theme: "platino",
        team: [
          {
            species: "Deoxys",
            form: 1,
            label: "Deoxys (forma Ataque)",
            item: "Focus Sash",
          },
          { species: "Salamence", item: "Sitrus Berry" },
          { species: "Cloyster", item: "Life Orb" },
          {
            species: "Rotom",
            form: 2,
            label: "Rotom Lavado",
            item: "Lum Berry",
          },
          { species: "Charizard", item: "Choice Specs" },
          { species: "Blissey", item: "Leftovers" },
        ],
      },
    ],
  },
];

// Owner rule 2026-11-18, Hall de la Fama only: a Pokémon holding its OWN Mega
// Stone is shown directly as its Mega Evolution. Stone → [species, PKHeX form].
const megaStones: Record<string, [string, number]> = {
  Venusaurite: ["Venusaur", 1],
  "Charizardite X": ["Charizard", 1],
  "Charizardite Y": ["Charizard", 2],
  Blastoisinite: ["Blastoise", 1],
  Beedrillite: ["Beedrill", 1],
  Pidgeotite: ["Pidgeot", 1],
  Alakazite: ["Alakazam", 1],
  Slowbronite: ["Slowbro", 1],
  Gengarite: ["Gengar", 1],
  Kangaskhanite: ["Kangaskhan", 1],
  Pinsirite: ["Pinsir", 1],
  Gyaradosite: ["Gyarados", 1],
  Aerodactylite: ["Aerodactyl", 1],
  "Mewtwonite X": ["Mewtwo", 1],
  "Mewtwonite Y": ["Mewtwo", 2],
  Ampharosite: ["Ampharos", 1],
  Steelixite: ["Steelix", 1],
  Scizorite: ["Scizor", 1],
  Heracronite: ["Heracross", 1],
  Houndoominite: ["Houndoom", 1],
  Tyranitarite: ["Tyranitar", 1],
  Sceptilite: ["Sceptile", 1],
  Blazikenite: ["Blaziken", 1],
  Swampertite: ["Swampert", 1],
  Gardevoirite: ["Gardevoir", 1],
  Sablenite: ["Sableye", 1],
  Mawilite: ["Mawile", 1],
  Aggronite: ["Aggron", 1],
  Medichamite: ["Medicham", 1],
  Manectite: ["Manectric", 1],
  Sharpedonite: ["Sharpedo", 1],
  Cameruptite: ["Camerupt", 1],
  Altarianite: ["Altaria", 1],
  Banettite: ["Banette", 1],
  Absolite: ["Absol", 1],
  Glalitite: ["Glalie", 1],
  Salamencite: ["Salamence", 1],
  Metagrossite: ["Metagross", 1],
  Latiasite: ["Latias", 1],
  Latiosite: ["Latios", 1],
  Lopunnite: ["Lopunny", 1],
  Garchompite: ["Garchomp", 1],
  Lucarionite: ["Lucario", 1],
  Abomasite: ["Abomasnow", 1],
  Galladite: ["Gallade", 1],
  Audinite: ["Audino", 1],
  Diancite: ["Diancie", 1],
};
// Resolved by catalog id, so a Spanish item name («Cameruptita») works too.
const megaByItem = new Map<
  number,
  { id: number; form: number; label: string }
>();
for (const [stone, [species, form]] of Object.entries(megaStones)) {
  const item = catalogId("item", stone),
    id = catalogId("species", species);
  const variant = / ([XY])$/.exec(stone)?.[1];
  if (item != null && id != null)
    megaByItem.set(item, {
      id,
      form,
      label: `Mega-${species}${variant ? ` ${variant}` : ""}`,
    });
}

/**
 * What the Hall shows for one Pokémon: its Mega Evolution when it holds its
 * own Mega Stone and that Mega has art here; otherwise exactly what the list
 * says. A stone of another species (or an unknown item) changes nothing.
 */
export function legendSprite(pokemon: LegendPokemon): LegendPokemon {
  const item = pokemon.item ? catalogId("item", pokemon.item) : null;
  const mega = item == null ? undefined : megaByItem.get(item);
  const id = catalogId("species", pokemon.species);
  if (
    !mega ||
    pokemon.form ||
    mega.id !== id ||
    !(`${id}:${mega.form}` in formSprites)
  )
    return pokemon;
  return { ...pokemon, form: mega.form, label: mega.label };
}
