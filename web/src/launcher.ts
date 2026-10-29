import type { Session } from "./api/types";

// PokeApp Launcher hosts this same web and adds a marker to its user agent.
// Inside it, a few routes are doors the Launcher watches: /saves opens its
// native «Saves y Launcher» hub, and /escritorio/objetos/<item> and
// /escritorio/robos open native dialogs over the web. The web never sends the
// Launcher data or commands: it only navigates.
export const insideLauncher = () =>
  typeof navigator !== "undefined" &&
  navigator.userAgent.includes("PokeAppLauncher/");

export const infiniteItemPath = (item: string) => `/escritorio/objetos/${item}`;
export const deliveriesPath = "/escritorio/robos";
// Links from 27C (Mi partida, Copias, Conexión) now live in the hub's tabs.
export const legacyDesktopPanels = ["partida", "copias", "nube"] as const;
// Launchers before 0.26.0 have no native hub at /saves: they still open their
// panels from the 27C routes, so the hub links there for them.
export function launcherWithoutHub() {
  const version = /PokeAppLauncher\/(\d+)\.(\d+)\./.exec(
    typeof navigator === "undefined" ? "" : navigator.userAgent,
  );
  return (
    Boolean(version) && Number(version![1]) === 0 && Number(version![2]) < 26
  );
}

// Session bridge. The Launcher keeps the session (encrypted on this PC) and
// hands this web an access token only — never the refresh token — through
// window.__pokeappLauncherSession. The web asks for one with a navigation to
// a fixed, data-free path that the Launcher intercepts (the page never leaves).
type Offer = { access_token: string; expires_at: number; trainer_id: string };
// A renewal answer: a fresh token, a definitive "no session in the Launcher",
// or null when no answer arrived in time (never a reason to sign out).
export type LauncherRenewal = Session | "signed_out" | null;
declare global {
  interface Window {
    __pokeappLauncherSession?: (offer: unknown) => void;
    __pokeappLauncherEvent?: (event: unknown) => void;
  }
}
const ask = (path: "/__launcher/session" | "/__launcher/logout") => {
  if (insideLauncher()) window.location.assign(path);
};
function parse(offer: unknown): (Session & { trainer_id: string }) | null {
  if (!offer || typeof offer !== "object") return null;
  const { access_token, expires_at, trainer_id } = offer as Offer;
  if (
    typeof access_token !== "string" ||
    access_token.length < 16 ||
    access_token.length > 8192 ||
    !Number.isSafeInteger(expires_at) ||
    typeof trainer_id !== "string" ||
    !/^[0-9a-f-]{36}$/.test(trainer_id)
  )
    return null;
  // No refresh token: renewing goes through the Launcher again.
  return {
    user_id: "",
    access_token,
    refresh_token: "",
    expires_at,
    trainer_id,
  };
}
let waiting: ((session: LauncherRenewal) => void)[] = [];
export function listenForLauncherSession(
  adopt: (session: Session, trainerId: string) => void,
  signedOut: () => void = () => {},
) {
  if (!insideLauncher()) return () => {};
  window.__pokeappLauncherSession = (offer) => {
    const resolved = waiting;
    if (
      offer &&
      typeof offer === "object" &&
      (offer as { signed_out?: unknown }).signed_out === true
    ) {
      waiting = [];
      resolved.forEach((resolve) => resolve("signed_out"));
      signedOut();
      return;
    }
    const session = parse(offer);
    if (!session) return;
    waiting = [];
    resolved.forEach((resolve) => resolve(session));
    adopt(session, session.trainer_id);
  };
  return () => {
    delete window.__pokeappLauncherSession;
  };
}
export const requestLauncherSession = () => ask("/__launcher/session");
// A fresh access token from the Launcher, "signed_out" when it has no
// session, or null when it did not answer in time.
export function renewFromLauncher(): Promise<LauncherRenewal> {
  if (!insideLauncher()) return Promise.resolve(null);
  return new Promise((resolve) => {
    waiting.push(resolve);
    ask("/__launcher/session");
    setTimeout(() => {
      waiting = waiting.filter((entry) => entry !== resolve);
      resolve(null);
    }, 30000);
  });
}
// Changes the Launcher confirmed (fixed names only, no data).
const LAUNCHER_EVENTS = [
  "save-synced",
  "save-changed",
  "account-changed",
  "items-changed",
] as const;
export type LauncherEvent = (typeof LAUNCHER_EVENTS)[number];
export function listenForLauncherEvents(
  onEvent: (type: LauncherEvent) => void,
) {
  if (!insideLauncher()) return () => {};
  window.__pokeappLauncherEvent = (event) => {
    const type = (event as { type?: unknown } | null)?.type;
    if (LAUNCHER_EVENTS.includes(type as LauncherEvent))
      onEvent(type as LauncherEvent);
  };
  return () => {
    delete window.__pokeappLauncherEvent;
  };
}
// Signing out of PokeApp also unlinks the Launcher and stops its sync.
export const tellLauncherLogout = () => ask("/__launcher/logout");
