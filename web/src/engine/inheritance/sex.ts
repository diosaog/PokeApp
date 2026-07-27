import type { PokemonSex, SpeciesData, TargetSex } from "@/domain/pokemon/types";
import type { OffspringRules } from "@/rules/types";

export interface SexDistributionEntry {
  sex: PokemonSex;
  probability: number;
}

export const getSexDistribution = (
  species: SpeciesData,
  targetSex: TargetSex,
  forcedSex: PokemonSex | undefined,
  rules: OffspringRules,
): { distribution: SexDistributionEntry[]; warnings: string[] } => {
  if (species.genderless || species.genderRatio === null) {
    if (forcedSex && forcedSex !== "genderless") {
      return {
        distribution: [{ sex: "genderless", probability: 1 }],
        warnings: ["No se puede forzar sexo en una especie sin genero."],
      };
    }
    return { distribution: [{ sex: "genderless", probability: 1 }], warnings: [] };
  }

  if (forcedSex && forcedSex !== "unknown" && forcedSex !== "genderless") {
    if (!rules.forcedSexAvailable) {
      return {
        distribution: [
          { sex: "male", probability: species.genderRatio.male / 100 },
          { sex: "female", probability: species.genderRatio.female / 100 },
        ],
        warnings: ["El perfil no confirma que se pueda forzar sexo."],
      };
    }

    return { distribution: [{ sex: forcedSex, probability: 1 }], warnings: [] };
  }

  if (targetSex !== "any" && targetSex !== "genderless" && targetSex !== "unknown") {
    return {
      distribution: [
        { sex: "male", probability: species.genderRatio.male / 100 },
        { sex: "female", probability: species.genderRatio.female / 100 },
      ],
      warnings: [],
    };
  }

  return {
    distribution: [
      { sex: "male", probability: species.genderRatio.male / 100 },
      { sex: "female", probability: species.genderRatio.female / 100 },
    ],
    warnings: [],
  };
};
