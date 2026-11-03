// League points arrive as exact decimal text (the official scoring works in
// tenths). They are never converted through binary floating point and never
// rounded: the text is only normalised for display.
//   "0.000000000000000000000" → "0"    "-0.40" → "-0,4"    "12" → "12"
//   "0E-21" → "0"                      "-0" → "0"          "10.25" → "10,25"
// A value that is not a decimal number is shown as received, so invalid data
// stays visible instead of being silently turned into a plausible score.
const DECIMAL = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d{1,4}))?$/;

export function points(value: string | number): string {
  const raw =
    typeof value === "number"
      ? Number.isFinite(value)
        ? String(value)
        : ""
      : value.trim();
  const match = DECIMAL.exec(raw);
  if (!match || !(match[2] || match[3])) return String(value);
  let digits = (match[2] ?? "") + (match[3] ?? "");
  // Position of the decimal point inside `digits` after applying the exponent.
  let point = (match[2] ?? "").length + Number(match[4] ?? 0);
  if (point < 0) {
    digits = "0".repeat(-point) + digits;
    point = 0;
  }
  if (point > digits.length) digits += "0".repeat(point - digits.length);
  const integer = digits.slice(0, point).replace(/^0+/, "") || "0";
  const fraction = digits.slice(point).replace(/0+$/, "");
  const zero = integer === "0" && !fraction;
  const sign = match[1] === "-" && !zero ? "-" : "";
  return `${sign}${BigInt(integer).toLocaleString("es-ES")}${fraction ? `,${fraction}` : ""}`;
}

/** Unknown or unconfirmed points stay distinguishable from a real zero. */
export function pointsOr(
  value: string | number | null | undefined,
  unknown = "—",
) {
  return value == null ? unknown : points(value);
}
