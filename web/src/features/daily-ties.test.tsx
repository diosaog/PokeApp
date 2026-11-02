import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "../api/client";
import type { Model } from "../api/types";
import { DailyTieFields, readTieResolution, tieReview } from "./daily-ties";

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
    vi.fn().mockResolvedValue(
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

it("requires actual 1v1 outcomes with time and evidence for the new global prize tie", () => {
  const current: Model<"RankingReview"> = {
    ...review,
    ranking_rule: "wins_segment_deaths_v2",
    groups: [
      {
        ...review.groups[0],
        segment_deaths: 5,
        adjusted_deaths: 10,
        consequences: ["matchday_prize"],
      },
    ],
  };
  render(
    <form data-testid="form">
      <DailyTieFields review={current} name={name} single />
    </form>,
  );
  expect(
    screen.getByRole("heading", { name: "Registrar desempates 1v1" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/muertes de progresión/)).toHaveTextContent(
    "5 muertes de progresión",
  );
  expect(screen.queryByText(/10 muertes/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Posición 1 · liga"), {
    target: { value: "p1" },
  });
  fireEvent.change(screen.getByLabelText("Posición 2 · liga"), {
    target: { value: "p2" },
  });
  fireEvent.change(screen.getByLabelText(/Motivo del desempate/), {
    target: { value: "Resultado del desempate" },
  });
  const winner = screen.getByLabelText("Ganador 1v1 · Lucía / Mario");
  expect(winner).toBeRequired();
  fireEvent.change(winner, { target: { value: "p1" } });
  fireEvent.change(screen.getByLabelText("Fecha del 1v1 · Lucía / Mario"), {
    target: { value: "2026-11-01T15:30" },
  });
  fireEvent.change(screen.getByLabelText("Evidencia del 1v1 · Lucía / Mario"), {
    target: { value: "Repetición del combate 42" },
  });
  expect(
    readTieResolution(
      new FormData(screen.getByTestId("form") as HTMLFormElement),
      current,
    ),
  ).toEqual({
    input_hash: "h",
    orders: [
      {
        player_ids: ["p1", "p2"],
        reason: "Resultado del desempate",
        battles: [
          {
            player_a_id: "p1",
            player_b_id: "p2",
            winner_id: "p1",
            played_at: new Date("2026-11-01T15:30").toISOString(),
            evidence: "Repetición del combate 42",
          },
        ],
      },
    ],
  });
});

it("keeps the actual-death criterion and required prize consequence through the browser parser", async () => {
  const current = {
    ...review,
    input_hash: "b".repeat(64),
    ranking_rule: "wins_segment_deaths_v2",
    groups: [
      {
        ...review.groups[0],
        segment_deaths: 3,
        consequences: ["matchday_prize"],
      },
    ],
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "RANKING_TIE_UNRESOLVED", ranking: current },
        }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
  const error = await new ApiClient("https://api.example")
    .command("/close", {}, "key")
    .catch((failure: unknown) => failure);
  expect(tieReview(error)).toEqual(current);
});

it("accepts the nullable added fields on historical API tie reviews", async () => {
  const historical = {
    ...review,
    input_hash: "c".repeat(64),
    ranking_rule: null,
    groups: [{ ...review.groups[0], segment_deaths: null }],
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: { code: "RANKING_TIE_UNRESOLVED", ranking: historical },
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
  );
  const error = await new ApiClient("https://api.example")
    .command("/close", {}, "key")
    .catch((failure: unknown) => failure);
  expect(tieReview(error)).toEqual(historical);
  render(<DailyTieFields review={tieReview(error)} name={name} />);
  expect(screen.queryByLabelText(/Ganador 1v1/)).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Registrar decisión externa" }),
  ).toBeInTheDocument();
});
