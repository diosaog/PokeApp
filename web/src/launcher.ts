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

// Session bridge. The Launcher keeps the session (encrypted on this PC) and
// hands this web an access token only — never the refresh token — through
// window.__pokeappLauncherSession. The web asks for one with a navigation to
// a fixed, data-free path that the Launcher intercepts (the page never leaves).
type Offer = { access_token: string; expires_at: number; trainer_id: string };
declare global {
  interface Window {
    __pokeappLauncherSession?: (offer: unknown) => void;
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
let waiting: ((session: Session | null) => void)[] = [];
export function listenForLauncherSession(
  adopt: (session: Session, trainerId: string) => void,
) {
  if (!insideLauncher()) return () => {};
  window.__pokeappLauncherSession = (offer) => {
    const session = parse(offer);
    if (!session) return;
    const resolved = waiting;
    waiting = [];
    resolved.forEach((resolve) => resolve(session));
    adopt(session, session.trainer_id);
  };
  return () => {
    delete window.__pokeappLauncherSession;
  };
}
export const requestLauncherSession = () => ask("/__launcher/session");
// A fresh access token from the Launcher, or null when it has none to give.
export function renewFromLauncher(): Promise<Session | null> {
  if (!insideLauncher()) return Promise.resolve(null);
  return new Promise((resolve) => {
    waiting.push(resolve);
    ask("/__launcher/session");
    setTimeout(() => {
      waiting = waiting.filter((entry) => entry !== resolve);
      resolve(null);
    }, 15000);
  });
}
// Signing out of PokeApp also unlinks the Launcher and stops its sync.
export const tellLauncherLogout = () => ask("/__launcher/logout");
