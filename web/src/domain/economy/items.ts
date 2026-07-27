import type { BreedingItemDefinition, BreedingItemId, InventoryState } from "@/domain/economy/types";

export const breedingItems: BreedingItemDefinition[] = [
  {
    id: "powerWeight",
    names: { es: "Pesa Recia", en: "Power Weight" },
    effect: { type: "power", stat: "hp" },
    consumable: true,
  },
  {
    id: "powerBracer",
    names: { es: "Brazal Recio", en: "Power Bracer" },
    effect: { type: "power", stat: "attack" },
    consumable: true,
  },
  {
    id: "powerBelt",
    names: { es: "Cinto Recio", en: "Power Belt" },
    effect: { type: "power", stat: "defense" },
    consumable: true,
  },
  {
    id: "powerLens",
    names: { es: "Lente Recia", en: "Power Lens" },
    effect: { type: "power", stat: "specialAttack" },
    consumable: true,
  },
  {
    id: "powerBand",
    names: { es: "Banda Recia", en: "Power Band" },
    effect: { type: "power", stat: "specialDefense" },
    consumable: true,
  },
  {
    id: "powerAnklet",
    names: { es: "Franja Recia", en: "Power Anklet" },
    effect: { type: "power", stat: "speed" },
    consumable: true,
  },
  {
    id: "destinyKnot",
    names: { es: "Lazo Destino", en: "Destiny Knot" },
    effect: { type: "destinyKnot" },
    consumable: true,
  },
  {
    id: "everstone",
    names: { es: "Piedra Eterna", en: "Everstone" },
    effect: { type: "nature" },
    consumable: true,
  },
  {
    id: "mirrorHerb",
    names: { es: "Hierba Copia", en: "Mirror Herb" },
    effect: { type: "ability" },
    consumable: true,
  },
];

export const breedingItemIds = breedingItems.map((item) => item.id) as BreedingItemId[];

export const itemById = new Map<BreedingItemId, BreedingItemDefinition>(
  breedingItems.map((item) => [item.id, item]),
);

export const createDefaultInventory = (price: number): InventoryState =>
  Object.fromEntries(
    breedingItems.map((item) => [
      item.id,
      {
        owned: 0,
        autoBuy: true,
        price,
        enabled: true,
      },
    ]),
  ) as InventoryState;
