import type { EquippedItem } from "@/domain/economy/types";
import type { IvSpread, PokemonSex, SpeciesData } from "@/domain/pokemon/types";
import { statKeys } from "@/domain/pokemon/types";
import { enumerateInheritancePatterns } from "@/engine/inheritance/probability";
import { getSexDistribution } from "@/engine/inheritance/sex";
import { createSeededRandom } from "@/engine/simulation/prng";
import type { InheritanceRules, OffspringRules } from "@/rules/types";

export interface SimulatedEgg {
  ivs: IvSpread;
  sex: PokemonSex;
}

const pickWeighted = <T extends { probability: number }>(items: readonly T[], roll: number): T => {
  let cumulative = 0;
  for (const item of items) {
    cumulative += item.probability;
    if (roll <= cumulative) {
      return item;
    }
  }
  const fallback = items[items.length - 1];
  if (!fallback) {
    throw new Error("No hay resultados para seleccionar.");
  }
  return fallback;
};

export const simulateEgg = ({
  parentAIvs,
  parentBIvs,
  items,
  inheritanceRules,
  offspringRules,
  species,
  forcedSex,
  seed,
}: {
  parentAIvs: IvSpread;
  parentBIvs: IvSpread;
  items: EquippedItem[];
  inheritanceRules: InheritanceRules;
  offspringRules: OffspringRules;
  species: SpeciesData;
  forcedSex?: PokemonSex;
  seed: number;
}): SimulatedEgg => {
  const rng = createSeededRandom(seed);
  const { patterns } = enumerateInheritancePatterns(parentAIvs, parentBIvs, items, inheritanceRules);
  const pattern = pickWeighted(patterns, rng.next());
  const ivs = {} as IvSpread;

  for (const stat of statKeys) {
    const inherited = pattern.inherited[stat];
    ivs[stat] = inherited ? inherited.value : Math.floor(rng.next() * 32);
  }

  const { distribution } = getSexDistribution(species, "any", forcedSex, offspringRules);
  const sex = pickWeighted(distribution, rng.next()).sex;

  return { ivs, sex };
};
