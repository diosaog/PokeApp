import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { RegistrationForm, registrationRecoveryKey } from "./registration";
import { ApiError } from "../api/client";
const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: { request: mocks.request },
}));
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  mocks.request.mockResolvedValue({ status: "registered" });
});
afterEach(cleanup);
function fill() {
  fireEvent.change(screen.getByLabelText("Nombre de entrenador"), {
    target: { value: "Nuevo" },
  });
  fireEvent.change(screen.getByLabelText("PIN de cuatro cifras"), {
    target: { value: "0061" },
  });
  fireEvent.change(screen.getByLabelText("Repetir PIN"), {
    target: { value: "0061" },
  });
  fireEvent.change(screen.getByLabelText("Código de acceso a la App"), {
    target: { value: "invitation-fixture" },
  });
}
it("sends exactly the approved fields to server validation and then returns to login", async () => {
  const registered = vi.fn();
  render(<RegistrationForm onRegistered={registered} onCancel={vi.fn()} />);
  fill();
  fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
  await waitFor(() => expect(registered).toHaveBeenCalledWith("Nuevo"));
  expect(JSON.parse(mocks.request.mock.calls[0][1].body)).toEqual({
    trainer_name: "Nuevo",
    pin: "0061",
    confirmation: "0061",
    access_code: "invitation-fixture",
  });
  expect(mocks.request.mock.calls[0][2]).toBe(false);
  expect(sessionStorage.length).toBe(0);
});
it("retains only an opaque key and repeats the same registration after an unknown result", async () => {
  mocks.request.mockRejectedValueOnce(
    new ApiError(503, "ACCOUNT_RETRY_REQUIRED"),
  );
  render(<RegistrationForm onRegistered={vi.fn()} onCancel={vi.fn()} />);
  fill();
  fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
  const retry = await screen.findByRole("button", {
    name: "Reintentar el mismo registro",
  });
  expect(sessionStorage.length).toBe(1);
  expect(sessionStorage.getItem(registrationRecoveryKey)).not.toContain("0061");
  fireEvent.click(retry);
  await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  expect(mocks.request.mock.calls[0]).toEqual(mocks.request.mock.calls[1]);
});
it("does not submit mismatched PINs", () => {
  render(<RegistrationForm onRegistered={vi.fn()} onCancel={vi.fn()} />);
  fill();
  fireEvent.change(screen.getByLabelText("Repetir PIN"), {
    target: { value: "9999" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
  expect(mocks.request).not.toHaveBeenCalled();
});
it("keeps the initial authorization in memory only and sends it with the invitation", async () => {
  mocks.request.mockRejectedValueOnce(
    new ApiError(503, "ACCOUNT_RETRY_REQUIRED"),
  );
  render(
    <RegistrationForm
      bootstrapRequired
      onRegistered={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  fill();
  fireEvent.change(screen.getByLabelText("Autorización de alta inicial"), {
    target: { value: "fictional-bootstrap" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
  await screen.findByRole("button", { name: "Reintentar el mismo registro" });
  expect(JSON.parse(mocks.request.mock.calls[0][1].body).bootstrap_token).toBe(
    "fictional-bootstrap",
  );
  expect(sessionStorage.length).toBe(1);
  expect(sessionStorage.getItem(registrationRecoveryKey)).not.toContain(
    "fictional-bootstrap",
  );
});
