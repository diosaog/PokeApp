import { roundTo } from "@/utils/math";

export const formatCurrency = (value: number): string =>
  new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 0,
  }).format(value) + " $";

export const formatMinutes = (minutes: number): string => {
  if (minutes < 60) {
    return `${roundTo(minutes, 1)} min`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
};

export const formatProbability = (value: number): string => `${roundTo(value * 100, 3)} %`;
