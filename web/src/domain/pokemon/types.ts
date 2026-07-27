export const statKeys = [
  "hp",
  "attack",
  "defense",
  "specialAttack",
  "specialDefense",
  "speed",
] as const;

export type StatKey = (typeof statKeys)[number];

export const statLabels: Record<StatKey, string> = {
  hp: "PS",
  attack: "Ataque",
  defense: "Defensa",
  specialAttack: "Ataque Esp.",
  specialDefense: "Defensa Esp.",
  speed: "Velocidad",
};

export const fullStatLabels: Record<StatKey, string> = {
  hp: "Puntos de Salud",
  attack: "Ataque",
  defense: "Defensa",
  specialAttack: "Ataque Especial",
  specialDefense: "Defensa Especial",
  speed: "Velocidad",
};

export type PokemonSex = "male" | "female" | "genderless" | "unknown";

export const sexLabels: Record<PokemonSex, string> = {
  male: "Macho",
  female: "Hembra",
  genderless: "Sin genero",
  unknown: "Desconocido",
};

export interface IvSpread {
  hp: number;
  attack: number;
  defense: number;
  specialAttack: number;
  specialDefense: number;
  speed: number;
}

export type IvConstraint =
  | { kind: "any" }
  | { kind: "exact31" }
  | { kind: "min"; value: number }
  | { kind: "range"; min: number; max: number }
  | { kind: "exact"; value: number }
  | { kind: "preferred"; value: number; weight: number };

export type TargetSex = PokemonSex | "any";

export interface BreedingTarget {
  speciesId: string;
  ivs: Record<StatKey, IvConstraint>;
  sex: TargetSex;
  natureId?: string;
  abilityId?: string;
}

export type EggGroupId =
  | "ditto"
  | "field"
  | "monster"
  | "water1"
  | "water2"
  | "dragon"
  | "fairy"
  | "flying"
  | "humanLike"
  | "bug"
  | "grass"
  | "mineral"
  | "amorphous"
  | "noEggs";

export interface SpeciesData {
  id: string;
  names: {
    es: string;
    en: string;
  };
  forms: string[];
  eggBaseSpeciesId: string;
  eggGroups: EggGroupId[];
  genderRatio: {
    male: number;
    female: number;
  } | null;
  genderless: boolean;
  canBreed: boolean;
  abilities: string[];
  hiddenAbility?: string;
  breedingExceptions?: string[];
}

export interface PokemonInstance {
  id: string;
  nickname?: string;
  speciesId: string;
  formId?: string;
  sex: PokemonSex;
  ivs: IvSpread;
  natureId?: string;
  abilityId?: string;
  isHiddenAbility?: boolean;
  canBreed: boolean;
  availableAtMinute: number;
  protected: boolean;
  notes?: string;
}

export const blankIvs = (): IvSpread => ({
  hp: 0,
  attack: 0,
  defense: 0,
  specialAttack: 0,
  specialDefense: 0,
  speed: 0,
});

export const defaultTargetIvs = (): Record<StatKey, IvConstraint> => ({
  hp: { kind: "exact31" },
  attack: { kind: "any" },
  defense: { kind: "exact31" },
  specialAttack: { kind: "exact31" },
  specialDefense: { kind: "exact31" },
  speed: { kind: "exact31" },
});
