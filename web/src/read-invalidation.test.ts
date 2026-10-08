import { expect, it } from "vitest";
import { affectedRead, invalidationFor } from "./read-invalidation";
const read = (tail: string) => `/v1/read/seasons/s/${tail}`;
it.each([
  ["matchdays/d/results", ["league", "overview"], ["shop", "pc"]],
  [
    "wipe-revivals",
    ["league", "overview", "inventory"],
    ["pc", "scouting?trainer_id=x"],
  ],
  [
    "shop/purchases/p/redemptions",
    ["league", "overview", "shop", "inventory"],
    ["pc"],
  ],
  ["progress", ["league", "overview", "shop", "progress"], ["pc"]],
  [
    "matchdays/d/team-lock",
    [
      "overview",
      "team-preview?mode=battle&trainer_id=x",
      "scouting?trainer_id=x",
    ],
    ["shop", "pc"],
  ],
  ["rules", [], ["pc", "shop"]],
  [
    "finish",
    ["league", "overview", "shop", "team-preview?mode=spectator"],
    ["pc"],
  ],
])(
  "maps %s to affected views without unrelated refetch",
  (command, yes, no) => {
    for (const path of yes)
      expect(affectedRead(`/v1/seasons/s/${command}`, read(path))).toBe(true);
    for (const path of no)
      expect(affectedRead(`/v1/seasons/s/${command}`, read(path))).toBe(false);
  },
);
it("isolates viewers and seasons while marking all public/self modes stale", () => {
  const predicate = invalidationFor(
    "owner",
    "/v1/seasons/s/matchdays/d/team-lock",
  );
  expect(
    predicate({ queryKey: ["owner", read("scouting?trainer_id=x")] }),
  ).toBe(true);
  expect(
    predicate({ queryKey: ["rival", read("scouting?trainer_id=x")] }),
  ).toBe(false);
  expect(
    predicate({ queryKey: ["owner", "/v1/read/seasons/other/overview"] }),
  ).toBe(false);
  expect(predicate({ queryKey: ["owner", "/v1/read/trainers"] })).toBe(false);
});
it("rules refresh current rules/setup and close refreshes participant/admin day state", () => {
  for (const path of ["rules", "setup"])
    expect(
      affectedRead("/v1/admin/seasons/s/rules", `/v1/admin/seasons/s/${path}`),
    ).toBe(true);
  for (const path of [
    "/v1/admin/seasons/s/matchdays/d",
    "/v1/seasons/s/matchdays/d",
  ])
    expect(affectedRead("/v1/seasons/s/matchdays/d/close", path)).toBe(true);
});
