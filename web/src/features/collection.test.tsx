import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Collection, collectionLocation } from "./collection";
import type { Model } from "../api/types";
const mon = {
  species: "Pokémon #635",
  nickname: "",
  level: 42,
  types: [],
  item: "",
  moves: [],
  is_shiny: false,
  ability: "",
  nature: "",
};
afterEach(cleanup);
it("renders six team slots and only one observed box without inventing empty capacity", () => {
  const slots: Model<"SlotRead">[] = [
    { location: "Equipo · 1", pokemon: mon },
    { location: "Caja 1 · 1", pokemon: { ...mon, nickname: "Primero" } },
    { location: "Caja 12 · 1", pokemon: { ...mon, nickname: "Último" } },
  ];
  const original = JSON.stringify(slots);
  render(<Collection slots={slots} />);
  expect(screen.getByText("1 / 2 cajas con Pokémon")).toBeVisible();
  expect(screen.getByRole("button", { name: /Primero/ })).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /Último/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Caja siguiente" }));
  expect(screen.getByRole("heading", { name: "Caja 12" })).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /Primero/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Caja siguiente" })).toBeDisabled();
  expect(JSON.stringify(slots)).toBe(original);
});
it("does not infer a box from malformed location or turn unknown source into a dead Pokémon", () => {
  expect(collectionLocation("missing")).toBeNull();
  expect(collectionLocation("Caja 8 · 7")).toEqual({ box: 8, slot: 7 });
});
