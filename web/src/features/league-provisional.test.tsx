import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ProvisionalPoints } from "./core";
vi.mock("../state", () => ({}));
afterEach(cleanup);

const row = (extra: Record<string, unknown> = {}) => ({
  season_player_id: "p",
  trainer_id: "t",
  display_name: "Entrenador",
  status: "active",
  total_points: "0",
  points_source_matchday_id: null,
  coin_balance: "44",
  dead_count: 2,
  dead_count_source: "observed_current_save" as const,
  dead_count_observed_at: null,
  ...extra,
});

it("shows preseason deaths and sanctions apart from the official total", () => {
  render(
    <ProvisionalPoints
      row={row({
        provisional_matchday_number: 1,
        provisional_dead_count: 2,
        provisional_points_reduction: "1.5",
        provisional_points: "-1.9",
      })}
    />,
  );
  expect(
    screen.getByText(
      "Provisional: -1.9 (2 muertes, sanciones −1.5) · se aplica al cerrar J1",
    ),
  ).toBeInTheDocument();
});

it("stays hidden when nothing would change or the database has no figures", () => {
  const { container, rerender } = render(<ProvisionalPoints row={row()} />);
  expect(container).toBeEmptyDOMElement();
  rerender(
    <ProvisionalPoints
      row={row({
        total_points: "3.0",
        provisional_matchday_number: 2,
        provisional_dead_count: 0,
        provisional_points_reduction: "0",
        provisional_points: "3.0",
      })}
    />,
  );
  expect(container).toBeEmptyDOMElement();
});
