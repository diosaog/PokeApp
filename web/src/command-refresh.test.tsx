import { useEffect } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { api, ApiError } from "./api/client";
import { AppState, queries, useApp, useRead } from "./state";
import { CommandState, useCommand } from "./ui";

const paths = [
  "/v1/read/seasons/s/league",
  "/v1/read/seasons/s/shop",
  "/v1/read/seasons/s/overview",
  "/v1/read/seasons/s/pc",
  "/v1/read/seasons/other/league",
];
function Value({ path }: { path: string }) {
  const q = useRead<{ value: number }>(path);
  return <span data-testid={path}>{q.data?.value}</span>;
}
function Harness() {
  const { setMe } = useApp(),
    command = useCommand();
  useEffect(
    () =>
      setMe({
        trainer_id: "owner",
        display_name: "Antonio",
        is_admin: true,
        globally_enabled: true,
      }),
    [setMe],
  );
  return (
    <>
      {paths.map((p) => (
        <Value key={p} path={p} />
      ))}
      <button
        onClick={() =>
          void command.execute("/v1/seasons/s/shop/purchases", { item_id: "i" })
        }
      >
        Comprar
      </button>
      <CommandState command={command} />
    </>
  );
}
beforeEach(() => queries.clear());
afterEach(() => {
  cleanup();
  queries.clear();
  vi.restoreAllMocks();
});
it("refreshes active affected views exactly once after acceptance, with no F5 or cross-season reads", async () => {
  let value = 0;
  const read = vi
    .spyOn(api, "request")
    .mockImplementation(async () => ({ value }) as never);
  vi.spyOn(api, "command").mockImplementation(async () => {
    value++;
    return {};
  });
  render(
    <AppState>
      <Harness />
    </AppState>,
  );
  await waitFor(() =>
    expect(screen.getByTestId(paths[0])).toHaveTextContent("0"),
  );
  read.mockClear();
  fireEvent.click(screen.getByRole("button", { name: "Comprar" }));
  await waitFor(() =>
    expect(screen.getByTestId(paths[0])).toHaveTextContent("1"),
  );
  await waitFor(() =>
    expect(screen.getByTestId(paths[2])).toHaveTextContent("1"),
  );
  expect(screen.getByTestId(paths[1])).toHaveTextContent("1");
  expect(screen.getByTestId(paths[3])).toHaveTextContent("0");
  expect(screen.getByTestId(paths[4])).toHaveTextContent("0");
  expect(read.mock.calls.map((c) => c[0]).sort()).toEqual(
    paths.slice(0, 3).sort(),
  );
});
it("automatically refreshes conflicts but preserves exact key/body on an uncertain retry", async () => {
  let value = 0;
  vi.spyOn(api, "request").mockImplementation(async () => ({ value }) as never);
  const command = vi
    .spyOn(api, "command")
    .mockImplementationOnce(async () => {
      value = 2;
      throw new ApiError(409, "STALE_REVISION");
    })
    .mockRejectedValueOnce(new ApiError(503, "UNKNOWN"))
    .mockResolvedValue({});
  render(
    <AppState>
      <Harness />
    </AppState>,
  );
  await waitFor(() =>
    expect(screen.getByTestId(paths[0])).toHaveTextContent("0"),
  );
  fireEvent.click(screen.getByRole("button", { name: "Comprar" }));
  await waitFor(() =>
    expect(screen.getByTestId(paths[0])).toHaveTextContent("2"),
  );
  expect(
    screen.getByText(/Los datos cambiaron mientras editabas/),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Comprar" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
    ).toBeVisible(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Reintentar la misma solicitud" }),
  );
  await waitFor(() => expect(command).toHaveBeenCalledTimes(3));
  expect(command.mock.calls[2]).toEqual(command.mock.calls[1]);
  expect(command.mock.calls[1][2]).not.toBe(command.mock.calls[0][2]);
});
