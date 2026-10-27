import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { Model } from "../api/types";
import { DailyTieFields } from "./daily-ties";

afterEach(cleanup);

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
