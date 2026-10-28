// After a while without input, the decorative CSS loops (sky, sparkles,
// lamps, beams…) hold their current frame: the scene looks the same but stops
// repainting. Idle, those loops kept the GPU process at ~13 % of a core.
// Any input brings the motion back; loading spinners never pause.
export const IDLE_MS = 45_000;
const INPUT = [
  "pointermove",
  "pointerdown",
  "keydown",
  "wheel",
  "touchstart",
  "scroll",
  "focus",
];

export function installIdleMotion(
  root: HTMLElement = document.documentElement,
  delay = IDLE_MS,
) {
  let timer = 0;
  const wake = () => {
    root.removeAttribute("data-idle");
    window.clearTimeout(timer);
    timer = window.setTimeout(() => root.setAttribute("data-idle", ""), delay);
  };
  for (const name of INPUT)
    window.addEventListener(name, wake, { passive: true, capture: true });
  document.addEventListener("visibilitychange", wake);
  wake();
  return () => {
    window.clearTimeout(timer);
    for (const name of INPUT)
      window.removeEventListener(name, wake, { capture: true });
    document.removeEventListener("visibilitychange", wake);
    root.removeAttribute("data-idle");
  };
}
