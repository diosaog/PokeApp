import type { ServerProfile } from "@/rules/types";

export const diosesmonProfile: ServerProfile = {
  id: "diosesmon-verification",
  name: "Diosesmon - reglas en verificacion",
  description:
    "Perfil inicial con costes confirmados y mecanicas de herencia todavia verificables.",
  economy: {
    breedingBaseCost: 2500,
    breedingDurationMinutes: 25,
    forcedSexCost: 5000,
    defaultItemPrice: 500,
    purchasesTakeTimeMinutes: 0,
  },
  time: {
    breedingSlots: 1,
    breedingDurationMinutes: 25,
    parentReuseMode: "immediate",
    parentCooldownMinutes: 0,
    cooldownStartsAt: "breeding_end",
  },
  inheritance: {
    defaultInheritedStats: 3,
    destinyKnotInheritedStats: 5,
    powerItemMode: "unconfirmed",
    nonInheritedIvMode: "uniform_0_31",
    allowTwoPowerItems: true,
    sameStatPowerConflict: "unconfirmed",
  },
  offspring: {
    speciesFollows: "mother",
    dittoCanBreedWithGenderless: true,
    dittoCanBreedWithDitto: false,
    forcedSexAvailable: true,
    forcedSexAllowedForGenderless: false,
  },
  notices: [
    {
      id: "costs",
      label: "Costes principales",
      status: "confirmed",
      details: "Crianza 2500 $, sexo 5000 $, objeto 500 $, duracion 25 minutos.",
    },
    {
      id: "inheritance-formula",
      label: "Formula exacta de herencia",
      status: "unconfirmed",
      details:
        "Falta confirmar distribucion de IV no heredados e interaccion entre Lazo Destino y objetos recios.",
    },
    {
      id: "reuse-cooldown",
      label: "Enfriamiento de progenitores",
      status: "user_configurable",
      details:
        "Se ha mencionado un posible enfriamiento de 60 minutos. El usuario debe confirmarlo.",
    },
    {
      id: "special-exceptions",
      label: "Excepciones de especies",
      status: "unconfirmed",
      details: "Las excepciones deben venir de datos declarativos, no de componentes visuales.",
    },
  ],
};
