export const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

export const roundTo = (value: number, decimals: number): number => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};

export const safeDivide = (numerator: number, denominator: number, fallback = 0): number =>
  denominator === 0 ? fallback : numerator / denominator;
