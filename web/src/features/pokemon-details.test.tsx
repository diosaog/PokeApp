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
  expect(screen.getByText("Rayo")).toBeVisible();
  expect(document.body.textContent).not.toMatch(
    /#658|#234|#85|#26|#10|\bspa\b|\bdefense\b/,
  );
  expect(JSON.stringify(pokemon)).toBe(source);
});
it("public rendering never discovers private fields even on an overfull object", () => {
  render(<PokemonDetails visibility="public" pokemon={pokemon} />);
  expect(screen.getByText("Rayo")).toBeVisible();
  for (const text of [
    "Habilidad",
    "Levitación",
    "Naturaleza",
    "Miedosa",
    "IVs",
    "EVs",
    "At. Esp.",
  ])
    expect(screen.queryByText(text)).not.toBeInTheDocument();
});

it("IV bars preserve exact zero/max and omit EVs, invalid or missing IV is not zero", () => {
  render(
    <PokemonDetails
      visibility="self"
      pokemon={{
        ...pokemon,
        ivs: { hp: 0, atk: 31, defense: -1, spa: 32, spd: 17, spe: 24 },
        evs: { hp: 252, atk: 0, defense: 0, spa: 0, spd: 0, spe: 0 },
      }}
    />,
  );
  expect(screen.getByRole("meter", { name: "PS" })).toHaveAttribute(
    "aria-valuenow",
    "0",
  );
  expect(screen.getByRole("meter", { name: "Ataque" })).toHaveAttribute(
    "aria-valuenow",
    "31",
  );
  expect(
    screen.queryByRole("meter", { name: "Defensa" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("252")).not.toBeInTheDocument();
  expect(screen.queryByText(/EVs/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Ver Rayo/ }),
  ).not.toBeInTheDocument();
});

it.each([6, 7] as const)(
  "resolves actual modern held item IDs with Gen %i context",
  (generation) => {
    const { rerender } = render(
      <PokemonDetails
        visibility="self"
        pokemon={{ ...pokemon, item: "Item #158", item_generation: generation }}
      />,
    );
    expect(screen.getByText("Baya Zidra")).toBeVisible();
    rerender(
      <PokemonDetails
        visibility="self"
        pokemon={{ ...pokemon, item: "Item #217", item_generation: generation }}
      />,
    );
    expect(screen.getByText("Garra Rápida")).toBeVisible();
    rerender(
      <PokemonDetails
        visibility="self"
        pokemon={{ ...pokemon, item: "", item_generation: generation }}
      />,
    );
    expect(screen.getByText("Sin objeto")).toBeVisible();
    expect(screen.getByText("Rayo")).toBeVisible();
    expect(screen.getByRole("meter", { name: "PS" })).toHaveAttribute(
      "aria-valuenow",
      "31",
    );
  },
);

it("does not guess an ambiguous item when source game is missing", () => {
  const { rerender } = render(
    <PokemonDetails
      visibility="self"
      pokemon={{ ...pokemon, species: "Clefable", item: "Item #158" }}
    />,
  );
  expect(
    screen.getByText("Objeto sin identificar (falta el juego)"),
  ).toBeVisible();
  rerender(
    <PokemonDetails
      visibility="self"
      pokemon={{ ...pokemon, item: "Item #158", item_generation: 3 }}
    />,
  );
  expect(screen.queryByText("Baya Zidra")).not.toBeInTheDocument();
});
