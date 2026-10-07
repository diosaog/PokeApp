import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { InitialAssignment } from "./initial-assignment";
import { ChampionshipReview } from "./championship";

const mocks = vi.hoisted(() => ({
  data: {} as Record<string, unknown>,
  error: null as Error | null,
  uncertain: true,
  retry: vi.fn(),
  refetch: vi.fn(),
  hold: vi.fn(),
  release: vi.fn(),
}));
vi.mock("../state", () => ({
  useApp: () => ({
    season: "season",
    me: { is_admin: true },
    holdAdminNavigation: mocks.hold,
  }),
  useRead: () => ({
    data: mocks.data,
    error: mocks.error,
    isPending: false,
    isFetching: false,
    refetch: mocks.refetch,
  }),
}));
vi.mock("../ui", async (original) => ({
  ...(await original<typeof import("../ui")>()),
  useCommand: () => ({
    pending: false,
    uncertain: mocks.uncertain,
    error: null,
    success: false,
    retry: mocks.retry,
  }),
}));
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.hold.mockReturnValue(mocks.release);
  mocks.uncertain = true;
  mocks.error = null;
  mocks.data = {
    state: "assigned",
    players: [],
    blocking_reasons: [],
    ready: false,
  };
});

it("keeps the original retry accessible after the initial assignment is observed as committed", () => {
  const view = render(<InitialAssignment administrative />);
  expect(screen.getByText("Reparto registrado")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Confirmar reparto inicial" }),
  ).not.toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  expect(mocks.retry).toHaveBeenCalledOnce();
  expect(mocks.hold).toHaveBeenCalledOnce();
  mocks.uncertain = false;
  view.rerender(<InitialAssignment administrative />);
  expect(mocks.release).toHaveBeenCalledOnce();
});

it.each(["initial", "championship"])(
  "retains %s retry when a background read fails",
  (component) => {
    mocks.error = new Error("read unavailable");
    render(
      component === "initial" ? (
        <InitialAssignment administrative />
      ) : (
        <ChampionshipReview seasonName="Liga" />
      ),
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
    );
    expect(mocks.retry).toHaveBeenCalledOnce();
    expect(mocks.hold).toHaveBeenCalledOnce();
  },
);

it("does not lock participant navigation for a read-only initial assignment", () => {
  render(<InitialAssignment />);
  expect(mocks.hold).not.toHaveBeenCalled();
});
