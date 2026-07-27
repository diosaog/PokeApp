import { describe, expect, it } from "vitest";

import { enumerateInheritancePatterns, getInheritedStatCount, summarizeEggProbability } from "@/engine/inheritance/probability";
import { simulateEgg } from "@/engine/simulation/simulateEgg";
import { statKeys } from "@/domain/pokemon/types";
import { diosesmonProfile } from "@/rules/diosesmon/profile";
import { ivs } from "@/tests/unit/testUtils";

describe("herencia y probabilidades", () => {
  it("las probabilidades de patrones suman 1", () => {
    const result = enumerateInheritancePatterns(ivs({ hp: 31 }), ivs({ attack: 31 }), [], diosesmonProfile.inheritance);
    const total = result.patterns.reduce((sum, pattern) => sum + pattern.probability, 0);
    expect(total).toBeCloseTo(1, 10);
  });

  it("todos los IV simulados estan entre 0 y 31", () => {
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

    for (let seed = 1; seed <= 50; seed += 1) {
      const egg = simulateEgg({
        parentAIvs: ivs({ hp: 31, defense: 31 }),
        parentBIvs: ivs({ attack: 31, speed: 31 }),
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
    }
  });

  it("un objeto recio produce el IV esperado segun el perfil configurado", () => {
    const rules = { ...diosesmonProfile.inheritance, powerItemMode: "guarantee_and_counted" as const };
    const result = enumerateInheritancePatterns(
      ivs({ hp: 31 }),
      ivs({ hp: 0 }),
      [{ parent: "parentA", itemId: "powerWeight" }],
      rules,
    );

    expect(result.patterns.every((pattern) => pattern.inherited.hp?.value === 31)).toBe(true);
  });

  it("Lazo Destino utiliza la cantidad configurada de estadisticas", () => {
    expect(getInheritedStatCount([{ parent: "parentA", itemId: "destinyKnot" }], diosesmonProfile.inheritance)).toBe(5);
  });

  it("Lazo Destino con objeto recio respeta el modo configurado", () => {
    const rules = { ...diosesmonProfile.inheritance, powerItemMode: "guarantee_and_counted" as const };
    const result = enumerateInheritancePatterns(
      ivs({ hp: 31 }),
      ivs({ speed: 31 }),
      [
        { parent: "parentA", itemId: "destinyKnot" },
        { parent: "parentB", itemId: "powerAnklet" },
      ],
      rules,
    );

    expect(result.inheritedStats).toBe(5);
    expect(result.patterns.every((pattern) => pattern.inherited.speed?.value === 31)).toBe(true);
  });

  it("calcula probabilidad directa para un objetivo", () => {
    const summary = summarizeEggProbability(
      ivs({ hp: 31, defense: 31 }),
      ivs({ specialAttack: 31, specialDefense: 31, speed: 31 }),
      {
        hp: { kind: "exact31" },
        attack: { kind: "any" },
        defense: { kind: "exact31" },
        specialAttack: { kind: "exact31" },
        specialDefense: { kind: "exact31" },
        speed: { kind: "exact31" },
      },
      [{ parent: "parentA", itemId: "destinyKnot" }],
      diosesmonProfile.inheritance,
    );

    expect(summary.directTargetProbability).toBeGreaterThan(0);
    expect(summary.directTargetProbability).toBeLessThanOrEqual(1);
  });
});
