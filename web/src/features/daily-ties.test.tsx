import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "../api/client";
import type { Model } from "../api/types";
import { DailyTieFields, tieReview } from "./daily-ties";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const review: Model<"RankingReview"> = {
  input_hash: "h",
  groups: [
    {
      division: "A",
      player_ids: ["p1", "p2"],
      position: 1,
      position_end: 2,
      wins: 2,
      adjusted_deaths: 0,
      consequences: ["points"],
    },
  ],
};
const name = (id: string) => ({ p1: "Lucía", p2: "Mario" })[id] ?? id;

it("two leagues name the division, keeping its letter inside a label", () => {
  render(<DailyTieFields review={review} name={name} />);
  expect(screen.getByText(/División A · posiciones 1–2/)).toBeInTheDocument();
  expect(screen.getByLabelText("Posición 1 · división A")).toBeInTheDocument();
  expect(
    screen.getByLabelText("Motivo del desempate · división A · posición 1"),
  ).toBeInTheDocument();
});

it("one league never mentions a division", () => {
  render(<DailyTieFields review={review} name={name} single />);
  expect(screen.getByText(/Liga · posiciones 1–2/)).toBeInTheDocument();
  expect(screen.getByLabelText("Posición 1 · liga")).toBeInTheDocument();
  expect(screen.queryByText(/[Dd]ivisión/)).not.toBeInTheDocument();
});

it("renders the last-place prize tie from a raw API 409 through the browser parser", async () => {
  const ranking = {
    ...review,
    input_hash: "a".repeat(64),
    groups: [
      {
        ...review.groups[0],
        position: 4,
        position_end: 5,
        consequences: ["single_league_prize"],
      },
    ],
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: { code: "RANKING_TIE_UNRESOLVED", ranking },
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
  );
  const client = new ApiClient("https://api.example");
  const error = await client
    .command("/close", { expected_results_revision: 1 }, "close-key")
    .catch((failure: unknown) => failure);
  expect(error).toBeInstanceOf(ApiError);
  const parsed = tieReview(error);
  expect(parsed).toEqual(ranking);
  render(<DailyTieFields review={parsed} name={name} single />);
  expect(screen.getByText(/Afecta a:/)).toHaveTextContent(
    "premio extra de Blindar o Robar Pokémon",
  );
  expect(screen.getByLabelText("Posición 4 · liga")).toBeRequired();
  expect(screen.getByLabelText("Posición 5 · liga")).toBeRequired();
});
