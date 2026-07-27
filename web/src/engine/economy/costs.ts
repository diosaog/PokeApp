import type {
  BudgetConfig,
  BreedingItemId,
  CostBreakdown,
  EquippedItem,
  InventoryConsumptionResult,
  InventoryState,
} from "@/domain/economy/types";
import { itemById } from "@/domain/economy/items";
import type { EconomyConfig } from "@/domain/economy/types";

export interface AttemptCostInput {
  economy: EconomyConfig;
  inventory: InventoryState;
  budget: BudgetConfig;
  items: EquippedItem[];
  forceSex: boolean;
}

export const emptyCostBreakdown = (): CostBreakdown => ({
  breedingCost: 0,
  purchasedItemsCost: 0,
  consumedItemsValue: 0,
  forcedSexCost: 0,
  directCashCost: 0,
  replacementCost: 0,
  metricCost: 0,
  purchasedItems: [],
  consumedItems: [],
});

const cloneInventory = (inventory: InventoryState): InventoryState =>
  Object.fromEntries(
    Object.entries(inventory).map(([id, entry]) => [
      id,
      {
        owned: entry.owned,
        autoBuy: entry.autoBuy,
        price: entry.price,
        enabled: entry.enabled,
      },
    ]),
  ) as InventoryState;

export const validateEquippedItems = (items: EquippedItem[]): string[] => {
  const reasons: string[] = [];
  const slots = new Set<string>();

  for (const item of items) {
    if (slots.has(item.parent)) {
      reasons.push("Un progenitor no puede llevar mas de un objeto.");
    }
    slots.add(item.parent);
    if (!itemById.has(item.itemId)) {
      reasons.push(`Objeto desconocido: ${item.itemId}.`);
    }
  }

  return reasons;
};

export const calculateAttemptCost = ({
  economy,
  inventory,
  budget,
  items,
  forceSex,
}: AttemptCostInput): InventoryConsumptionResult => {
  const reasons = validateEquippedItems(items);
  const nextInventory = cloneInventory(inventory);
  const purchasedItems: BreedingItemId[] = [];
  const consumedItems: BreedingItemId[] = [];
  let purchasedItemsCost = 0;
  let consumedItemsValue = 0;

  for (const equipped of items) {
    const itemDefinition = itemById.get(equipped.itemId);
    const inventoryEntry = nextInventory[equipped.itemId];

    if (!itemDefinition || !inventoryEntry) {
      reasons.push(`Objeto desconocido: ${equipped.itemId}.`);
      continue;
    }

    if (!inventoryEntry.enabled) {
      reasons.push(`El objeto ${itemDefinition.names.es} esta deshabilitado.`);
      continue;
    }

    consumedItemsValue += inventoryEntry.price;
    consumedItems.push(equipped.itemId);

    if (inventoryEntry.owned > 0) {
      inventoryEntry.owned -= 1;
      continue;
    }

    if (!inventoryEntry.autoBuy) {
      reasons.push(`No hay ${itemDefinition.names.es} y las compras automaticas estan deshabilitadas.`);
      continue;
    }

    purchasedItemsCost += inventoryEntry.price;
    purchasedItems.push(equipped.itemId);
  }

  const forcedSexCost = forceSex ? economy.forcedSexCost : 0;
  const breedingCost = economy.breedingBaseCost;
  const directCashCost = breedingCost + forcedSexCost + purchasedItemsCost;
  const replacementCost = breedingCost + forcedSexCost + consumedItemsValue;
  const metricCost = budget.metric === "cash" ? directCashCost : replacementCost;

  if (!budget.unlimited && directCashCost > budget.money) {
    reasons.push("El presupuesto disponible no cubre el desembolso directo.");
  }

  const breakdown: CostBreakdown = {
    breedingCost,
    purchasedItemsCost,
    consumedItemsValue,
    forcedSexCost,
    directCashCost,
    replacementCost,
    metricCost,
    purchasedItems,
    consumedItems,
  };

  return {
    ok: reasons.length === 0,
    inventory: nextInventory,
    breakdown,
    reasons,
  };
};

export const applyPaidAttempt = (
  money: number,
  unlimited: boolean,
  result: InventoryConsumptionResult,
): { money: number; inventory: InventoryState } => ({
  money: unlimited ? money : money - result.breakdown.directCashCost,
  inventory: result.inventory,
});
