import { Volume2, VolumeX } from "lucide-react";
import { Card, Tag } from "../ui";
import { usePrefs, useReducedMotion, writePrefs } from "../preferences";
import { play } from "../sound";

function Choice({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <div className="tabs pref-choice" role="group" aria-label={label}>
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

// Own profile: how PokeApp looks and sounds on this device.
export function PreferencesCard() {
  const prefs = usePrefs(),
    reduced = useReducedMotion(),
    systemAsks = reduced && prefs.motion === "full";
  return (
    <Card className="prefs-card">
      <div className="section-row">
        <h2>Ajustes de la app</h2>
        <Tag>En este dispositivo</Tag>
      </div>
      <div className="pref-row">
        <span>
          <strong>Sonidos</strong>
          <small>Efectos breves al navegar, confirmar y comprar.</small>
        </span>
        <Choice
          label="Sonidos"
          value={prefs.sound ? "on" : "off"}
          options={[
            ["on", "Activados"],
            ["off", "Desactivados"],
          ]}
          onChange={(value) => writePrefs({ sound: value === "on" })}
        />
      </div>
      <label className="pref-row">
        <span>
          <strong>Volumen</strong>
          <small>{Math.round(prefs.volume * 100)} %</small>
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(prefs.volume * 100)}
          disabled={!prefs.sound}
          onChange={(event) =>
            writePrefs({ volume: Number(event.target.value) / 100 })
          }
          onPointerUp={() => play("confirm")}
          onKeyUp={() => play("select")}
        />
      </label>
      <div className="pref-row">
        <span>
          <strong>Animaciones</strong>
          <small>
            {systemAsks
              ? "Tu sistema pide movimiento reducido y PokeApp lo respeta."
              : "Fondos de estadio, brillos, saltos de Pokémon y transiciones."}
          </small>
        </span>
        <Choice
          label="Animaciones"
          value={prefs.motion}
          options={[
            ["full", "Activadas"],
            ["reduced", "Reducidas"],
          ]}
          onChange={(value) =>
            writePrefs({ motion: value === "reduced" ? "reduced" : "full" })
          }
        />
      </div>
    </Card>
  );
}

// Sidebar: mute or unmute from anywhere.
export function SoundToggle() {
  const { sound } = usePrefs();
  return (
    <button
      type="button"
      className="icon-button sound-toggle"
      aria-label={sound ? "Silenciar sonidos" : "Activar sonidos"}
      aria-pressed={sound}
      onClick={() => {
        writePrefs({ sound: !sound });
        if (!sound) play("confirm");
      }}
    >
      {sound ? <Volume2 size={18} /> : <VolumeX size={18} />}
    </button>
  );
}
