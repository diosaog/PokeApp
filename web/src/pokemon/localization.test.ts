import { describe, expect, it } from "vitest";
import catalog from "./catalog.es.json";
import { pokemonName, pokemonTitle, statName } from "./localization";

describe("pinned Spanish presentation catalog", () => {
  it.each([
    ["species", "#635", "Hydreigon"],
    ["species", "Pokémon #658", "Greninja"],
    ["species", "species 700", "Sylveon"],
    ["species", "Nidoran♀", "Nidoran♀"],
    ["species", "Nidoran♂", "Nidoran♂"],
    ["move", "move 85", "Rayo"],
    ["move", "Thunderbolt", "Rayo"],
    ["move", "dark-pulse", "Pulso Umbrío"],
    ["move", "Move #560", "Plancha Voladora"],
    ["ability", "ability 26", "Levitación"],
    ["ability", "Levitate", "Levitación"],
    ["ability", "Inner Focus", "Fuerza Mental"],
    ["ability", "CompoundEyes", "Ojo Compuesto"],
    ["item", "Leftovers", "Restos"],
    ["item", "Item #234", "Restos"],
    ["type", "Electric", "Eléctrico"],
    ["type", "Fairy", "Hada"],
    ["nature", "Nature #0", "Fuerte"],
    ["nature", "Timid", "Miedosa"],
    ["nature", "Nature #10", "Miedosa"],
  ] as const)("resolves %s / %s", (category, input, output) => {
    expect(pokemonName(category, input)).toBe(output);
  });
  it("fails closed on ambiguous item IDs instead of guessing Gen3 vs Gen4+", () => {
    expect(pokemonName("item", "Item #200")).toBe(
      "Objeto sin identificar (falta el juego)",
    );
    expect(pokemonName("item", 200, 3)).toBe("Restos");
    expect(pokemonName("item", 200, 5)).toBe("Baya Chilan");
    expect(pokemonName("item", 234, 6)).toBe("Restos");
  });
  it("preserves neutral/custom names and nicknames, with safe missing-key fallback", () => {
    expect(pokemonName("species", "Unown-B")).toBe("Unown-B");
    expect(pokemonName("item", "Blindar Pokémon")).toBe("Blindar Pokémon");
    expect(pokemonTitle({ species: "#635", nickname: "Thunderbolt" })).toBe(
      "Thunderbolt",
    );
    expect(pokemonName("move", "Move #999999")).toBe(
      "Movimiento no disponible",
    );
    expect(pokemonName("ability", undefined)).toBe("Habilidad no disponible");
    expect(pokemonName("species", "private_species_id")).toBe(
      "Especie no disponible",
    );
    expect(pokemonName("species", "#0")).toBe("Especie no disponible");
    expect(pokemonName("nature", -1)).toBe("Naturaleza no disponible");
    expect(statName("spa")).toBe("At. Esp.");
    expect(statName("private_field")).toBe("Característica");
  });
  it("keeps resource indexing and Unicode intact, with no invented flavor text", () => {
    for (const table of Object.values(catalog.categories)) {
      expect(table.en.length).toBe(table.es.length);
      expect(JSON.stringify(table)).not.toMatch(/\\u0000|�/);
    }
    expect(Object.keys(catalog.resources)).toHaveLength(14);
    expect(catalog.categories.item3.es[200]).toBe("Restos");
    // Current projections have no version context or description field. Neither
    // modern text nor a legacy cache with cross-version fallback is inserted.
    expect(catalog.descriptions).toBe("unavailable");
  });
});
