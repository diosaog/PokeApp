import { afterEach, expect, it, vi } from "vitest";
import { installIdleMotion } from "./idle-motion";

let stop: (() => void) | undefined;
afterEach(() => {
  stop?.();
  vi.useRealTimers();
});

it("decorative motion pauses after the idle delay and resumes on input", () => {
  vi.useFakeTimers();
  const root = document.documentElement;
  stop = installIdleMotion(root, 1000);
  expect(root.hasAttribute("data-idle")).toBe(false);
  vi.advanceTimersByTime(999);
  expect(root.hasAttribute("data-idle")).toBe(false);
  vi.advanceTimersByTime(1);
  expect(root.hasAttribute("data-idle")).toBe(true);
  window.dispatchEvent(new KeyboardEvent("keydown"));
  expect(root.hasAttribute("data-idle")).toBe(false);
  vi.advanceTimersByTime(1000);
  expect(root.hasAttribute("data-idle")).toBe(true);
  window.dispatchEvent(new Event("pointermove"));
  expect(root.hasAttribute("data-idle")).toBe(false);
});

it("uninstalling removes the pause and stops listening", () => {
  vi.useFakeTimers();
  const root = document.documentElement;
  installIdleMotion(root, 1000)();
  vi.advanceTimersByTime(5000);
  expect(root.hasAttribute("data-idle")).toBe(false);
});
