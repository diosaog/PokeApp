// Hall de la Fama › Leyendas: the champions of the competitions played before
// PokeApp (owner's list, 2026-11-18). Static presentation content: these
// titles have no PokeApp season, save or account behind them, so they never
// enter the certified `hall_of_fame_entries` and change nothing in the League.
// To add one, append a title to its trainer (or a new trainer); the portrait
// comes from the trainer's name (see TrainerPhoto).

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
          { species: "Camerupt" },
          { species: "Gyarados" },
          { species: "Tyranitar" },
          { species: "Metagross" },
          { species: "Rhydon" },
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
          { species: "Deoxys", form: 1, label: "Deoxys (forma Ataque)" },
          { species: "Salamence" },
          { species: "Cloyster" },
          { species: "Rotom", form: 2, label: "Rotom Lavado" },
          { species: "Charizard" },
          { species: "Blissey" },
        ],
      },
    ],
  },
];
