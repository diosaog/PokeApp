/** Artwork lookup only. Never derives earned progress or gameplay authority. */
const sequences: Record<string, number[]> = {
  kanto: [1, 2, 3, 4, 5, 6, 7, 8],
  johto: [9, 10, 11, 12, 13, 14, 15, 16],
  hoenn: [17, 18, 19, 20, 21, 22, 23, 24],
  sinnoh: [25, 26, 27, 28, 29, 30, 31, 32],
  bw: [33, 34, 36, 37, 38, 39, 40, 41],
  b2w2: [34, 35, 36, 37, 38, 39, 41, 42],
  kalos: [43, 44, 45, 46, 47, 48, 49, 50],
};
export const gameRegion: Record<string, string> = {
  R: "hoenn",
  S: "hoenn",
  E: "hoenn",
  OR: "hoenn",
  AS: "hoenn",
  FR: "kanto",
  LG: "kanto",
  HG: "johto",
  SS: "johto",
  D: "sinnoh",
  P: "sinnoh",
  Pt: "sinnoh",
  B: "unova",
  W: "unova",
  B2: "unova",
  W2: "unova",
  X: "kalos",
  Y: "kalos",
};
export function badgeAsset(
  region: string,
  number: number,
  game?: string | null,
) {
  if (!Number.isInteger(number) || number < 1 || number > 8) return null;
  if (
    game &&
    (!gameRegion[game] ||
      (gameRegion[game] !== region &&
        !(["HG", "SS"].includes(game) && region === "kanto")))
  )
    return null;
  const set =
    region === "unova"
      ? ["B", "W"].includes(game || "")
        ? "bw"
        : ["B2", "W2"].includes(game || "")
          ? "b2w2"
          : "unknown"
      : region;
  return sequences[set]?.[number - 1] ?? null;
}
