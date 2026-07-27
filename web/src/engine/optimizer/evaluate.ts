import type { BudgetConfig, InventoryState } from "@/domain/economy/types";
import type { BreedingAction, EngineWarning, OptimizationGoal } from "@/domain/optimization/types";
import type { BreedingTarget, PokemonInstance, PokemonSex, SpeciesData } from "@/domain/pokemon/types";
import { getSpeciesName } from "@/data/species";
import { generateItemPlans } from "@/engine/actions/itemPlans";
import { canBreed } from "@/engine/compatibility/canBreed";
import { calculateAttemptCost } from "@/engine/economy/costs";
import { getSexDistribution } from "@/engine/inheritance/sex";
import { summarizeEggProbability } from "@/engine/inheritance/probability";
import { getOffspringSpecies } from "@/engine/offspring/getOffspringSpecies";
import { estimateSingleAttemptSchedule } from "@/engine/scheduling/schedule";
import type { ServerProfile } from "@/rules/types";
import { safeDivide } from "@/utils/math";

const sexOptionsForTarget = (
  target: BreedingTarget,
  offspringSpecies: SpeciesData,
  profile: ServerProfile,
): Array<PokemonSex | undefined> => {
  if (
    target.sex === "male" ||
    target.sex === "female" ||
    target.sex === "genderless"
  ) {
    if (offspringSpecies.genderless) {
      return [undefined];
    }
    if (profile.offspring.forcedSexAvailable && target.sex !== "genderless") {
      return [undefined, target.sex];
    }
  }
  return [undefined];
};

const targetSexProbability = (
  species: SpeciesData,
  targetSex: BreedingTarget["sex"],
  forcedSex: PokemonSex | undefined,
  profile: ServerProfile,
): { probability: number; warnings: EngineWarning[] } => {
  const { distribution, warnings } = getSexDistribution(species, targetSex, forcedSex, profile.offspring);

  if (targetSex === "any") {
    return {
      probability: 1,
      warnings: warnings.map((message) => ({ code: "sex-rule", message })),
    };
  }

  return {
    probability: distribution
      .filter((entry) => entry.sex === targetSex)
      .reduce((total, entry) => total + entry.probability, 0),
    warnings: warnings.map((message) => ({ code: "sex-rule", message })),
  };
};

const speciesBridgeMultiplier = (
  offspringSpecies: SpeciesData,
  targetSpecies: SpeciesData,
): number => {
  if (offspringSpecies.id === targetSpecies.id || offspringSpecies.eggBaseSpeciesId === targetSpecies.id) {
    return 1;
  }

  const sharesGroup = offspringSpecies.eggGroups.some((group) => targetSpecies.eggGroups.includes(group));
  if (sharesGroup) {
    return offspringSpecies.eggGroups.length > 1 ? 0.75 : 0.55;
  }

  return offspringSpecies.eggGroups.length > 1 ? 0.35 : 0.1;
};

const scoreAction = (
  cost: number,
  minutes: number,
  directTargetProbability: number,
  usefulBreederProbability: number,
  expectedImprovement: number,
  goal: OptimizationGoal,
): { expectedTotalCost: number; expectedTotalMinutes: number; score: number } => {
  const effectiveSuccess = Math.min(
    1,
    directTargetProbability + usefulBreederProbability * 0.35 + safeDivide(expectedImprovement, 6) * 0.25,
  );
  const divisor = Math.max(0.0025, effectiveSuccess);
  const expectedTotalCost = cost / divisor;
  const expectedTotalMinutes = minutes / divisor;

  if (goal === "cheapest") {
    return { expectedTotalCost, expectedTotalMinutes, score: expectedTotalCost };
  }

  if (goal === "fastest") {
    return { expectedTotalCost, expectedTotalMinutes, score: expectedTotalMinutes * 120 + cost * 0.08 };
  }

  return {
    expectedTotalCost,
    expectedTotalMinutes,
    score: expectedTotalCost * 0.72 + expectedTotalMinutes * 28,
  };
};

export const evaluatePairActions = ({
  parentA,
  parentB,
  speciesById,
  target,
  profile,
  inventory,
  budget,
  nowMinute,
  seed,
  precise,
  goal,
}: {
  parentA: PokemonInstance;
  parentB: PokemonInstance;
  speciesById: ReadonlyMap<string, SpeciesData>;
  target: BreedingTarget;
  profile: ServerProfile;
  inventory: InventoryState;
  budget: BudgetConfig;
  nowMinute: number;
  seed: number;
  precise: boolean;
  goal: OptimizationGoal;
}): BreedingAction[] => {
  const compatibility = canBreed(parentA, parentB, speciesById, profile.offspring, nowMinute);
  if (!compatibility.valid) {
    return [];
  }

  const offspring = getOffspringSpecies(parentA, parentB, speciesById);
  if (!offspring.speciesId) {
    return [];
  }

  const offspringSpecies = speciesById.get(offspring.speciesId);
  const targetSpecies = speciesById.get(target.speciesId);
  if (!offspringSpecies || !targetSpecies) {
    return [];
  }

  const itemPlans = generateItemPlans(parentA.ivs, parentB.ivs, target, precise);
  const forcedSexOptions = sexOptionsForTarget(target, offspringSpecies, profile);
  const actions: BreedingAction[] = [];
  const bridgeMultiplier = speciesBridgeMultiplier(offspringSpecies, targetSpecies);

  for (const items of itemPlans) {
    for (const forcedSex of forcedSexOptions) {
      const costResult = calculateAttemptCost({
        economy: profile.economy,
        inventory,
        budget,
        items,
        forceSex: forcedSex !== undefined,
      });

      if (!costResult.ok) {
        continue;
      }

      const probability = summarizeEggProbability(parentA.ivs, parentB.ivs, target.ivs, items, profile.inheritance);
      const { probability: sexProbability, warnings: sexWarnings } = targetSexProbability(
        offspringSpecies,
        target.sex,
        forcedSex,
        profile,
      );
      const sameSpeciesMultiplier = offspringSpecies.id === target.speciesId ? 1 : 0;
      const directTargetProbability = probability.directTargetProbability * sexProbability * sameSpeciesMultiplier;
      const usefulBreederProbability = probability.usefulBreederProbability * bridgeMultiplier;
      const schedule = estimateSingleAttemptSchedule(profile.time, parentA, parentB, nowMinute);
      const score = scoreAction(
        costResult.breakdown.metricCost,
        schedule.clockMinutes,
        directTargetProbability,
        usefulBreederProbability,
        probability.expectedImprovement,
        goal,
      );
      const warnings: EngineWarning[] = [
        ...compatibility.warnings.map((message) => ({ code: "compatibility", message })),
        ...offspring.warnings.map((message) => ({ code: "offspring", message })),
        ...probability.warnings.map((message) => ({ code: "inheritance", message })),
        ...sexWarnings,
        ...schedule.warnings.map((message) => ({ code: "time", message })),
      ];
      const itemText =
        items.length === 0
          ? "sin objetos"
          : items.map((item) => `${item.parent === "parentA" ? "Primer progenitor" : "Segundo progenitor"}: ${item.itemId}`).join(", ");

      actions.push({
        id: `${parentA.id}_${parentB.id}_${items.map((item) => `${item.parent}-${item.itemId}`).join("_")}_${forcedSex ?? "random"}`,
        parentAId: parentA.id,
        parentBId: parentB.id,
        ...(offspring.motherId ? { motherId: offspring.motherId } : {}),
        ...(offspring.fatherId ? { fatherId: offspring.fatherId } : {}),
        offspringSpeciesId: offspring.speciesId,
        sharedEggGroups: compatibility.sharedEggGroups,
        items,
        ...(forcedSex ? { forcedSex } : {}),
        cost: costResult.breakdown,
        schedule,
        directTargetProbability,
        usefulBreederProbability,
        expectedImprovement: probability.expectedImprovement,
        expectedTotalCost: score.expectedTotalCost,
        expectedTotalMinutes: score.expectedTotalMinutes,
        score: score.score,
        warnings,
        explanation: [
          `Pareja compatible por ${compatibility.sharedEggGroups.join(", ")}.`,
          offspring.explanation,
          `Descendencia esperada: ${getSpeciesName(offspring.speciesId)}.`,
          `Objetos evaluados: ${itemText}.`,
          forcedSex ? "Se compara pagar por sexo objetivo." : "Se acepta sexo aleatorio en este intento.",
          "La recomendacion pondera coste, tiempo, probabilidad directa y utilidad como reproductor intermedio.",
        ],
        howCalculated: {
          inheritedStats: probability.inheritedStats,
          actionCount: itemPlans.length * forcedSexOptions.length,
          statesExplored: itemPlans.length,
          simulations: 0,
          seed,
          depth: precise ? 2 : 1,
          elapsedMs: 0,
        },
      });
    }
  }

  return actions;
};

export const isDominatedBy = (candidate: BreedingAction, other: BreedingAction): boolean => {
  const noWorse =
    other.cost.metricCost <= candidate.cost.metricCost &&
    other.schedule.clockMinutes <= candidate.schedule.clockMinutes &&
    other.directTargetProbability >= candidate.directTargetProbability &&
    other.usefulBreederProbability >= candidate.usefulBreederProbability &&
    other.expectedImprovement >= candidate.expectedImprovement;

  const strictlyBetter =
    other.cost.metricCost < candidate.cost.metricCost ||
    other.schedule.clockMinutes < candidate.schedule.clockMinutes ||
    other.directTargetProbability > candidate.directTargetProbability ||
    other.usefulBreederProbability > candidate.usefulBreederProbability ||
    other.expectedImprovement > candidate.expectedImprovement;

  return noWorse && strictlyBetter;
};

export const splitDominatedActions = (
  actions: BreedingAction[],
): { pareto: BreedingAction[]; dominated: BreedingAction[] } => {
  const pareto: BreedingAction[] = [];
  const dominated: BreedingAction[] = [];

  for (const action of actions) {
    const isDominated = actions.some((other) => other.id !== action.id && isDominatedBy(action, other));
    if (isDominated) {
      dominated.push(action);
    } else {
      pareto.push(action);
    }
  }

  return { pareto, dominated };
};
