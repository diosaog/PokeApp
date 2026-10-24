import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { AccountEditor, PinForm, pinRecoveryKey } from "./account-editor";
import { ApiError } from "../api/client";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  logout: vi.fn(),
  setMe: vi.fn(),
  hold: vi.fn(() => () => {}),
}));
vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: { request: mocks.request },
}));
vi.mock("../state", () => ({
  useApp: () => ({
    me: { trainer_id: "owner" },
    setMe: mocks.setMe,
    logout: mocks.logout,
    holdAdminNavigation: mocks.hold,
  }),
}));
const profile = {
  trainer_id: "owner",
  display_name: "Antonio",
  photo_url: null,
  revision: 3,
};
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  mocks.request.mockResolvedValue({ status: "changed" });
});
afterEach(cleanup);
it("requires independent renewal authorization, preserves retry, and stores only the operation ID", async () => {
  const authorization = "synthetic-authorization-token-00000000000000000";
  mocks.request.mockRejectedValueOnce(new ApiError(0, "NETWORK_ERROR"));
  render(<PinForm renewal />);
  expect(screen.queryByLabelText("PIN actual")).toBeNull();
  fireEvent.change(screen.getByLabelText("Código de renovación"), {
    target: { value: authorization },
  });
  fireEvent.change(screen.getByLabelText("Nuevo PIN"), {
    target: { value: "0028" },
  });
  fireEvent.change(screen.getByLabelText("Repetir nuevo PIN"), {
    target: { value: "0028" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Cambiar PIN" }));
  const retry = await screen.findByRole("button", {
    name: "Comprobar la misma solicitud",
  });
  expect(sessionStorage.length).toBe(1);
  expect(sessionStorage.getItem(`${pinRecoveryKey}:renewal`)).not.toContain(
    authorization,
  );
  fireEvent.click(retry);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  expect(mocks.request.mock.calls[0]).toEqual(mocks.request.mock.calls[1]);
  expect(mocks.request.mock.calls[0][0]).toBe("/v1/auth/pin-renewal");
  expect(mocks.request.mock.calls[0][2]).toBe(false);
  expect(JSON.parse(mocks.request.mock.calls[0][1].body)).toEqual({
    renewal_token: authorization,
    new_pin: "0028",
    confirmation: "0028",
  });
});
it("renames only the current account with its revision", async () => {
  render(<AccountEditor profile={profile} refresh={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Nombre de entrenador"), {
    target: { value: "Nuevo" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar nombre" }));
  await waitFor(() => expect(mocks.request).toHaveBeenCalled());
  const [path, init] = mocks.request.mock.calls[0];
  expect(path).toBe("/v1/account/name");
  expect(JSON.parse(init.body)).toEqual({
    display_name: "Nuevo",
    expected_revision: 3,
  });
});
it("keeps the exact profile key and body after a lost response", async () => {
  mocks.request.mockRejectedValueOnce(new ApiError(0, "NETWORK_ERROR"));
  render(<AccountEditor profile={profile} refresh={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Guardar nombre" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Reintentar la misma solicitud",
    }),
  );
  await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  expect(mocks.request.mock.calls[0]).toEqual(mocks.request.mock.calls[1]);
});
function fillPin() {
  fireEvent.change(screen.getByLabelText("PIN actual"), {
    target: { value: "0017" },
  });
  fireEvent.change(screen.getByLabelText("Nuevo PIN"), {
    target: { value: "0028" },
  });
  fireEvent.change(screen.getByLabelText("Repetir nuevo PIN"), {
    target: { value: "0028" },
  });
}
it("changes PIN then closes the session without storing credentials", async () => {
  render(<PinForm />);
  fillPin();
  fireEvent.click(screen.getByRole("button", { name: "Cambiar PIN" }));
  await waitFor(() => expect(mocks.logout).toHaveBeenCalledOnce());
  expect(sessionStorage.getItem(pinRecoveryKey)).toBeNull();
  expect(mocks.request.mock.calls[0][0]).toBe("/v1/account/pin");
});
it("resumes the same PIN intent using only a retained opaque key", async () => {
  mocks.request.mockRejectedValueOnce(
    new ApiError(503, "ACCOUNTS_UNAVAILABLE"),
  );
  render(<PinForm />);
  fillPin();
  fireEvent.click(screen.getByRole("button", { name: "Cambiar PIN" }));
  const retry = await screen.findByRole("button", {
    name: "Comprobar la misma solicitud",
  });
  expect(sessionStorage.length).toBe(1);
  expect(sessionStorage.getItem(pinRecoveryKey)).not.toMatch(/0017|0028/);
  fireEvent.click(retry);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  expect(mocks.request.mock.calls[1][0]).toBe("/v1/auth/pin-change/resume");
  expect(mocks.request.mock.calls[1][1]).toEqual(
    mocks.request.mock.calls[0][1],
  );
  expect(mocks.request.mock.calls[1][2]).toBe(false);
});
it("rejects mismatched PIN confirmation before any request", () => {
  render(<PinForm />);
  fillPin();
  fireEvent.change(screen.getByLabelText("Repetir nuevo PIN"), {
    target: { value: "0099" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Cambiar PIN" }));
  expect(mocks.request).not.toHaveBeenCalled();
});
