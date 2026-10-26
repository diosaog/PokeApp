import { readPrefs } from "./preferences";

// PokeApp interface sounds, synthesised in the browser with Web Audio: short,
// soft and original (no audio files, no game music). They only play after the
// trainer has interacted with the page, as browsers require, never on hover,
// and silently do nothing where audio is unavailable.
export type Sfx =
  "select" | "nav" | "open" | "close" | "confirm" | "coin" | "error" | "notice";
// [frequency Hz, start s, duration s, waveform, relative gain]
type Note = [number, number, number, OscillatorType, number];
const kit: Record<Sfx, Note[]> = {
  select: [[1046, 0, 0.045, "triangle", 0.5]],
  nav: [
    [784, 0, 0.05, "triangle", 0.45],
    [1175, 0.045, 0.07, "triangle", 0.4],
  ],
  open: [
    [587, 0, 0.06, "sine", 0.7],
    [880, 0.05, 0.1, "sine", 0.6],
  ],
  close: [
    [880, 0, 0.05, "sine", 0.5],
    [587, 0.04, 0.08, "sine", 0.45],
  ],
  confirm: [
    [659, 0, 0.07, "triangle", 0.55],
    [831, 0.07, 0.07, "triangle", 0.55],
    [988, 0.14, 0.16, "triangle", 0.6],
  ],
  coin: [
    [988, 0, 0.07, "square", 0.22],
    [1319, 0.07, 0.24, "square", 0.22],
  ],
  error: [
    [233, 0, 0.11, "triangle", 0.7],
    [185, 0.1, 0.16, "triangle", 0.7],
  ],
  notice: [
    [740, 0, 0.07, "sine", 0.5],
    [740, 0.11, 0.07, "sine", 0.5],
  ],
};
const MASTER = 0.22; // the whole kit stays quiet even at full volume

let context: AudioContext | null = null;
let last = 0;

function unlock() {
  try {
    const Context =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Context) return;
    context ??= new Context();
    if (context.state === "suspended") void context.resume().catch(() => {});
  } catch {
    context = null;
  }
}

export function play(name: Sfx) {
  const prefs = readPrefs();
  if (!prefs.sound || !prefs.volume || !context || context.state !== "running")
    return;
  // Two sounds in the same instant (click + route change) read as one.
  const now = performance.now();
  if (now - last < 60) return;
  last = now;
  try {
    const start = context.currentTime + 0.005;
    const detune = 1 + (Math.random() - 0.5) * 0.03; // never twice identical
    for (const [frequency, at, duration, type, gain] of kit[name]) {
      const osc = context.createOscillator();
      const amp = context.createGain();
      osc.type = type;
      osc.frequency.value = frequency * detune;
      const peak = gain * prefs.volume * MASTER;
      amp.gain.setValueAtTime(0.0001, start + at);
      amp.gain.exponentialRampToValueAtTime(peak, start + at + 0.008);
      amp.gain.exponentialRampToValueAtTime(0.0001, start + at + duration);
      osc.connect(amp).connect(context.destination);
      osc.start(start + at);
      osc.stop(start + at + duration + 0.02);
    }
  } catch {
    // Audio is a nicety; nothing depends on it.
  }
}

// Sounds the markup can ask for without code: data-sfx="select|confirm|…";
// segmented tabs select by default.
function fromClick(event: MouseEvent) {
  const target = (event.target as Element | null)?.closest?.(
    "[data-sfx], .tabs button, [role='tab']",
  );
  if (!target || (target as HTMLButtonElement).disabled) return;
  const name = (target.getAttribute("data-sfx") || "select") as Sfx;
  if (name in kit) play(name);
}

export function installSound() {
  if (typeof window === "undefined") return;
  // The audio context may only start inside a user gesture.
  window.addEventListener("pointerdown", unlock, { capture: true });
  window.addEventListener("keydown", unlock, { capture: true });
  document.addEventListener("click", fromClick);
}
