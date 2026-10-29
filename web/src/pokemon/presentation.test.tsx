import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  PokemonSprite,
  TrainerPhoto,
  TypeBadge,
  ItemIcon,
  MovePopover,
  PokemonStatusFlags,
  SpriteGeneration,
  gameGeneration,
} from "./presentation";
import { catalogId } from "./localization";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
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
  expect(screen.getAllByLabelText("Imagen no disponible")).toHaveLength(1);
  expect(
    screen.getByRole("img", {
      name: "No se pudo cargar la imagen de Hydreigon",
    }),
  ).toBeVisible();
  expect(catalogId("item", "Item #200")).toBeNull();
});
it.each([
  ["Pok\u00c3\u00a9mon #647", null, "647", "Keldeo"],
  ["Pok\u00c3\u00a9mon #718", 0, "718", "Zygarde"],
  ["Pok\u00c3\u00a9mon #371", null, "371", "Bagon"],
  ["Pikachu", 0, "25", "Pikachu"],
  ["#722", 0, "722", "Rowlet"],
  ["Zeraora", 0, "807", "Zeraora"],
  ["Keldeo", 1, "647-form-1", "Keldeo"],
  ["Zygarde", 4, "718-form-4", "Zygarde"],
  ["Raichu", 1, "26-form-1", "Raichu"],
  ["Deoxys", 3, "386-form-3", "Deoxys"],
  ["Charizard", 2, "6-form-2", "Charizard"],
] as const)("resolves sprite %s form %s", (species, form, file, label) => {
  render(<PokemonSprite species={species} form={form} animated />);
  expect(screen.getByAltText(label)).toHaveAttribute(
    "src",
    `/visuals/v1/pokemon/${file}.png`,
  );
});
it("never substitutes base art for an unknown form or masks a load failure as unknown data", () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  const view = render(<PokemonSprite species="Keldeo" form={255} />);
  expect(
    screen.getByLabelText("Imagen de esta forma no disponible"),
  ).toBeVisible();
  expect(warn).not.toHaveBeenCalled();
  view.rerender(<PokemonSprite species="Keldeo" form={1} />);
  fireEvent.error(screen.getByAltText("Keldeo"));
  expect(
    screen.getByRole("img", { name: "No se pudo cargar la imagen de Keldeo" }),
  ).toBeVisible();
  expect(warn).toHaveBeenCalledWith(
    "pokemon_sprite_load_failed",
    "/visuals/v1/pokemon/647-form-1.png",
  );
  view.rerender(<PokemonSprite species="Keldeo" form={0} />);
  expect(screen.getByAltText("Keldeo")).toHaveAttribute(
    "src",
    "/visuals/v1/pokemon/647.png",
  );
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

it("a save's own generation decides the art, never another generation's", () => {
  render(
    <>
      <SpriteGeneration value={gameGeneration("Y")}>
        <PokemonSprite species="Pokémon #25" animated />
        <PokemonSprite species="Pokémon #6" form={1} />
      </SpriteGeneration>
      <SpriteGeneration value={gameGeneration("UM")}>
        <PokemonSprite species="Pokémon #722" />
        <PokemonSprite species="Pokémon #807" />
      </SpriteGeneration>
      <PokemonSprite species="Pokémon #635" />
    </>,
  );
  const [pikachu] = screen.getAllByRole("img", { name: /Pikachu/ });
  // X/Y render, static: the Black/White animation is never mixed in.
  expect(pikachu).toHaveAttribute("src", "/visuals/v1/gen6/25.png");
  expect(screen.getByAltText(/Charizard/)).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/6-form-1.png",
  );
  expect(screen.getByAltText(/Rowlet/)).toHaveAttribute(
    "src",
    "/visuals/v1/gen7/722.png",
  );
  // No Ultra Sun/Moon render for Zeraora: its own species art, not another
  // generation's design.
  expect(screen.getByAltText(/Zeraora/)).toHaveAttribute(
    "src",
    "/visuals/v1/pokemon/807.png",
  );
  // Without a known game the established collection stays.
  expect(screen.getByAltText("Hydreigon")).toHaveAttribute(
    "src",
    "/visuals/v1/pokemon/635.png",
  );
  expect(gameGeneration("B2")).toBeNull();
});
