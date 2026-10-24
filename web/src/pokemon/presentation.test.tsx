import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  PokemonSprite,
  TrainerPhoto,
  TypeBadge,
  ItemIcon,
  MovePopover,
  PokemonStatusFlags,
} from "./presentation";
import { catalogId } from "./localization";
afterEach(cleanup);
it("shows an uploaded portrait and safely falls back when its signed URL expires", () => {
  render(<TrainerPhoto name="Nuevo" url="https://example.invalid/portrait" />);
  const image = screen.getByAltText("Retrato de Nuevo");
  expect(image).toHaveAttribute("src", "https://example.invalid/portrait");
  fireEvent.error(image);
  expect(screen.getByLabelText("Sin foto")).toBeVisible();
});
it("renders compatible public state flags as compact labels", () => {
  render(<PokemonStatusFlags flags={["blindado", "revivido", "blindado"]} />);
  expect(screen.getByText("BLINDADO")).toHaveClass("blindado");
  expect(screen.getByText("REVIVIDO")).toHaveClass("revivido");
  expect(screen.queryAllByText("BLINDADO")).toHaveLength(1);
});
it("uses local sprites, canonical categories and honest unresolved fallbacks", () => {
  render(
    <>
      <PokemonSprite species="Pokémon #635" />
      <PokemonSprite species="Unknown Species" />
      <TypeBadge type="Electric" />
      <ItemIcon name="Leftovers" />
      <TrainerPhoto name="Anto" />
    </>,
  );
  expect(screen.getByAltText("Hydreigon")).toHaveAttribute(
    "src",
    "/visuals/v1/pokemon/635.png",
  );
  expect(screen.getByLabelText("Imagen no disponible")).toBeVisible();
  expect(screen.getByText("Eléctrico")).toBeVisible();
  expect(screen.getByAltText("Retrato de Anto")).toHaveAttribute(
    "loading",
    "lazy",
  );
  fireEvent.error(screen.getByAltText("Hydreigon"));
  expect(screen.getAllByLabelText("Imagen no disponible")).toHaveLength(2);
  expect(catalogId("item", "Item #200")).toBeNull();
});
it("loads the explicitly versioned local reference only on move interaction", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        85: {
          type: "Electric",
          category: "Special",
          power: 90,
          accuracy: 100,
          description:
            "Potente ataque eléctrico que puede paralizar al objetivo.",
        },
      }),
    ),
  );
  render(<MovePopover name="Move #85" />);
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Ver Rayo" }));
  expect(
    await screen.findByText(
      "Potente ataque eléctrico que puede paralizar al objetivo.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Referencia Pokémon X/Y")).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledWith("/visuals/v1/moves-xy.json");
  fetcher.mockRestore();
});

it("opening a second move dismisses the first; Escape returns focus", () => {
  render(
    <>
      <MovePopover name="Rayo" />
      <MovePopover name="Placaje" />
    </>,
  );
  const first = screen.getByRole("button", { name: "Ver Rayo" });
  const second = screen.getByRole("button", { name: "Ver Placaje" });
  fireEvent.click(first);
  expect(first).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(second);
  expect(first).toHaveAttribute("aria-expanded", "false");
  expect(second).toHaveAttribute("aria-expanded", "true");
  fireEvent.keyDown(window, { key: "Escape" });
  expect(second).toHaveAttribute("aria-expanded", "false");
  expect(second).toHaveFocus();
});
