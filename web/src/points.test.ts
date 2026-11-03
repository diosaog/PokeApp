import { expect, it } from "vitest";
import { points, pointsOr } from "./points";

it("shows integers as integers and meaningful tenths only", () => {
  expect(points("0")).toBe("0");
  expect(points("1")).toBe("1");
  expect(points("2")).toBe("2");
  expect(points("-1")).toBe("-1");
  expect(points("0.3")).toBe("0,3");
  expect(points("-0.4")).toBe("-0,4");
  expect(points("1.7")).toBe("1,7");
  expect(points("-2.1")).toBe("-2,1");
});

it("removes trailing zeroes and the artefacts of exact decimal text", () => {
  // The value the home pill used to print verbatim.
  expect(points("0.000000000000000000000")).toBe("0");
  expect(points("-0.000000000000000000000")).toBe("0");
  expect(points("2.0")).toBe("2");
  expect(points("-0.40")).toBe("-0,4");
  expect(points("1.700000000000000000000")).toBe("1,7");
  expect(points("0E-21")).toBe("0");
  expect(points("-3E-1")).toBe("-0,3");
  expect(points("1.5E+1")).toBe("15");
  expect(points("-0")).toBe("0");
  expect(points("+0.3")).toBe("0,3");
});

it("keeps large scores exact and grouped", () => {
  expect(points("12345")).toBe("12.345");
  expect(points("-12345.6")).toBe("-12.345,6");
  expect(points("9007199254740993.1")).toBe("9.007.199.254.740.993,1");
});

it("never rounds or hides data that is not a tenth", () => {
  expect(points("10.25")).toBe("10,25");
  expect(points("not a number")).toBe("not a number");
  expect(points("")).toBe("");
});

it("accepts numbers without floating-point noise for exact values", () => {
  expect(points(0)).toBe("0");
  expect(points(-0)).toBe("0");
  expect(points(1.7)).toBe("1,7");
  expect(points(-2)).toBe("-2");
});

it("keeps unknown points distinguishable from a real zero", () => {
  expect(pointsOr(null)).toBe("—");
  expect(pointsOr(undefined)).toBe("—");
  expect(pointsOr(null, "Pendiente de confirmar")).toBe("Pendiente de confirmar");
  expect(pointsOr("0.000")).toBe("0");
});
