import type { Model } from "../api/types";
import { gameName } from "./progress";

// 072 (owner decision 2026-10-29, «Tienda honesta + entrega en bolsa»): each
// Shop item says what it is for and which games hold it; the server refuses
// what the trainer's league game cannot use.
type Use = Model<"ItemUseRead">;

function gamesText(games: string[]) {
  if (games.length >= 8) return "Existe en los 8 juegos de 3DS.";
  const names = games.map(gameName);
  return `Solo existe en ${names.slice(0, -1).join(", ")}${names.length > 1 ? " y " : ""}${names.at(-1)}.`;
}

// What the item is for, in one sentence (null: no use defined yet).
export function useSummary(use?: Use | null): string | null {
  if (!use) return null;
  switch (use.mode) {
    case "pokemon":
      return "Se usa sobre un Pokémon desde tu inventario.";
    case "bag":
      return `Objeto del juego: PokeApp Launcher lo añade a la bolsa de tu partida. ${gamesText(use.games)}`;
    case "choice":
      return `Eliges cuál al añadirlo a la bolsa con PokeApp Launcher. ${gamesText(use.games)}`;
    case "permission":
      return "Permiso de PokeApp: se usa desde tu inventario y no va a la bolsa.";
    case "unavailable":
      return "No existe en los juegos de 3DS.";
    default:
      return null;
  }
}

// Why it cannot be bought now, or null.
export function purchaseBlock(use?: Use | null): string | null {
  if (use?.reason === "ITEM_NOT_USABLE") return "No disponible";
  if (use?.reason === "ITEM_INCOMPATIBLE_WITH_GAME")
    return "No existe en tu juego";
  return null;
}
