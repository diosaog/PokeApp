import { Link, Navigate, useParams } from "react-router-dom";
import { Heading } from "../ui";
import { insideLauncher, legacyDesktopPanels } from "../launcher";
import { LauncherDownload } from "./launcher-download";

const tools: Record<string, [string, string]> = {
  objetos: [
    "Objetos ∞",
    "Caramelos Raros y Escamas Corazón, a la bolsa de tu partida",
  ],
  robos: ["Robos y entregas", "Retiradas y recepciones de robos en tu partida"],
};

// /escritorio/<tool>: inside PokeApp Launcher the native dialog opens over this
// page; in a browser it explains where the tool lives. The 27C links (Mi
// partida, Copias, Conexión) are tabs of «Saves y Launcher» now.
export function DesktopPage() {
  const { panel = "" } = useParams();
  const legacy = (legacyDesktopPanels as readonly string[]).includes(panel);
  if (legacy && !insideLauncher()) return <Navigate to="/saves" replace />;
  const entry = legacy
    ? (["Saves y Launcher", "Tu partida, tus copias y tu Launcher"] as const)
    : tools[panel];
  if (!entry)
    return (
      <section className="empty">
        <h1>Herramienta no encontrada</h1>
        <Link to="/">Volver a Inicio</Link>
      </section>
    );
  const [title, detail] = entry;
  if (!insideLauncher())
    return (
      <>
        <Heading eyebrow="POKEAPP LAUNCHER" title={title}>
          {detail}. Esta herramienta trabaja con la partida de tu equipo y solo
          está en PokeApp Launcher.
        </Heading>
        <section className="card desktop-download">
          <LauncherDownload />
        </section>
      </>
    );
  return (
    <>
      <Heading eyebrow="POKEAPP LAUNCHER" title={title}>
        {detail}.
      </Heading>
      <section className="desktop-host" aria-live="polite">
        <p className="muted">Abriendo en tu Launcher…</p>
      </section>
    </>
  );
}
