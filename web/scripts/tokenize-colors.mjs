// One-shot design-system migration (Phase27B): every hard-coded colour in the
// legacy stylesheets becomes a semantic token from src/design/tokens.css.
// Mapping is deterministic (HSL lightness + hue family); alpha is preserved with
// color-mix. Run: node scripts/tokenize-colors.mjs [--check]
import { readFileSync, writeFileSync } from "node:fs";

const files = [
  "src/styles.css",
  "src/product.css",
  "src/art-direction.css",
  "src/product-polish.css",
];

function parse(hex) {
  let h = hex.slice(1);
  if (h.length <= 4) h = [...h].map((c) => c + c).join("");
  const n = (i) => parseInt(h.slice(i, i + 2), 16) / 255;
  return { r: n(0), g: n(2), b: n(4), a: h.length === 8 ? n(6) : 1 };
}

function hsl({ r, g, b }) {
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b),
    l = (max + min) / 2,
    d = max - min;
  if (!d) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h =
    max === r
      ? ((g - b) / d) % 6
      : max === g
        ? (b - r) / d + 2
        : (r - g) / d + 4;
  h = (h * 60 + 360) % 360;
  return { h, s, l };
}

function neutral(l) {
  if (l < 0.08) return "--bg-0";
  if (l < 0.11) return "--bg-1";
  if (l < 0.145) return "--surface-1";
  if (l < 0.19) return "--surface-2";
  if (l < 0.25) return "--surface-3";
  if (l < 0.34) return "--line";
  if (l < 0.46) return "--line-strong";
  if (l < 0.64) return "--text-muted";
  if (l < 0.8) return "--text-soft";
  return "--text";
}

function family(h) {
  if (h >= 40 && h < 62) return "gold";
  if (h >= 62 && h < 200) return "accent";
  if (h >= 200 && h < 255) return "info";
  if (h >= 255 && h < 318) return "violet";
  if (h >= 15 && h < 40) return "warm";
  return "danger";
}

export function token(hex) {
  const rgb = parse(hex),
    { h, s, l } = hsl(rgb);
  let name;
  if (s < 0.28 || l < 0.12 || l > 0.93) name = neutral(l);
  else {
    const f = family(h);
    name = l < 0.3 ? `--${f}-deep` : l > 0.74 ? `--${f}-soft` : `--${f}`;
  }
  const alpha = Math.round(rgb.a * 100);
  return alpha >= 100
    ? `var(--c${name.slice(1)})`
    : `color-mix(in srgb, var(--c${name.slice(1)}) ${alpha}%, transparent)`;
}

const check = process.argv.includes("--check");
const report = {};
for (const file of files) {
  const source = readFileSync(file, "utf8");
  const result = source.replace(/#[0-9a-fA-F]{3,8}\b/g, (hex) => {
    if (![3, 4, 6, 8].includes(hex.length - 1)) return hex;
    const value = token(hex.toLowerCase());
    report[hex.toLowerCase()] = value;
    return value;
  });
  if (check) {
    if (result !== source) {
      console.error(`${file} still has hard-coded colours`);
      process.exitCode = 1;
    }
  } else writeFileSync(file, result);
}
// A re-run finds nothing to map; keep the original migration record.
if (!check && Object.keys(report).length)
  writeFileSync(
    "scripts/tokenize-colors.report.json",
    JSON.stringify(report, null, 1) + "\n",
  );
console.log(`${Object.keys(report).length} colours mapped`);
