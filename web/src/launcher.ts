// PokeApp Launcher hosts this same web and adds a marker to its user agent.
// Inside it, the web's /escritorio routes are the doors to the native tools:
// the Launcher watches the URL and opens the matching panel beside the sidebar.
// The web never sends it data or commands.
export const insideLauncher = () =>
  typeof navigator !== "undefined" &&
  navigator.userAgent.includes("PokeAppLauncher/");

export const desktopPanels = [
  ["partida", "Mi partida", "Tu save, cambios autorizados, equipo y cajas"],
  ["objetos", "Objetos ∞", "Caramelos Raros y Escamas Corazón a tu partida"],
  ["robos", "Robos y entregas", "Retiradas y recepciones en tu partida"],
  ["copias", "Copias de seguridad", "Copias diarias de 30 días y recuperación"],
  ["nube", "Conexión", "Sincronización y estado de la nube"],
] as const;

export type DesktopPanel = (typeof desktopPanels)[number][0];
export const desktopPath = (panel: DesktopPanel, item?: string) =>
  `/escritorio/${panel}${item ? `/${item}` : ""}`;
