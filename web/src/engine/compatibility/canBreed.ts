import type { PokemonInstance, SpeciesData } from "@/domain/pokemon/types";
import type { OffspringRules } from "@/rules/types";

export interface CanBreedResult {
  valid: boolean;
  certainty: "confirmed" | "uncertain";
  sharedEggGroups: string[];
  reasons: string[];
  warnings: string[];
}

const invalid = (reason: string): CanBreedResult => ({
  valid: false,
  certainty: "confirmed",
  sharedEggGroups: [],
  reasons: [reason],
  warnings: [],
});

const isDitto = (species: SpeciesData): boolean => species.id === "ditto" || species.eggGroups.includes("ditto");

const hasNoEggGroup = (species: SpeciesData): boolean => species.eggGroups.includes("noEggs");

export const canBreed = (
  parentA: PokemonInstance,
  parentB: PokemonInstance,
  speciesById: ReadonlyMap<string, SpeciesData>,
  rules: OffspringRules,
  nowMinute: number,
): CanBreedResult => {
  if (parentA.id === parentB.id) {
    return invalid("No se puede cruzar un Pokemon consigo mismo.");
  }

  if (parentA.protected || parentB.protected) {
    return invalid("Un Pokemon protegido no se utiliza en recomendaciones.");
  }

  if (!parentA.canBreed || !parentB.canBreed) {
    return invalid("Un progenitor marcado como esteril no puede criar.");
  }

  if (parentA.availableAtMinute > nowMinute || parentB.availableAtMinute > nowMinute) {
    return invalid("Un progenitor en enfriamiento no esta disponible todavia.");
  }

  const speciesA = speciesById.get(parentA.speciesId);
  const speciesB = speciesById.get(parentB.speciesId);

  if (!speciesA || !speciesB) {
    return invalid("Faltan datos de especie para uno de los progenitores.");
  }

  if (!speciesA.canBreed || !speciesB.canBreed || hasNoEggGroup(speciesA) || hasNoEggGroup(speciesB)) {
    return invalid("Una de las especies pertenece a un grupo no criable.");
  }

  const aDitto = isDitto(speciesA);
  const bDitto = isDitto(speciesB);

  if (aDitto && bDitto && !rules.dittoCanBreedWithDitto) {
    return invalid("Ditto con Ditto es invalido.");
  }

  if (aDitto || bDitto) {
    const nonDittoSpecies = aDitto ? speciesB : speciesA;
    if (nonDittoSpecies.genderless && !rules.dittoCanBreedWithGenderless) {
      return invalid("El perfil no permite Ditto con especies sin genero.");
    }
    return {
      valid: true,
      certainty: "confirmed",
      sharedEggGroups: ["ditto"],
      reasons: ["Ditto permite cruzar con el progenitor no Ditto segun el perfil."],
      warnings: [],
    };
  }

  const sharedEggGroups = speciesA.eggGroups.filter((group) => speciesB.eggGroups.includes(group));

  if (sharedEggGroups.length === 0) {
    return invalid("No comparten ningun grupo huevo.");
  }

  if (speciesA.genderless || speciesB.genderless) {
    return invalid("Una especie sin genero normalmente necesita Ditto.");
  }

  const sexes = new Set([parentA.sex, parentB.sex]);
  if (sexes.has("male") && sexes.has("female")) {
    return {
      valid: true,
      certainty: "confirmed",
      sharedEggGroups,
      reasons: ["Comparten grupo huevo y los sexos son compatibles."],
      warnings: [],
    };
  }

  if (sexes.has("unknown")) {
    return {
      valid: true,
      certainty: "uncertain",
      sharedEggGroups,
      reasons: ["Comparten grupo huevo."],
      warnings: ["Hay sexo desconocido: confirma el sexo real para asegurar madre, padre y especie."],
    };
  }

  return invalid("Sin Ditto, normalmente se necesita un macho y una hembra.");
};
