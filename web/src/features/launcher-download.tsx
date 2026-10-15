import { Download } from "lucide-react";
import launcher from "../../../companion/launcher/package.json";

export function LauncherDownload() {
  return (
    <>
      <a
        className="button primary"
        href="/launcher/download"
        download="PokeApp-Launcher-Setup.exe"
      >
        <Download aria-hidden="true" /> Descargar Launcher
      </a>
      <p className="muted">Windows 10/11 · v{launcher.version}</p>
    </>
  );
}
