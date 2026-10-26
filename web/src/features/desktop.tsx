import { Link, useParams } from "react-router-dom";
import { Heading } from "../ui";
import { desktopPanels, insideLauncher } from "../launcher";
import { LauncherDownload } from "./launcher-download";

// /escritorio/<panel>: inside PokeApp Launcher the native tool opens over this
// page, beside the sidebar; in a browser it explains where the tool lives.
export function DesktopPage() {
  const { panel } = useParams();
  const entry = desktopPanels.find(([key]) => key === panel);
  if (!entry)
    return (
      <section className="empty">
        <h1>Herramienta no encontrada</h1>
        <Link to="/">Volver a Inicio</Link>
      </section>
    );
  const [, title, detail] = entry;
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
        <p className="muted">Abriendo la herramienta de escritorio…</p>
      </section>
    </>
  );
}
