import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { api } from "./api/client";
import { AppState, useApp } from "./state";

function Probe() {
  const { capabilitiesKnown, registrationEnabled, renewalEnabled } = useApp();
  return (
    <p>
      {String(capabilitiesKnown)} {String(registrationEnabled)}{" "}
      {String(renewalEnabled)}
    </p>
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("sign-in options are unknown until the server answers, and nothing is stored", async () => {
  let answer!: (value: unknown) => void;
  vi.spyOn(api, "request").mockReturnValue(
    new Promise((resolve) => (answer = resolve)) as never,
  );
  render(
    <AppState>
      <Probe />
    </AppState>,
  );
  expect(screen.getByText("false false false")).toBeVisible();
  await act(async () =>
    answer({
      enabled: true,
      registration_enabled: true,
      bootstrap_required: false,
      renewal_enabled: true,
    }),
  );
  expect(screen.getByText("true true true")).toBeVisible();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});

it("an unreachable server ends the wait with no options offered", async () => {
  vi.spyOn(api, "request").mockRejectedValue(new Error("offline"));
  render(
    <AppState>
      <Probe />
    </AppState>,
  );
  await act(async () => {});
  expect(screen.getByText("true false false")).toBeVisible();
});
