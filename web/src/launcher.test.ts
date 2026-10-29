import { afterEach, expect, it, vi } from "vitest";
import {
  insideLauncher,
  listenForLauncherSession,
  renewFromLauncher,
  requestLauncherSession,
  tellLauncherLogout,
} from "./launcher";

const trainer = "11111111-1111-4111-8111-111111111111";
const offer = {
  access_token: "a".repeat(40),
  expires_at: 2_000_000_000,
  trainer_id: trainer,
};
const inLauncher = () =>
  vi
    .spyOn(navigator, "userAgent", "get")
    .mockReturnValue("Mozilla/5.0 PokeAppLauncher/0.26.0");
const navigation = () => {
  const assign = vi.fn();
  vi.spyOn(window, "location", "get").mockReturnValue({
    ...window.location,
    assign,
  });
  return assign;
};
afterEach(() => {
  vi.restoreAllMocks();
  delete window.__pokeappLauncherSession;
});

it("in a browser there is no bridge and nothing is requested", () => {
  const assign = navigation();
  expect(insideLauncher()).toBe(false);
  listenForLauncherSession(() => {});
  requestLauncherSession();
  tellLauncherLogout();
  expect(window.__pokeappLauncherSession).toBeUndefined();
  expect(assign).not.toHaveBeenCalled();
});

it("inside the Launcher it asks with data-free paths only", () => {
  inLauncher();
  const assign = navigation();
  requestLauncherSession();
  tellLauncherLogout();
  expect(assign.mock.calls).toEqual([
    ["/__launcher/session"],
    ["/__launcher/logout"],
  ]);
});

it("adopts an access token only, never a refresh token, and rejects junk", () => {
  inLauncher();
  const adopt = vi.fn();
  listenForLauncherSession(adopt);
  for (const junk of [
    null,
    "token",
    { ...offer, access_token: "short" },
    { ...offer, expires_at: "soon" },
    { ...offer, trainer_id: "../../admin" },
  ])
    window.__pokeappLauncherSession!(junk);
  expect(adopt).not.toHaveBeenCalled();
  window.__pokeappLauncherSession!({ ...offer, refresh_token: "r".repeat(40) });
  expect(adopt).toHaveBeenCalledTimes(1);
  const [session, trainerId] = adopt.mock.calls[0];
  expect(trainerId).toBe(trainer);
  expect(session.refresh_token).toBe("");
  expect(session.access_token).toBe(offer.access_token);
});

it("renewal waits for the Launcher; a slow answer is null, not a sign-out", async () => {
  vi.useFakeTimers();
  inLauncher();
  navigation();
  listenForLauncherSession(() => {});
  const renewed = renewFromLauncher();
  window.__pokeappLauncherSession!(offer);
  const fresh = await renewed;
  expect(fresh !== "signed_out" && fresh?.access_token).toBe(
    offer.access_token,
  );
  const none = renewFromLauncher();
  vi.advanceTimersByTime(15000);
  let settled = false;
  void none.then(() => (settled = true));
  await Promise.resolve();
  expect(settled).toBe(false); // still waiting after 15 s
  vi.advanceTimersByTime(15000);
  expect(await none).toBeNull();
  vi.useRealTimers();
});

it("an explicit «no session» from the Launcher is definitive", async () => {
  inLauncher();
  navigation();
  const signedOut = vi.fn();
  listenForLauncherSession(() => {}, signedOut);
  const renewal = renewFromLauncher();
  window.__pokeappLauncherSession!({ signed_out: true });
  expect(await renewal).toBe("signed_out");
  expect(signedOut).toHaveBeenCalledTimes(1);
});

it("Launcher events refresh the web for known changes only", async () => {
  const { listenForLauncherEvents } = await import("./launcher");
  inLauncher();
  const seen = vi.fn();
  const stop = listenForLauncherEvents(seen);
  window.__pokeappLauncherEvent!({ type: "save-synced" });
  window.__pokeappLauncherEvent!({ type: "rm -rf" });
  window.__pokeappLauncherEvent!(null);
  expect(seen.mock.calls).toEqual([["save-synced"]]);
  stop();
  expect(window.__pokeappLauncherEvent).toBeUndefined();
});
