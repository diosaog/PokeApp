import type { BudgetConfig, CostBreakdown } from "@/domain/economy/types";
import type { BreedingAction } from "@/domain/optimization/types";
import type { IvSpread, PokemonInstance, PokemonSex } from "@/domain/pokemon/types";
import { createDefaultInventory } from "@/domain/economy/items";
import { diosesmonProfile } from "@/rules/diosesmon/profile";

export const budget = (money = 100_000): BudgetConfig => ({
  unlimited: false,
  money,
  metric: "replacement",
});

export const inventory = () => createDefaultInventory(diosesmonProfile.economy.defaultItemPrice);

export const ivs = (partial: Partial<IvSpread> = {}): IvSpread => ({
  hp: 0,
  attack: 0,
  defense: 0,
  specialAttack: 0,
  specialDefense: 0,
  speed: 0,
  ...partial,
});

export const pokemon = ({
  id,
  speciesId,
  sex,
  spread,
  protectedPokemon = false,
  canBreed = true,
  availableAtMinute = 0,
}: {
  id: string;
  speciesId: string;
  sex: PokemonSex;
  spread?: Partial<IvSpread>;
  protectedPokemon?: boolean;
  canBreed?: boolean;
  availableAtMinute?: number;
}): PokemonInstance => ({
  id,
  speciesId,
  sex,
  ivs: ivs(spread),
  canBreed,
  availableAtMinute,
  protected: protectedPokemon,
});

const cost = (metricCost: number): CostBreakdown => ({
  breedingCost: metricCost,
  purchasedItemsCost: 0,
  consumedItemsValue: 0,
  forcedSexCost: 0,
  directCashCost: metricCost,
  replacementCost: metricCost,
  metricCost,
  purchasedItems: [],
  consumedItems: [],
});

export const action = ({
  id,
  metricCost,
  minutes,
  directTargetProbability,
  usefulBreederProbability,
  expectedImprovement,
}: {
  id: string;
  metricCost: number;
  minutes: number;
  directTargetProbability: number;
  usefulBreederProbability: number;
  expectedImprovement: number;
}): BreedingAction => ({
  id,
  parentAId: "a",
  parentBId: "b",
  offspringSpeciesId: "eevee",
  sharedEggGroups: ["field"],
  items: [],
  cost: cost(metricCost),
  schedule: {
    workMinutes: minutes,
    clockMinutes: minutes,
    waitingMinutes: 0,
    eggCount: 1,
    rounds: 1,
    slotUtilization: 1,
    warnings: [],
  },
  directTargetProbability,
  usefulBreederProbability,
  expectedImprovement,
  expectedTotalCost: metricCost,
  expectedTotalMinutes: minutes,
  score: metricCost,
  warnings: [],
  explanation: [],
  howCalculated: {
    inheritedStats: 3,
    actionCount: 1,
    statesExplored: 1,
    simulations: 0,
    seed: 1,
    depth: 1,
    elapsedMs: 0,
  },
});
