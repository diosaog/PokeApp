import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  PokemonSprite,
  SpriteGeneration,
  gameGeneration,
} from "./presentation";
import { writePrefs } from "../preferences";

// jsdom has no layout or image loading: a visible viewport, a media query
// answer and an Image that "downloads" at once, recording what was fetched.
let fetched: string[] = [];
let systemReduced = false;
beforeEach(() => {
  fetched = [];
  systemReduced = false;
  localStorage.clear();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(
        private callback: (entries: { isIntersecting: boolean }[]) => void,
      ) {}
      observe() {
        this.callback([{ isIntersecting: true }]);
      }
      disconnect() {}
    },
  );
  window.matchMedia = vi.fn(() => ({
    matches: systemReduced,
    addEventListener() {},
    removeEventListener() {},
  })) as never;
  vi.stubGlobal(
    "Image",
    class {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(value: string) {
        fetched.push(value);
        queueMicrotask(() => this.onload?.());
      }
    },
  );
});
afterEach(() => {
  cleanup();
  writePrefs({ motion: "full" });
  vi.unstubAllGlobals();
  localStorage.clear();
});

async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

it("a Gen6/7 game's Pokémon moves with its own battle model, shiny included", async () => {
  render(
    <>
      <SpriteGeneration value={gameGeneration("Y")}>
        <PokemonSprite species="Pokémon #25" animated />
      </SpriteGeneration>
      <SpriteGeneration value={gameGeneration("US")}>
        <PokemonSprite species="Pokémon #722" shiny animated />
      </SpriteGeneration>
    </>,
  );
  await settle();
  expect(screen.getByAltText("Pikachu")).toHaveAttribute(
    "src",
    "/visuals/animated/v2/25.gif",
  );
  expect(screen.getByAltText("Rowlet")).toHaveAttribute(
    "src",
    "/visuals/animated/v2/shiny/722.gif",
  );
  // Never the Black/White pixel clips inside a Gen6/7 game's art.
  expect(fetched.some((f) => f.includes("/animated/v1/"))).toBe(false);
});

it("only screens that ask for motion move; nothing else is downloaded", async () => {
  render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <PokemonSprite species="Pokémon #25" />
      <PokemonSprite species="Pokémon #6" />
    </SpriteGeneration>,
  );
  await settle();
  expect(screen.getByAltText("Pikachu")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/25.png",
  );
  expect(fetched).toEqual([]);
});

it("forms, unverified clips and a game's missing art stay on the correct still", async () => {
  render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <PokemonSprite species="Pokémon #6" form={1} animated />
      <PokemonSprite species="Pokémon #716" animated />
      <PokemonSprite species="Pokémon #666" animated />
    </SpriteGeneration>,
  );
  await settle();
  expect(screen.getByAltText(/Charizard/)).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/6-form-1.png",
  );
  // Xerneas' clip shows Active Mode and Vivillon's another pattern: excluded.
  expect(screen.getByAltText("Xerneas")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/716.png",
  );
  expect(screen.getByAltText("Vivillon")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/666.png",
  );
  expect(fetched).toEqual([]);
});

it("reduced motion, from the system or the app setting, keeps every sprite still", async () => {
  systemReduced = true;
  const { unmount } = render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <PokemonSprite species="Pokémon #25" animated />
    </SpriteGeneration>,
  );
  await settle();
  expect(screen.getByAltText("Pikachu")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/25.png",
  );
  unmount();
  systemReduced = false;
  writePrefs({ motion: "reduced" });
  render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <PokemonSprite species="Pokémon #25" animated />
    </SpriteGeneration>,
  );
  await settle();
  expect(screen.getByAltText("Pikachu")).toHaveAttribute(
    "src",
    "/visuals/v1/gen6/25.png",
  );
  expect(fetched).toEqual([]);
});

it("a screen without a game keeps the Black/White clips of its stills", async () => {
  render(<PokemonSprite species="Pokémon #635" animated />);
  await settle();
  expect(screen.getByAltText("Hydreigon")).toHaveAttribute(
    "src",
    "/visuals/animated/v1/635.gif",
  );
});

it("«Mi PC» never moves; an Entrenadores team moves, its boxes don't", async () => {
  const { Collection } = await import("../features/collection");
  const mon = (species: string, nickname: string) => ({
    species,
    nickname,
    level: 30,
    types: [],
    item: "",
    moves: [],
    is_shiny: false,
    ability: "",
    nature: "",
  });
  const slots = [
    { location: "Equipo · 1", pokemon: mon("Pokémon #25", "Equipo") },
    { location: "Caja 1 · 1", pokemon: mon("Pokémon #6", "Caja") },
  ];
  const { unmount } = render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <Collection slots={slots} />
    </SpriteGeneration>,
  );
  await settle();
  expect(fetched).toEqual([]);
  unmount();
  render(
    <SpriteGeneration value={gameGeneration("Y")}>
      <Collection slots={slots} animateTeam />
    </SpriteGeneration>,
  );
  await settle();
  expect(fetched).toEqual(["/visuals/animated/v2/25.gif"]);
});
