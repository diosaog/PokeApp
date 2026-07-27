import { Clipboard, Download, FileUp, Undo2 } from "lucide-react";
import { useState } from "react";

import { formatCurrency, formatMinutes, formatProbability } from "@/components/common/format";
import { getSpeciesName } from "@/data/species";
import type { BreedingAction } from "@/domain/optimization/types";
import { useSession } from "@/state/sessionStore";

const recommendationToText = (action: BreedingAction | null): string => {
  if (!action) {
    return "No hay recomendacion calculada.";
  }

  return [
    "MEJOR SIGUIENTE CRIANZA",
    `Descendencia: ${getSpeciesName(action.offspringSpeciesId)}`,
    `Coste directo: ${formatCurrency(action.cost.directCashCost)}`,
    `Coste esperado: ${formatCurrency(action.expectedTotalCost)}`,
    `Tiempo esperado: ${formatMinutes(action.expectedTotalMinutes)}`,
    `Probabilidad objetivo directo: ${formatProbability(action.directTargetProbability)}`,
    `Probabilidad reproductor util: ${formatProbability(action.usefulBreederProbability)}`,
    ...action.explanation.map((line) => `- ${line}`),
  ].join("\n");
};

export const HistoryPage = () => {
  const { state, dispatch, exportProject, importProjectFromJson, canUndo, canRedo } = useSession();
  const [importText, setImportText] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const recommendation = state.optimizationResult?.recommendation ?? null;

  const downloadProject = (): void => {
    const json = JSON.stringify(exportProject(), null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "crianza-diosesmon.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const importProject = (): void => {
    try {
      const document = importProjectFromJson(importText);
      dispatch({ type: "import-project", document });
      setImportText("");
      setImportError(null);
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "JSON invalido.");
    }
  };

  const copyRecommendation = (): void => {
    const text = recommendationToText(recommendation);
    void navigator.clipboard.writeText(text);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
      <section className="surface p-4">
        <h2 className="mb-4 text-lg font-black">Exportar e importar</h2>
        <div className="grid gap-2">
          <button className="btn-primary" type="button" onClick={downloadProject}>
            <Download className="h-4 w-4" />
            Exportar proyecto JSON
          </button>
          <button className="btn-secondary" type="button" onClick={copyRecommendation}>
            <Clipboard className="h-4 w-4" />
            Copiar recomendacion
          </button>
          <button
            className="btn-secondary"
            type="button"
            onClick={() => {
              const blob = new Blob([recommendationToText(recommendation)], { type: "text/plain" });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "resumen-crianza.txt";
              link.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="h-4 w-4" />
            Descargar resumen
          </button>
          <div className="mt-3 grid gap-2">
            <textarea
              className="input min-h-48"
              value={importText}
              onChange={(event) => setImportText(event.target.value)}
              placeholder="Pega aqui un JSON exportado"
            />
            {importError ? <p className="text-sm font-semibold text-red-700">{importError}</p> : null}
            <button className="btn-secondary" type="button" onClick={importProject} disabled={!importText.trim()}>
              <FileUp className="h-4 w-4" />
              Importar proyecto
            </button>
          </div>
        </div>
      </section>

      <section className="surface p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-black">Historial y deshacer</h2>
          <div className="flex gap-2">
            <button className="btn-secondary" type="button" disabled={!canUndo} onClick={() => dispatch({ type: "undo" })}>
              <Undo2 className="h-4 w-4" />
              Deshacer
            </button>
            <button className="btn-secondary" type="button" disabled={!canRedo} onClick={() => dispatch({ type: "redo" })}>
              Rehacer
            </button>
          </div>
        </div>
        <div className="grid gap-2">
          {state.history.map((entry) => (
            <div key={entry.id} className="rounded-md border border-slate-200 p-3">
              <p className="font-semibold">{entry.message}</p>
              <p className="text-xs text-slate-500">{new Date(entry.createdAt).toLocaleString("es-ES")}</p>
            </div>
          ))}
          {state.history.length === 0 ? <p className="text-sm text-slate-500">Sin acciones registradas.</p> : null}
        </div>
      </section>
    </div>
  );
};
