import type { PokemonInstance, SpeciesData } from "@/domain/pokemon/types";

export interface OffspringSpeciesResult {
  speciesId: string | null;
  motherId: string | null;
  fatherId: string | null;
  certainty: "confirmed" | "uncertain";
  explanation: string;
  warnings: string[];
}

const isDittoSpecies = (species: SpeciesData): boolean =>
  species.id === "ditto" || species.eggGroups.includes("ditto");

export const getOffspringSpecies = (
  parentA: PokemonInstance,
  parentB: PokemonInstance,
  speciesById: ReadonlyMap<string, SpeciesData>,
): OffspringSpeciesResult => {
  const speciesA = speciesById.get(parentA.speciesId);
  const speciesB = speciesById.get(parentB.speciesId);

  if (!speciesA || !speciesB) {
    return {
      speciesId: null,
      motherId: null,
      fatherId: null,
      certainty: "uncertain",
      explanation: "Faltan datos de especie.",
      warnings: ["No se puede determinar la descendencia sin datos de especie."],
    };
  }

  const aDitto = isDittoSpecies(speciesA);
  const bDitto = isDittoSpecies(speciesB);

  if (aDitto && bDitto) {
    return {
      speciesId: null,
      motherId: null,
      fatherId: null,
      certainty: "confirmed",
      explanation: "Ditto con Ditto no produce una descendencia valida en este perfil.",
      warnings: ["Crianza invalida."],
    };
  }

  if (aDitto || bDitto) {
    const nonDittoParent = aDitto ? parentB : parentA;
    const nonDittoSpecies = aDitto ? speciesB : speciesA;
    return {
      speciesId: nonDittoSpecies.eggBaseSpeciesId,
      motherId: nonDittoParent.id,
      fatherId: aDitto ? parentA.id : parentB.id,
      certainty: "confirmed",
      explanation: `Con Ditto, nace la linea base de ${nonDittoSpecies.names.es}.`,
      warnings: [],
    };
  }

  if (parentA.sex === "female" && parentB.sex === "male") {
    return {
      speciesId: speciesA.eggBaseSpeciesId,
      motherId: parentA.id,
      fatherId: parentB.id,
      certainty: "confirmed",
      explanation: `La madre pertenece a la linea de ${speciesA.names.es}.`,
      warnings: [],
    };
  }

  if (parentB.sex === "female" && parentA.sex === "male") {
    return {
      speciesId: speciesB.eggBaseSpeciesId,
      motherId: parentB.id,
      fatherId: parentA.id,
      certainty: "confirmed",
      explanation: `La madre pertenece a la linea de ${speciesB.names.es}.`,
      warnings: [],
    };
  }

  return {
    speciesId: null,
    motherId: null,
    fatherId: null,
    certainty: "uncertain",
    explanation: "No se puede fijar madre ni especie con sexos desconocidos o incompatibles.",
    warnings: ["Introduce el sexo real para determinar que especie nace."],
  };
};
