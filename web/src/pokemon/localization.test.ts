import { describe, expect, it } from "vitest";
import catalog from "./catalog.es.json";
import { catalogId, pokemonName, pokemonTitle, statName } from "./localization";

describe("pinned Spanish presentation catalog", () => {
  it.each([
    [647, "Keldeo"],
    [718, "Zygarde"],
    [371, "Bagon"],
  ] as const)(
    "resolves the existing encoded server species label %s without changing nicknames",
    (id, name) => {
      const species = `Pok\u00c3\u00a9mon #${id}`;
      expect(pokemonName("species", species)).toBe(name);
      expect(catalogId("species", species)).toBe(id);
      expect(pokemonTitle({ species, nickname: species })).toBe(species);
    },
  );
  it("does not extract a species number from arbitrary names or invalid legacy labels", () => {
    for (const value of [
      "My Keldeo #647",
      "Pok\u00c3\u00a9mon #999999",
      "Pok\u00c3\u00a9mon #647 extra",
    ])
      expect(catalogId("species", value)).toBeNull();
  });
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
  it("localizes SM and USUM without extending beyond generation 7", () => {
    expect(pokemonName("species", 802)).toBe("Marshadow");
    expect(pokemonName("species", 808)).toBe("Especie no disponible");
    expect(pokemonName("move", 719)).toBe("Gigarrayo Fulminante");
    expect(pokemonName("item", 776, 7)).toBe("Normastal Z");
    expect(pokemonName("ability", 207)).toBe("Cola Surf");
    expect(pokemonName("species", 807)).toBe("Zeraora");
    expect(pokemonName("move", 728)).toBe("Estruendo Implacable");
    expect(pokemonName("ability", 233)).toBe("Fuerza Cerebral");
    expect(pokemonName("item", 923, 7)).toBe("Ultranecrostal Z");
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
