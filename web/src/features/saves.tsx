import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArchiveRestore,
  CloudUpload,
  HardDrive,
  MonitorDown,
  Radar,
  ShieldCheck,
} from "lucide-react";
import { usePC } from "../state";
import { Card, Heading, Notice, Tag, date } from "../ui";
import { insideLauncher, launcherWithoutHub } from "../launcher";
import { MyProgress, SaveGame } from "./progress";
import { LauncherDownload } from "./launcher-download";
import { WithSeason } from "./core";

const tabs = [
  ["partidas", "Mis partidas"],
  ["copias", "Copias de seguridad"],
  ["launcher", "Launcher"],
] as const;
type Tab = (typeof tabs)[number][0];

// Launcher 0.25.x opens these views as panels from the 27C routes.
function OlderLauncherPanel({
  panel,
  label,
}: {
  panel: string;
  label: string;
}) {
  return (
    <Link className="button primary" to={`/escritorio/${panel}`}>
      {label}
    </Link>
  );
}

// «Saves y Launcher». Inside PokeApp Launcher this route opens the native hub
// (the same three tabs, with the save on this PC). In a browser it shows what
// PokeApp already has and what the Launcher does, with its download.
export function SavesPage() {
  const [tab, setTab] = useState<Tab>("partidas");
  return (
    <>
      <Heading eyebrow="TU PARTIDA, BAJO CONTROL" title="Saves y Launcher">
        Tu partida del juego, sus copias y tu Launcher, en un solo lugar.
      </Heading>
      <nav className="tabs hub-tabs" aria-label="Saves y Launcher">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : ""}
            aria-pressed={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "partidas" && <Saves />}
      {tab === "copias" && <Backups />}
      {tab === "launcher" && <LauncherTab />}
    </>
  );
}

function Saves() {
  const pc = usePC();
  const save = pc.data?.save;
  return (
    <>
      <div className="hub-layout">
        <Card className="hub-save">
          <span className="eyebrow">PARTIDA EN POKEAPP</span>
          <Notice error={pc.error} />
          {save ? (
            <>
              <div className="hub-save-head">
                <SaveGame game={save.game} />
                <Tag>
                  {pc.data!.status === "ready"
                    ? "Sincronizada"
                    : "Pendiente de preparar"}
                </Tag>
              </div>
              <p className="hub-save-when">
                Última sincronización · {date(save.uploaded_at)}
              </p>
              <Link className="button primary" to="/pc">
                Abrir mi PC
              </Link>
            </>
          ) : (
            <div className="hub-empty">
              <HardDrive aria-hidden="true" />
              <h2>
                {pc.isPending
                  ? "Consultando tu partida…"
                  : "Aún no hay partida en esta temporada"}
              </h2>
              <p>
                PokeApp Launcher busca tu partida en el emulador y la envía sola
                cuando cambia.
              </p>
            </div>
          )}
        </Card>
        <Card className="hub-launcher">
          <span className="eyebrow">EN TU EQUIPO</span>
          <h2>PokeApp Launcher</h2>
          <ul className="hub-facts">
            <li>
              <Radar aria-hidden="true" /> Encuentra tu partida: una se elige
              sola; si hay varias, eliges en un momento.
            </li>
            <li>
              <CloudUpload aria-hidden="true" /> Sincroniza solo cuando cambia y
              el archivo está estable, sin duplicados.
            </li>
          </ul>
          {launcherWithoutHub() ? (
            <OlderLauncherPanel panel="partida" label="Abrir Mi partida" />
          ) : insideLauncher() ? (
            <p className="muted">
              Estás en PokeApp Launcher: abre «Saves y Launcher» en la barra
              lateral para ver la partida de este equipo.
            </p>
          ) : (
            <LauncherDownload />
          )}
        </Card>
      </div>
      <WithSeason>
        <MyProgress />
      </WithSeason>
    </>
  );
}

function Backups() {
  return (
    <div className="hub-layout three">
      {(
        [
          [
            ShieldCheck,
            "Antes de cada cambio",
            "PokeApp guarda una copia completa y verificada de tu partida antes de modificarla.",
          ],
          [
            ArchiveRestore,
            "Una copia diaria, 30 días",
            "El estado antes del primer cambio de cada día se conserva un mes.",
          ],
          [
            HardDrive,
            "Restaurar con «Confirmo»",
            "Comprueba la copia, el juego y que el emulador esté cerrado, y guarda antes el estado actual.",
          ],
        ] as const
      ).map(([Icon, title, detail]) => (
        <Card key={title} className="hub-feature">
          <Icon aria-hidden="true" />
          <h2>{title}</h2>
          <p>{detail}</p>
        </Card>
      ))}
      <Card className="hub-feature wide">
        <h2>Tus copias viven en tu equipo</h2>
        <p>
          Las copias de seguridad se guardan en el ordenador donde juegas, no en
          la nube. Consúltalas, expórtalas o restáuralas desde PokeApp Launcher.
        </p>
        {launcherWithoutHub() ? (
          <OlderLauncherPanel
            panel="copias"
            label="Abrir copias de seguridad"
          />
        ) : (
          !insideLauncher() && <LauncherDownload />
        )}
      </Card>
    </div>
  );
}

function LauncherTab() {
  return (
    <div className="hub-layout">
      <Card className="hub-launcher">
        <MonitorDown aria-hidden="true" />
        <h2>
          {launcherWithoutHub()
            ? "Tu Launcher"
            : insideLauncher()
              ? "Buscar actualizaciones"
              : "Descargar Launcher"}
        </h2>
        {launcherWithoutHub() ? (
          <>
            <p>
              Esta versión se actualiza instalando la nueva desde la web de
              PokeApp cuando se publique. Su conexión y su sincronización están
              en «Conexión».
            </p>
            <OlderLauncherPanel panel="nube" label="Abrir Conexión" />
          </>
        ) : insideLauncher() ? (
          <p>
            Abre «Saves y Launcher» › Launcher para buscar actualizaciones. Solo
            se instalan versiones firmadas y verificadas.
          </p>
        ) : (
          <>
            <p>
              PokeApp completo en tu escritorio, con tu partida al lado. Inicias
              sesión una vez y se queda guardada de forma segura en tu equipo.
            </p>
            <LauncherDownload />
          </>
        )}
      </Card>
      <Card className="hub-launcher">
        <h2>Qué hace en tu equipo</h2>
        <ul className="hub-facts">
          <li>
            <Radar aria-hidden="true" /> Detecta tu partida en el emulador sin
            modificarla.
          </li>
          <li>
            <CloudUpload aria-hidden="true" /> Sincroniza sola, también con el
            emulador abierto, y espera a que el archivo esté estable.
          </li>
          <li>
            <ShieldCheck aria-hidden="true" /> Nunca cambia una partida abierta:
            los cambios se confirman con el juego cerrado.
          </li>
        </ul>
      </Card>
    </div>
  );
}
