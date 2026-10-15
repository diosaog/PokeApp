import { expect, it } from "vitest";
import { badgeAsset } from "./badges";
it("selects game-correct regional artwork without assigning progress", () => {
  expect(badgeAsset("unova", 1, "B")).toBe(33);
  expect(badgeAsset("unova", 1, "B2")).toBe(34);
  expect(badgeAsset("unova", 2, "W2")).toBe(35);
  expect(badgeAsset("unova", 8, "W2")).toBe(42);
  expect(badgeAsset("kalos", 8, "Y")).toBe(50);
  expect(badgeAsset("hoenn", 1, "OR")).toBe(17);
  expect(badgeAsset("kanto", 1, "HG")).toBe(1);
  expect(badgeAsset("johto", 1, "HG")).toBe(9);
});
it("fails safely for mismatched, ambiguous, nonexistent or unsupported badges", () => {
  expect(badgeAsset("unova", 1)).toBeNull();
  expect(badgeAsset("sinnoh", 1, "X")).toBeNull();
  expect(badgeAsset("alola", 1, "SN")).toBeNull();
  expect(badgeAsset("kalos", 0, "X")).toBeNull();
  expect(badgeAsset("kalos", 9, "X")).toBeNull();
  expect(badgeAsset("sinnoh", 1.5, "Pt")).toBeNull();
});
