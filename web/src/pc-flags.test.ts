import { expect, it, vi } from "vitest";
import { withSeasonFlags } from "./state";
import type { Model } from "./api/types";

vi.mock("./launcher", () => ({
  insideLauncher: () => false,
  listenForLauncherEvents: () => () => {},
  listenForLauncherSession: () => () => {},
  renewFromLauncher: () => {},
  requestLauncherSession: () => {},
  tellLauncherLogout: () => {},
}));

type Slot = Model<"PCRead">["pokemon"][number];
const ivs = (n: number) => ({
  hp: n,
  atk: 31,
  defense: 31,
  spa: 31,
  spd: 31,
  spe: 31,
});
const slot = (
  location: string,
  species: string,
  iv: number,
  extra: Partial<Slot["pokemon"]> = {},
): Slot => ({
  location,
  pokemon: {
    species,
    nickname: "",
    item: "",
    is_shiny: false,
    ability: "",
    nature: "",
    gender: "M",
    ivs: ivs(iv),
    status_flags: [],
    ...extra,
  },
});
const pc = (pokemon: Slot[]): Model<"PCRead"> => ({
  save: null,
  status: "ready",
  pokemon,
});

it("2026-11-18: a newer personal save keeps the season's ROBADO/BLINDADO/REVIVIDO labels", () => {
  const season = pc([
    slot("Equipo · 6", "Excadrill", 20, { status_flags: ["revivido"] }),
    slot("Caja 1 · 1", "Drilbur", 5, { status_flags: ["blindado"] }),
    slot("Caja 1 · 2", "Magikarp", 31),
    // Two identical twins: ambiguous, never labelled by guess.
    slot("Caja 2 · 1", "Ditto", 31, { status_flags: ["robado"] }),
    slot("Caja 2 · 2", "Ditto", 31),
  ]);
  const personal = pc([
    slot("Caja 3 · 4", "Excadrill", 20), // moved box
    slot("Equipo · 1", "Excadrill", 5), // evolved
    slot("Caja 1 · 2", "Magikarp", 31),
    slot("Caja 2 · 1", "Ditto", 31),
    slot("Caja 2 · 2", "Ditto", 31),
  ]);
  const merged = withSeasonFlags(personal, season);
  expect(merged.pokemon.map((s) => s.pokemon.status_flags)).toEqual([
    ["revivido"],
    ["blindado"],
    [],
    [],
    [],
  ]);
  // Nothing else of the personal save changes.
  expect(merged.pokemon.map((s) => s.location)).toEqual(
    personal.pokemon.map((s) => s.location),
  );
  // No labels in the season save: the same object comes back.
  expect(withSeasonFlags(personal, pc([slot("Equipo · 1", "Ditto", 1)]))).toBe(
    personal,
  );
});
