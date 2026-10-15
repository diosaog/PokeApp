import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { PokemonDetails } from "./pokemon-details";
import type { Model } from "../api/types";

const pokemon: Model<"PrivatePokemonRead"> = {
  species: "Pokémon #658",
  nickname: "",
  level: 42,
  types: ["Water", "Dark"],
  item: "Item #234",
  moves: [{ name: "Move #85", pp: 15 }],
  ability: "Ability #26",
  nature: "Nature #10",
  is_shiny: false,
  ivs: { hp: 31, atk: 30, defense: 29, spa: 28, spd: 27, spe: 26 },
  evs: null,
};
afterEach(cleanup);
it("localizes existing private details without altering the source object", () => {
  const source = JSON.stringify(pokemon);
  render(<PokemonDetails visibility="self" pokemon={pokemon} />);
  for (const text of [
    "Greninja",
    "Agua",
    "Siniestro",
    "Restos",
    "Levitación",
    "Miedosa",
    "At. Esp.",
  ])
    expect(screen.getByText(text)).toBeVisible();
  expect(screen.getByRole("button", { name: "Ver Rayo" })).toBeVisible();
  expect(document.body.textContent).not.toMatch(
    /#658|#234|#85|#26|#10|\bspa\b|\bdefense\b/,
  );
  expect(JSON.stringify(pokemon)).toBe(source);
});
it("public rendering never discovers private fields even on an overfull object", () => {
  render(<PokemonDetails visibility="public" pokemon={pokemon} />);
  expect(screen.getByRole("button", { name: "Ver Rayo" })).toBeVisible();
  for (const text of [
    "Habilidad",
    "Levitación",
    "Naturaleza",
    "Miedosa",
    "IVS",
    "EVS",
    "At. Esp.",
  ])
    expect(screen.queryByText(text)).not.toBeInTheDocument();
});
