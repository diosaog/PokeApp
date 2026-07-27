import { describe, expect, it } from "vitest";

import { splitDominatedActions } from "@/engine/optimizer/evaluate";
import { parseProjectDocument } from "@/schemas/projectSchema";
import { createInitialHistoryStateForTests, sessionReducerForTests } from "@/state/sessionStore";
import { action, pokemon } from "@/tests/unit/testUtils";

describe("optimizador y estado", () => {
  it("el optimizador separa acciones dominadas", () => {
    const dominated = action({
      id: "dominated",
      metricCost: 5000,
      minutes: 30,
      directTargetProbability: 0.1,
      usefulBreederProbability: 0.2,
      expectedImprovement: 1,
    });
    const better = action({
      id: "better",
      metricCost: 4000,
      minutes: 25,
      directTargetProbability: 0.2,
      usefulBreederProbability: 0.3,
      expectedImprovement: 2,
    });

    const result = splitDominatedActions([dominated, better]);
    expect(result.dominated.map((item) => item.id)).toEqual(["dominated"]);
    expect(result.pareto.map((item) => item.id)).toEqual(["better"]);
  });

  it("la importacion rechaza archivos invalidos", () => {
    expect(() => parseProjectDocument({ schemaVersion: 1, pokemon: "no" })).toThrow();
  });

  it("deshacer restaura dinero, objetos y Pokemon", () => {
    let historyState = createInitialHistoryStateForTests();
    historyState = sessionReducerForTests(historyState, {
      type: "set-inventory-entry",
      itemId: "powerWeight",
      entry: { owned: 1, autoBuy: false, price: 500, enabled: true },
    });
    historyState = sessionReducerForTests(historyState, {
      type: "add-pokemon",
      pokemon: pokemon({ id: "a", speciesId: "eevee", sex: "female" }),
    });
    historyState = sessionReducerForTests(historyState, {
      type: "add-pokemon",
      pokemon: pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
    });

    const beforeRecord = historyState.present;
    historyState = sessionReducerForTests(historyState, {
      type: "record-egg",
      action: {
        ...action({
          id: "breed",
          metricCost: 3000,
          minutes: 25,
          directTargetProbability: 0.2,
          usefulBreederProbability: 0.5,
          expectedImprovement: 2,
        }),
        items: [{ parent: "parentA", itemId: "powerWeight" }],
      },
      egg: pokemon({ id: "egg", speciesId: "eevee", sex: "female" }),
    });

    expect(historyState.present.pokemon).toHaveLength(3);
    expect(historyState.present.inventory.powerWeight.owned).toBe(0);
    expect(historyState.present.budget.money).toBe(beforeRecord.budget.money - 2500);

    historyState = sessionReducerForTests(historyState, { type: "undo" });

    expect(historyState.present.pokemon).toHaveLength(beforeRecord.pokemon.length);
    expect(historyState.present.inventory.powerWeight.owned).toBe(beforeRecord.inventory.powerWeight.owned);
    expect(historyState.present.budget.money).toBe(beforeRecord.budget.money);
  });
});
