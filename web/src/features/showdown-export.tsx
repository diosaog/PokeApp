import { useRef, useState } from "react";
import { ClipboardCopy, LoaderCircle } from "lucide-react";
import { api, errorText } from "../api/client";
import type { Model } from "../api/types";
import { queries, useApp } from "../state";
import { Modal, notify } from "../ui";

type Export = Model<"ShowdownExportRead">;
type Warning = Model<"ShowdownWarningRead">;

export const COPIED = "Equipo copiado. Ya puedes pegarlo en Pokémon Showdown.";
const LEGALITY =
  "El texto se importa tal cual en Pokémon Showdown. Un formato con validador puede rechazar combinaciones de una partida aleatorizada; en ese caso usa «Custom Game».";

const warningText = (w: Warning) => {
  const at = `Equipo ${w.slot}`;
  switch (w.code) {
    case "egg_skipped":
      return `${at}: es un Huevo y no se exporta.`;
    case "species_unknown":
      return `${at}: especie no reconocida; no se exporta.`;
    case "form_unknown":
      return `${at}: forma no reconocida (${w.detail}); se exporta la forma base.`;
    case "form_unavailable":
      return `${at}: tu última sincronización no incluye la forma de ${w.detail}; se exporta la forma base.`;
    case "gender_unavailable":
      return `${at}: tu última sincronización no incluye el género; Showdown elegirá uno.`;
    case "nickname_unsupported":
      return `${at}: el mote «${w.detail}» no cabe en el formato; se exporta sin mote.`;
    case "item_not_in_showdown":
      return `${at}: ${w.detail} no existe en Showdown; se exporta sin objeto.`;
    case "item_unknown":
      return `${at}: objeto no reconocido; se exporta sin objeto.`;
    case "ivs_unavailable":
      return `${at}: IVs no disponibles; revísalos en Showdown.`;
    case "level_unavailable":
      return `${at}: nivel no disponible.`;
    default:
      return `${at}: un dato no reconocido se ha omitido.`;
  }
};

/**
 * «Generar Poképaste» on the own «Equipo» card. Nothing is generated until
 * the button is pressed; the server builds the text from the same save the
 * card shows, and it is only copied when it belongs to that save.
 */
export function ShowdownExport({
  save,
  personal,
}: {
  save: Model<"SaveRead">;
  personal: boolean;
}) {
  const { season, me } = useApp();
  const [busy, setBusy] = useState(false),
    [manual, setManual] = useState<string | null>(null);
  const running = useRef(false);
  const path = personal
    ? "/v1/me/pc/showdown"
    : `/v1/read/seasons/${season}/pc/showdown`;
  async function generate() {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    try {
      const result = await api.request<Export>(path);
      if (
        result.save_id !== save.id ||
        Date.parse(result.uploaded_at) !== Date.parse(save.uploaded_at)
      ) {
        // A newer sync arrived: show it first, never copy another team.
        void queries.invalidateQueries({
          predicate: (q) =>
            q.queryKey[0] === me?.trainer_id &&
            /\/pc$/.test(String(q.queryKey[1])),
        });
        notify(
          "Tu partida acaba de cambiar. Revisa el equipo actualizado y vuelve a generar el Poképaste.",
          "warn",
          { key: "showdown-export" },
        );
        return;
      }
      if (result.warnings?.length)
        notify(result.warnings.map(warningText).join(" "), "warn", {
          key: "showdown-export-warnings",
          ttl: 15000,
        });
      try {
        if (!navigator.clipboard?.writeText) throw new Error("no clipboard");
        await navigator.clipboard.writeText(result.text);
        notify(COPIED, "ok", { key: "showdown-export" });
      } catch {
        // Never claim a copy that did not happen: offer the text instead.
        setManual(result.text);
      }
    } catch (error) {
      notify(errorText(error), "error", { key: "showdown-export" });
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      <button
        type="button"
        className="button secondary showdown-export"
        disabled={busy}
        aria-busy={busy || undefined}
        title={LEGALITY}
        onClick={() => void generate()}
      >
        {busy ? (
          <LoaderCircle className="spin" size={16} aria-hidden="true" />
        ) : (
          <ClipboardCopy size={16} aria-hidden="true" />
        )}
        Generar Poképaste
      </button>
      {manual !== null && (
        <ManualCopy text={manual} onClose={() => setManual(null)} />
      )}
    </>
  );
}

function ManualCopy({ text, onClose }: { text: string; onClose: () => void }) {
  const area = useRef<HTMLTextAreaElement>(null);
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  return (
    <Modal
      title="Copia tu equipo"
      onClose={onClose}
      className="showdown-manual"
    >
      <p>
        No se pudo copiar automáticamente. Selecciona el texto y cópialo
        (Ctrl+C) para pegarlo en Pokémon Showdown.
      </p>
      <textarea
        ref={area}
        readOnly
        value={text}
        rows={Math.min(24, text.split("\n").length + 1)}
        aria-label="Equipo en formato Pokémon Showdown"
        autoFocus
        onFocus={(event) => event.currentTarget.select()}
      />
      <div className="toolbar">
        <button
          type="button"
          className="button primary"
          onClick={async () => {
            area.current?.select();
            try {
              await navigator.clipboard.writeText(text);
              setState("copied");
              notify(COPIED, "ok", { key: "showdown-export" });
            } catch {
              setState("failed");
            }
          }}
        >
          <ClipboardCopy size={16} aria-hidden="true" /> Copiar
        </button>
      </div>
      {state === "copied" && <p role="status">{COPIED}</p>}
      {state === "failed" && (
        <p role="status">
          El navegador no permite copiar desde aquí: usa Ctrl+C con el texto
          seleccionado.
        </p>
      )}
      <p className="caption">{LEGALITY}</p>
    </Modal>
  );
}
