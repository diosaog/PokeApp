import type { StatKey } from "@/domain/pokemon/types";

export interface EconomyConfig {
  breedingBaseCost: number;
  breedingDurationMinutes: number;
  forcedSexCost: number;
  defaultItemPrice: number;
  purchasesTakeTimeMinutes: number;
}

export type CostMetric = "cash" | "replacement";

export interface BudgetConfig {
  unlimited: boolean;
  money: number;
  metric: CostMetric;
}

export type BreedingItemId =
  | "powerWeight"
  | "powerBracer"
  | "powerBelt"
  | "powerLens"
  | "powerBand"
  | "powerAnklet"
  | "destinyKnot"
  | "everstone"
  | "mirrorHerb";

export type BreedingItemEffect =
  | { type: "power"; stat: StatKey }
  | { type: "destinyKnot" }
  | { type: "nature" }
  | { type: "ability" };

export interface BreedingItemDefinition {
  id: BreedingItemId;
  names: {
    es: string;
    en: string;
  };
  effect: BreedingItemEffect;
  consumable: boolean;
}

export interface InventoryEntry {
  owned: number;
  autoBuy: boolean;
  price: number;
  enabled: boolean;
}

export type InventoryState = Record<BreedingItemId, InventoryEntry>;

export type ParentSlot = "parentA" | "parentB";

export interface EquippedItem {
  parent: ParentSlot;
  itemId: BreedingItemId;
}

export interface CostBreakdown {
  breedingCost: number;
  purchasedItemsCost: number;
  consumedItemsValue: number;
  forcedSexCost: number;
  directCashCost: number;
  replacementCost: number;
  metricCost: number;
  purchasedItems: BreedingItemId[];
  consumedItems: BreedingItemId[];
}

export interface InventoryConsumptionResult {
  ok: boolean;
  inventory: InventoryState;
  breakdown: CostBreakdown;
  reasons: string[];
}
