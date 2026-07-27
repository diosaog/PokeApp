import type { EquippedItem } from "@/domain/economy/types";
import { itemById } from "@/domain/economy/items";
import type { IvConstraint, IvSpread, StatKey } from "@/domain/pokemon/types";
import { statKeys } from "@/domain/pokemon/types";
import type { InheritanceRules } from "@/rules/types";

export interface InheritancePattern {
  probability: number;
  inherited: Partial<Record<StatKey, { parent: "parentA" | "parentB"; value: number }>>;
}

export interface EggProbabilitySummary {
  directTargetProbability: number;
  usefulBreederProbability: number;
  expectedImprovement: number;
  inheritedStats: number;
  warnings: string[];
}

const combinations = <T,>(values: readonly T[], count: number): T[][] => {
  if (count <= 0) {
    return [[]];
  }
  if (count > values.length) {
    return [];
  }

  const result: T[][] = [];
  const walk = (start: number, chosen: T[]): void => {
    if (chosen.length === count) {
      result.push([...chosen]);
      return;
    }

    for (let index = start; index < values.length; index += 1) {
      const value = values[index];
      if (value !== undefined) {
        chosen.push(value);
        walk(index + 1, chosen);
        chosen.pop();
      }
    }
  };

  walk(0, []);
  return result;
};

const cartesianParents = (stats: readonly StatKey[]): Array<Record<StatKey, "parentA" | "parentB">> => {
  const assignments: Array<Record<StatKey, "parentA" | "parentB">> = [];
  const walk = (index: number, current: Partial<Record<StatKey, "parentA" | "parentB">>): void => {
    const stat = stats[index];
    if (stat === undefined) {
      assignments.push(current as Record<StatKey, "parentA" | "parentB">);
      return;
    }

    walk(index + 1, { ...current, [stat]: "parentA" });
    walk(index + 1, { ...current, [stat]: "parentB" });
  };

  walk(0, {});
  return assignments;
};

export const getInheritedStatCount = (items: EquippedItem[], rules: InheritanceRules): number =>
  items.some((item) => item.itemId === "destinyKnot")
    ? rules.destinyKnotInheritedStats
    : rules.defaultInheritedStats;

const getForcedStats = (items: EquippedItem[]): Array<{ stat: StatKey; parent: "parentA" | "parentB" }> =>
  items.flatMap((equipped) => {
    const definition = itemById.get(equipped.itemId);
    if (definition?.effect.type !== "power") {
      return [];
    }
    return [{ stat: definition.effect.stat, parent: equipped.parent }];
  });

export const enumerateInheritancePatterns = (
  parentAIvs: IvSpread,
  parentBIvs: IvSpread,
  items: EquippedItem[],
  rules: InheritanceRules,
): { patterns: InheritancePattern[]; warnings: string[]; inheritedStats: number } => {
  const inheritedStats = getInheritedStatCount(items, rules);
  const warnings: string[] = [];
  const forcedStats = getForcedStats(items);
  const duplicatedForcedStats = new Set<StatKey>();

  for (const forced of forcedStats) {
    if (forcedStats.filter((candidate) => candidate.stat === forced.stat).length > 1) {
      duplicatedForcedStats.add(forced.stat);
    }
  }

  if (rules.powerItemMode === "unconfirmed" && forcedStats.length > 0) {
    warnings.push(
      "La interaccion exacta de objetos recios esta sin confirmar; se calcula como estadistica garantizada y contada.",
    );
  }

  if (duplicatedForcedStats.size > 0) {
    warnings.push("Hay conflicto de objetos recios sobre la misma estadistica; el perfil no esta confirmado.");
  }

  const uniqueForcedStats = Array.from(new Set(forcedStats.map((forced) => forced.stat)));
  const remainingCount =
    rules.powerItemMode === "guarantee_then_fill"
      ? inheritedStats
      : Math.max(0, inheritedStats - uniqueForcedStats.length);
  const availableStats = statKeys.filter((stat) => !uniqueForcedStats.includes(stat));
  const statSets = combinations(availableStats, Math.min(remainingCount, availableStats.length));
  const patterns: InheritancePattern[] = [];

  for (const set of statSets) {
    const inheritedSet = [...uniqueForcedStats, ...set].slice(0, statKeys.length);
    const randomStats = inheritedSet.filter((stat) => !uniqueForcedStats.includes(stat));
    const assignments = cartesianParents(randomStats);
    const setProbability = statSets.length > 0 ? 1 / statSets.length : 1;
    const assignmentProbability = assignments.length > 0 ? 1 / assignments.length : 1;

    for (const assignment of assignments) {
      const inherited: Partial<Record<StatKey, { parent: "parentA" | "parentB"; value: number }>> = {};

      for (const forcedStat of forcedStats) {
        const value = forcedStat.parent === "parentA" ? parentAIvs[forcedStat.stat] : parentBIvs[forcedStat.stat];
        inherited[forcedStat.stat] = { parent: forcedStat.parent, value };
      }

      for (const stat of randomStats) {
        const parent = assignment[stat] ?? "parentA";
        const value = parent === "parentA" ? parentAIvs[stat] : parentBIvs[stat];
        inherited[stat] = { parent, value };
      }

      patterns.push({
        inherited,
        probability: setProbability * assignmentProbability,
      });
    }
  }

  return { patterns, warnings, inheritedStats };
};

export const ivSatisfiesConstraint = (value: number, constraint: IvConstraint): boolean => {
  switch (constraint.kind) {
    case "any":
      return true;
    case "exact31":
      return value === 31;
    case "min":
      return value >= constraint.value;
    case "range":
      return value >= constraint.min && value <= constraint.max;
    case "exact":
      return value === constraint.value;
    case "preferred":
      return true;
  }
};

const randomIvProbability = (constraint: IvConstraint): number => {
  switch (constraint.kind) {
    case "any":
    case "preferred":
      return 1;
    case "exact31":
      return 1 / 32;
    case "min": {
      const valid = Math.max(0, 32 - Math.max(0, constraint.value));
      return valid / 32;
    }
    case "range": {
      const min = Math.max(0, constraint.min);
      const max = Math.min(31, constraint.max);
      return max < min ? 0 : (max - min + 1) / 32;
    }
    case "exact":
      return constraint.value >= 0 && constraint.value <= 31 ? 1 / 32 : 0;
  }
};

const statPotential = (parentAIvs: IvSpread, parentBIvs: IvSpread, constraint: IvConstraint, stat: StatKey): number => {
  const values = [parentAIvs[stat], parentBIvs[stat]];
  if (constraint.kind === "any") {
    return 0;
  }
  if (constraint.kind === "preferred") {
    return Math.max(...values) >= constraint.value ? constraint.weight : 0;
  }
  return values.some((value) => ivSatisfiesConstraint(value, constraint)) ? 1 : 0;
};

export const summarizeEggProbability = (
  parentAIvs: IvSpread,
  parentBIvs: IvSpread,
  targetIvs: Record<StatKey, IvConstraint>,
  items: EquippedItem[],
  rules: InheritanceRules,
): EggProbabilitySummary => {
  const { patterns, warnings, inheritedStats } = enumerateInheritancePatterns(parentAIvs, parentBIvs, items, rules);
  let directTargetProbability = 0;
  let usefulBreederProbability = 0;
  let expectedImprovement = 0;

  for (const pattern of patterns) {
    let targetProbability = 1;
    let usefulProbability = 1;
    let inheritedUsefulStats = 0;

    for (const stat of statKeys) {
      const constraint = targetIvs[stat];
      const inherited = pattern.inherited[stat];
      if (inherited) {
        const satisfies = ivSatisfiesConstraint(inherited.value, constraint);
        targetProbability *= satisfies ? 1 : 0;
        usefulProbability *= satisfies || constraint.kind === "any" || constraint.kind === "preferred" ? 1 : 0.5;
        if (satisfies && constraint.kind !== "any") {
          inheritedUsefulStats += 1;
        }
        continue;
      }

      targetProbability *= randomIvProbability(constraint);
      usefulProbability *= constraint.kind === "any" ? 1 : Math.max(randomIvProbability(constraint), 1 / 8);
    }

    directTargetProbability += pattern.probability * targetProbability;
    usefulBreederProbability += pattern.probability * usefulProbability;
    expectedImprovement += pattern.probability * inheritedUsefulStats;
  }

  const maxPotential = statKeys.reduce(
    (total, stat) => total + statPotential(parentAIvs, parentBIvs, targetIvs[stat], stat),
    0,
  );

  return {
    directTargetProbability,
    usefulBreederProbability,
    expectedImprovement: Math.max(expectedImprovement, maxPotential * 0.3),
    inheritedStats,
    warnings,
  };
};
