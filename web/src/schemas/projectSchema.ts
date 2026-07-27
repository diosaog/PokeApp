import { z } from "zod";

import { breedingItemIds } from "@/domain/economy/items";
import { statKeys } from "@/domain/pokemon/types";

const ivSchema = z.number().int().min(0).max(31);

const ivSpreadSchema = z.object({
  hp: ivSchema,
  attack: ivSchema,
  defense: ivSchema,
  specialAttack: ivSchema,
  specialDefense: ivSchema,
  speed: ivSchema,
});

const sexSchema = z.enum(["male", "female", "genderless", "unknown"]);

const constraintSchema = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("any") }),
  z.object({ kind: z.literal("exact31") }),
  z.object({ kind: z.literal("min"), value: ivSchema }),
  z.object({ kind: z.literal("range"), min: ivSchema, max: ivSchema }),
  z.object({ kind: z.literal("exact"), value: ivSchema }),
  z.object({ kind: z.literal("preferred"), value: ivSchema, weight: z.number().min(0).max(10) }),
]);

const targetIvsSchema = z.object(
  Object.fromEntries(statKeys.map((stat) => [stat, constraintSchema])),
);

const pokemonSchema = z.object({
  id: z.string().min(1),
  nickname: z.string().optional(),
  speciesId: z.string().min(1),
  formId: z.string().optional(),
  sex: sexSchema,
  ivs: ivSpreadSchema,
  natureId: z.string().optional(),
  abilityId: z.string().optional(),
  isHiddenAbility: z.boolean().optional(),
  canBreed: z.boolean(),
  availableAtMinute: z.number().int().min(0),
  protected: z.boolean(),
  notes: z.string().optional(),
});

const inventoryEntrySchema = z.object({
  owned: z.number().int().min(0),
  autoBuy: z.boolean(),
  price: z.number().min(0),
  enabled: z.boolean(),
});

const inventorySchema = z.object(
  Object.fromEntries(breedingItemIds.map((id) => [id, inventoryEntrySchema])),
);

const economySchema = z.object({
  breedingBaseCost: z.number().min(0),
  breedingDurationMinutes: z.number().min(0),
  forcedSexCost: z.number().min(0),
  defaultItemPrice: z.number().min(0),
  purchasesTakeTimeMinutes: z.number().min(0),
});

const timeSchema = z.object({
  breedingSlots: z.number().int().min(1),
  breedingDurationMinutes: z.number().min(0),
  parentReuseMode: z.enum(["immediate", "cooldown", "single_use"]),
  parentCooldownMinutes: z.number().min(0),
  cooldownStartsAt: z.enum(["breeding_start", "breeding_end"]),
});

export const projectSchema = z.object({
  schemaVersion: z.literal(1),
  exportedAt: z.string(),
  profileId: z.string(),
  budget: z.object({
    unlimited: z.boolean(),
    money: z.number().min(0),
    metric: z.enum(["cash", "replacement"]),
  }),
  economy: economySchema,
  time: timeSchema,
  inventory: inventorySchema,
  target: z.object({
    speciesId: z.string().min(1),
    ivs: targetIvsSchema,
    sex: z.union([sexSchema, z.literal("any")]),
    natureId: z.string().optional(),
    abilityId: z.string().optional(),
  }),
  pokemon: z.array(pokemonSchema),
  history: z.array(z.string()).optional(),
});

export type ProjectDocument = z.infer<typeof projectSchema>;

export const parseProjectDocument = (value: unknown): ProjectDocument => projectSchema.parse(value);
