import { describe, expect, it } from "vitest";

import { speciesById } from "@/data/species";
import { canBreed } from "@/engine/compatibility/canBreed";
import { getOffspringSpecies } from "@/engine/offspring/getOffspringSpecies";
import { getSexDistribution } from "@/engine/inheritance/sex";
import { diosesmonProfile } from "@/rules/diosesmon/profile";
import { pokemon } from "@/tests/unit/testUtils";

describe("compatibilidad y descendencia", () => {
  it("Ditto con Ditto es invalido", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "ditto", sex: "genderless" }),
      pokemon({ id: "b", speciesId: "ditto", sex: "genderless" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(false);
  });

  it("dos Pokemon sin grupo compatible son invalidos", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "eevee", sex: "female" }),
      pokemon({ id: "b", speciesId: "lapras", sex: "male" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(false);
  });

  it("dos Pokemon compatibles por grupo compartido son validos", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "eevee", sex: "female" }),
      pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(true);
    expect(result.sharedEggGroups).toContain("field");
  });

  it("un Pokemon protegido no se utiliza", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "eevee", sex: "female", protectedPokemon: true }),
      pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(false);
  });

  it("un Pokemon esteril no se utiliza", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "eevee", sex: "female", canBreed: false }),
      pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(false);
  });

  it("un progenitor en enfriamiento no se usa antes de tiempo", () => {
    const result = canBreed(
      pokemon({ id: "a", speciesId: "eevee", sex: "female", availableAtMinute: 60 }),
      pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
      speciesById,
      diosesmonProfile.offspring,
      0,
    );

    expect(result.valid).toBe(false);
  });

  it("la especie de la cria sigue la madre sin Ditto", () => {
    const result = getOffspringSpecies(
      pokemon({ id: "a", speciesId: "eevee", sex: "female" }),
      pokemon({ id: "b", speciesId: "rattata", sex: "male" }),
      speciesById,
    );

    expect(result.speciesId).toBe("eevee");
    expect(result.motherId).toBe("a");
  });

  it("forzar sexo produce siempre el sexo seleccionado", () => {
    const species = speciesById.get("eevee");
    expect(species).toBeDefined();
    if (!species) {
      return;
    }

    const result = getSexDistribution(species, "female", "female", diosesmonProfile.offspring);
    expect(result.distribution).toEqual([{ sex: "female", probability: 1 }]);
  });

  it("no fuerza sexo en una especie sin genero", () => {
    const species = speciesById.get("magnemite");
    expect(species).toBeDefined();
    if (!species) {
      return;
    }

    const result = getSexDistribution(species, "male", "male", diosesmonProfile.offspring);
    expect(result.distribution).toEqual([{ sex: "genderless", probability: 1 }]);
    expect(result.warnings.join(" ")).toContain("sin genero");
  });
});
