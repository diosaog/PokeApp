import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  PokemonSprite,
  TrainerPhoto,
  TypeBadge,
  ItemIcon,
  MovePopover,
} from "./presentation";
import { catalogId } from "./localization";
afterEach(cleanup);
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
