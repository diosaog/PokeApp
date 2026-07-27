import { describe, expect, it } from "vitest";
import fc from "fast-check";

import { calculateAttemptCost } from "@/engine/economy/costs";
import { enumerateInheritancePatterns } from "@/engine/inheritance/probability";
import { simulateEgg } from "@/engine/simulation/simulateEgg";
import { createDefaultInventory } from "@/domain/economy/items";
import { statKeys } from "@/domain/pokemon/types";
import { diosesmonProfile } from "@/rules/diosesmon/profile";
import { budget, ivs } from "@/tests/unit/testUtils";

describe("propiedades del motor", () => {
  it("los costes y los inventarios nunca son negativos", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 10 }), fc.integer({ min: 0, max: 20_000 }), (owned, money) => {
        const inv = createDefaultInventory(500);
        inv.powerWeight.owned = owned;
        const result = calculateAttemptCost({
          economy: diosesmonProfile.economy,
          inventory: inv,
          budget: budget(money),
          items: [{ parent: "parentA", itemId: "powerWeight" }],
          forceSex: money % 2 === 0,
        });

        expect(result.breakdown.directCashCost).toBeGreaterThanOrEqual(0);
        expect(result.inventory.powerWeight.owned).toBeGreaterThanOrEqual(0);
      }),
    );
  });

  it("una accion sin objetos no consume objetos", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 20 }), (owned) => {
        const inv = createDefaultInventory(500);
        inv.powerWeight.owned = owned;
        const result = calculateAttemptCost({
          economy: diosesmonProfile.economy,
          inventory: inv,
          budget: budget(),
          items: [],
          forceSex: false,
        });

        expect(result.inventory.powerWeight.owned).toBe(owned);
        expect(result.breakdown.consumedItems).toHaveLength(0);
      }),
    );
  });

  it("una accion con n objetos consume exactamente n", () => {
    fc.assert(
      fc.property(fc.boolean(), (twoItems) => {
        const inv = createDefaultInventory(500);
        inv.powerWeight.owned = 1;
        inv.powerBand.owned = 1;
        const items = twoItems
          ? [
              { parent: "parentA" as const, itemId: "powerWeight" as const },
              { parent: "parentB" as const, itemId: "powerBand" as const },
            ]
          : [{ parent: "parentA" as const, itemId: "powerWeight" as const }];
        const result = calculateAttemptCost({
          economy: diosesmonProfile.economy,
          inventory: inv,
          budget: budget(),
          items,
          forceSex: false,
        });

        expect(result.breakdown.consumedItems).toHaveLength(items.length);
      }),
    );
  });

  it("un sexo forzado nunca produce otro sexo", () => {
    const species = {
      id: "eevee",
      names: { es: "Eevee", en: "Eevee" },
      forms: [],
      eggBaseSpeciesId: "eevee",
      eggGroups: ["field" as const],
      genderRatio: { male: 50, female: 50 },
      genderless: false,
      canBreed: true,
      abilities: [],
    };

    fc.assert(
      fc.property(fc.integer({ min: 1, max: 100_000 }), (seed) => {
        const egg = simulateEgg({
          parentAIvs: ivs(),
          parentBIvs: ivs(),
          items: [],
          inheritanceRules: diosesmonProfile.inheritance,
          offspringRules: diosesmonProfile.offspring,
          species,
          forcedSex: "female",
          seed,
        });

        expect(egg.sex).toBe("female");
      }),
    );
  });

  it("la suma de resultados agrupados mantiene la probabilidad", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 31 }), fc.integer({ min: 0, max: 31 }), (hpA, hpB) => {
        const result = enumerateInheritancePatterns(ivs({ hp: hpA }), ivs({ hp: hpB }), [], diosesmonProfile.inheritance);
        const total = result.patterns.reduce((sum, pattern) => sum + pattern.probability, 0);
        expect(total).toBeCloseTo(1, 10);
      }),
    );
  });

  it("todos los IV generados por simulacion estan en rango", () => {
    const species = {
      id: "eevee",
      names: { es: "Eevee", en: "Eevee" },
      forms: [],
      eggBaseSpeciesId: "eevee",
      eggGroups: ["field" as const],
      genderRatio: { male: 50, female: 50 },
      genderless: false,
      canBreed: true,
      abilities: [],
    };

    fc.assert(
      fc.property(fc.integer({ min: 1, max: 100_000 }), (seed) => {
        const egg = simulateEgg({
          parentAIvs: ivs({ hp: 31 }),
          parentBIvs: ivs({ speed: 31 }),
          items: [],
          inheritanceRules: diosesmonProfile.inheritance,
          offspringRules: diosesmonProfile.offspring,
          species,
          seed,
        });
        for (const stat of statKeys) {
          expect(egg.ivs[stat]).toBeGreaterThanOrEqual(0);
          expect(egg.ivs[stat]).toBeLessThanOrEqual(31);
        }
      }),
    );
  });
});
