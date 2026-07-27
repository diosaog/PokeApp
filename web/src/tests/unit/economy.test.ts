import { describe, expect, it } from "vitest";

import { calculateAttemptCost } from "@/engine/economy/costs";
import { diosesmonProfile } from "@/rules/diosesmon/profile";
import { budget, inventory } from "@/tests/unit/testUtils";

describe("economia Diosesmon", () => {
  it("calcula costes confirmados sin forzar sexo", () => {
    const inv = inventory();

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [],
        forceSex: false,
      }).breakdown.directCashCost,
    ).toBe(2500);

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [{ parent: "parentA", itemId: "powerWeight" }],
        forceSex: false,
      }).breakdown.directCashCost,
    ).toBe(3000);

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [
          { parent: "parentA", itemId: "powerWeight" },
          { parent: "parentB", itemId: "powerBand" },
        ],
        forceSex: false,
      }).breakdown.directCashCost,
    ).toBe(3500);
  });

  it("calcula costes confirmados forzando sexo", () => {
    const inv = inventory();

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [],
        forceSex: true,
      }).breakdown.directCashCost,
    ).toBe(7500);

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [{ parent: "parentA", itemId: "powerWeight" }],
        forceSex: true,
      }).breakdown.directCashCost,
    ).toBe(8000);

    expect(
      calculateAttemptCost({
        economy: diosesmonProfile.economy,
        inventory: inv,
        budget: budget(),
        items: [
          { parent: "parentA", itemId: "powerWeight" },
          { parent: "parentB", itemId: "powerBand" },
        ],
        forceSex: true,
      }).breakdown.directCashCost,
    ).toBe(8500);
  });

  it("consume objetos existentes sin desembolso extra", () => {
    const inv = inventory();
    inv.powerWeight.owned = 1;

    const result = calculateAttemptCost({
      economy: diosesmonProfile.economy,
      inventory: inv,
      budget: budget(),
      items: [{ parent: "parentA", itemId: "powerWeight" }],
      forceSex: false,
    });

    expect(result.ok).toBe(true);
    expect(result.inventory.powerWeight.owned).toBe(0);
    expect(result.breakdown.directCashCost).toBe(2500);
    expect(result.breakdown.replacementCost).toBe(3000);
  });

  it("consume dos objetos de inventarios distintos", () => {
    const inv = inventory();
    inv.powerWeight.owned = 1;
    inv.powerBand.owned = 1;

    const result = calculateAttemptCost({
      economy: diosesmonProfile.economy,
      inventory: inv,
      budget: budget(),
      items: [
        { parent: "parentA", itemId: "powerWeight" },
        { parent: "parentB", itemId: "powerBand" },
      ],
      forceSex: false,
    });

    expect(result.inventory.powerWeight.owned).toBe(0);
    expect(result.inventory.powerBand.owned).toBe(0);
  });

  it("rechaza consumir un objeto inexistente sin compras automaticas", () => {
    const inv = inventory();
    inv.powerWeight.autoBuy = false;

    const result = calculateAttemptCost({
      economy: diosesmonProfile.economy,
      inventory: inv,
      budget: budget(),
      items: [{ parent: "parentA", itemId: "powerWeight" }],
      forceSex: false,
    });

    expect(result.ok).toBe(false);
    expect(result.reasons.join(" ")).toContain("compras automaticas");
  });

  it("compra un objeto si esta permitido", () => {
    const inv = inventory();

    const result = calculateAttemptCost({
      economy: diosesmonProfile.economy,
      inventory: inv,
      budget: budget(),
      items: [{ parent: "parentA", itemId: "powerWeight" }],
      forceSex: false,
    });

    expect(result.ok).toBe(true);
    expect(result.breakdown.purchasedItemsCost).toBe(500);
  });

  it("no permite que el presupuesto quede negativo", () => {
    const result = calculateAttemptCost({
      economy: diosesmonProfile.economy,
      inventory: inventory(),
      budget: budget(100),
      items: [],
      forceSex: false,
    });

    expect(result.ok).toBe(false);
    expect(result.reasons.join(" ")).toContain("presupuesto");
  });
});
