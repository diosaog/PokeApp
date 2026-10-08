import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { GameProgress } from "./progress";
import type { Model } from "../api/types";

afterEach(cleanup);
const observed = (champion: boolean | null = null): Model<"ProgressRead"> => ({
  state: "observed",
  game: "B2",
  badges_count: 8,
  primary_region: "unova",
  observed_at: "2026-10-08T12:00:00Z",
  regions: [{ region: "unova", earned_badges: [1, 2, 3, 4, 5, 6, 7, 8] }],
  champion_defeated: champion,
});

it("unknown has no fabricated zero, empty badge set or incomplete Champion", () => {
  render(<GameProgress progress={{ state: "unknown" }} />);
  expect(screen.getByText(/Progreso no observado/)).toBeVisible();
  expect(screen.queryByText(/0 medallas/)).not.toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.queryByText(/aún no derrotado/)).not.toBeInTheDocument();
});
it.each([true, false, null])(
  "eight badges preserve Champion state %s",
  (champion) => {
    render(<GameProgress progress={observed(champion)} />);
    expect(screen.getByText("8 medallas observadas")).toBeVisible();
    expect(
      screen.getByText(
        champion === true
          ? /Juego completado/
          : champion === false
            ? /aún no derrotado/
            : /sin observar/,
      ),
    ).toBeVisible();
  },
);
it("zero is observed and sparse regional identities are not filled in", () => {
  const value = {
    ...observed(),
    badges_count: 2,
    primary_region: "johto" as const,
    regions: [
      { region: "johto" as const, earned_badges: [] },
      { region: "kanto" as const, earned_badges: [2, 7] },
    ],
  };
  const view = render(<GameProgress progress={value} />);
  expect(
    screen.getByRole("img", { name: "Medalla 1 de Johto: no conseguida" }),
  ).toBeVisible();
  expect(
    screen.getByRole("img", { name: "Medalla 2 de Kanto: conseguida" }),
  ).toBeVisible();
  expect(
    screen.getByRole("img", { name: "Medalla 1 de Kanto: no conseguida" }),
  ).toBeVisible();
  view.rerender(
    <GameProgress
      progress={{
        ...observed(false),
        badges_count: 0,
        regions: [{ region: "unova", earned_badges: [] }],
      }}
    />,
  );
  expect(screen.getByText("0 medallas observadas")).toBeVisible();
});
it("a count without regional evidence does not invent individual badges", () => {
  render(<GameProgress progress={{ ...observed(), regions: null }} />);
  expect(screen.getByText("8 medallas observadas")).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
