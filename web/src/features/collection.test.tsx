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
  expect(screen.getByRole("button", { name: "Caja siguiente" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Caja siguiente" }));
  expect(screen.getByRole("heading", { name: "Caja 1" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Caja anterior" }));
  expect(screen.getByRole("heading", { name: "Caja 12" })).toBeVisible();
  expect(JSON.stringify(slots)).toBe(original);
});
it("wraps left from the first box and disables cycling for one box", () => {
  const slots: Model<"SlotRead">[] = [
    { location: "Caja 1 · 1", pokemon: mon },
    {
      location: "Caja 4 · 1",
      pokemon: {
        ...mon,
        nickname: "Cuatro",
        status_flags: ["blindado", "revivido"],
      },
    },
  ];
  const view = render(<Collection slots={slots} />);
  fireEvent.click(screen.getByRole("button", { name: "Caja anterior" }));
  expect(screen.getByRole("heading", { name: "Caja 4" })).toBeVisible();
  expect(screen.getByText("BLINDADO")).toBeVisible();
  expect(screen.getByText("REVIVIDO")).toBeVisible();
  view.unmount();
  render(<Collection slots={[slots[0]]} />);
  expect(screen.getByRole("button", { name: "Caja anterior" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Caja siguiente" })).toBeDisabled();
});
it("does not infer a box from malformed location or turn unknown source into a dead Pokémon", () => {
  expect(collectionLocation("missing")).toBeNull();
  expect(collectionLocation("Caja 8 · 7")).toEqual({ box: 8, slot: 7 });
});
it("the own team shows the gender its save stores, never a guessed one", () => {
  const slots: Model<"SlotRead">[] = [
    { location: "Equipo · 1", pokemon: { ...mon, gender: "M" } },
    { location: "Equipo · 2", pokemon: { ...mon, gender: "F" } },
    { location: "Equipo · 3", pokemon: { ...mon, gender: "N" } },
    { location: "Equipo · 4", pokemon: { ...mon, gender: null } },
  ];
  render(<Collection slots={slots} />);
  expect(screen.getAllByRole("img", { name: "Macho" })).toHaveLength(1);
  expect(screen.getAllByRole("img", { name: "Hembra" })).toHaveLength(1);
  cleanup();
  // A public view has no gender at all.
  render(<Collection slots={slots} visibility="public" />);
  expect(
    screen.queryByRole("img", { name: /Macho|Hembra/ }),
  ).not.toBeInTheDocument();
});
