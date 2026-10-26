import { useSyncExternalStore } from "react";

// Audio-visual preferences: presentation only, kept in this browser (or this
// Launcher's web session). Never sent to the API, never part of an account.
export type Prefs = {
  sound: boolean;
  volume: number; // 0..1
  motion: "full" | "reduced";
};
const KEY = "pokeapp.preferences.v1";
export const defaultPrefs: Prefs = { sound: true, volume: 0.5, motion: "full" };
let current: Prefs | null = null;
const listeners = new Set<() => void>();

function load(): Prefs {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "{}");
    return {
      sound: typeof raw.sound === "boolean" ? raw.sound : defaultPrefs.sound,
      volume:
        typeof raw.volume === "number" && raw.volume >= 0 && raw.volume <= 1
          ? raw.volume
          : defaultPrefs.volume,
      motion: raw.motion === "reduced" ? "reduced" : "full",
    };
  } catch {
    return defaultPrefs;
  }
}

export function readPrefs(): Prefs {
  return (current ??= load());
}

const systemReduced = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Reduced when the trainer asks for it or the system does; CSS and the sprite
// animation both read this one attribute.
export function reducedMotion() {
  return readPrefs().motion === "reduced" || systemReduced();
}
function apply() {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.motion = reducedMotion()
    ? "reduced"
    : "full";
}

export function writePrefs(patch: Partial<Prefs>) {
  current = { ...readPrefs(), ...patch };
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    // Private mode or blocked storage: the choice lasts for this visit.
  }
  apply();
  listeners.forEach((listener) => listener());
}

export function installPreferences() {
  apply();
  if (typeof window.matchMedia === "function")
    window
      .matchMedia("(prefers-reduced-motion: reduce)")
      .addEventListener("change", () => {
        apply();
        listeners.forEach((listener) => listener());
      });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function usePrefs(): Prefs {
  return useSyncExternalStore(subscribe, readPrefs, readPrefs);
}
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, reducedMotion, () => false);
}
