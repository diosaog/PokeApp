import type { BreedingItemId, EquippedItem, ParentSlot } from "@/domain/economy/types";
import { breedingItems } from "@/domain/economy/items";
import type { BreedingTarget, IvSpread, StatKey } from "@/domain/pokemon/types";
import { statKeys } from "@/domain/pokemon/types";

const powerItemByStat = new Map<StatKey, BreedingItemId>(
  breedingItems.flatMap((item) => (item.effect.type === "power" ? [[item.effect.stat, item.id]] : [])),
);

const needsStat = (target: BreedingTarget, stat: StatKey): boolean => target.ivs[stat].kind !== "any";

const usefulPowerItems = (
  ivs: IvSpread,
  parent: ParentSlot,
  target: BreedingTarget,
): EquippedItem[] =>
  statKeys.flatMap((stat) => {
    const itemId = powerItemByStat.get(stat);
    if (!itemId || !needsStat(target, stat)) {
      return [];
    }
    if (ivs[stat] < 28 && target.ivs[stat].kind !== "preferred") {
      return [];
    }
    return [{ parent, itemId }];
  });

const keyForPlan = (plan: EquippedItem[]): string =>
  plan
    .map((item) => `${item.parent}:${item.itemId}`)
    .sort()
    .join("|");

const addUniquePlan = (plans: EquippedItem[][], seen: Set<string>, plan: EquippedItem[]): void => {
  const key = keyForPlan(plan);
  if (!seen.has(key)) {
    seen.add(key);
    plans.push(plan);
  }
};

export const generateItemPlans = (
  parentAIvs: IvSpread,
  parentBIvs: IvSpread,
  target: BreedingTarget,
  precise: boolean,
): EquippedItem[][] => {
  const plans: EquippedItem[][] = [];
  const seen = new Set<string>();
  const powerA = usefulPowerItems(parentAIvs, "parentA", target);
  const powerB = usefulPowerItems(parentBIvs, "parentB", target);

  addUniquePlan(plans, seen, []);
  addUniquePlan(plans, seen, [{ parent: "parentA", itemId: "destinyKnot" }]);
  addUniquePlan(plans, seen, [{ parent: "parentB", itemId: "destinyKnot" }]);

  for (const item of [...powerA, ...powerB]) {
    addUniquePlan(plans, seen, [item]);
    addUniquePlan(plans, seen, [{ parent: item.parent === "parentA" ? "parentB" : "parentA", itemId: "destinyKnot" }, item]);
  }

  const pairLimit = precise ? 36 : 12;
  let pairsAdded = 0;
  for (const itemA of powerA) {
    for (const itemB of powerB) {
      if (pairsAdded >= pairLimit) {
        break;
      }
      if (itemA.itemId === itemB.itemId) {
        continue;
      }
      addUniquePlan(plans, seen, [itemA, itemB]);
      pairsAdded += 1;
    }
  }

  return plans;
};
