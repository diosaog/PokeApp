import { Redo2, Undo2 } from "lucide-react";

import { routes } from "@/app/routes";
import { formatCurrency } from "@/components/common/format";
import { getSpeciesName } from "@/data/species";
import { BreedersPage } from "@/pages/BreedersPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { OptimizePage } from "@/pages/OptimizePage";
import { SetupPage } from "@/pages/SetupPage";
import { TargetPage } from "@/pages/TargetPage";
import { useSession } from "@/state/sessionStore";

const pageById = {
  setup: <SetupPage />,
  breeders: <BreedersPage />,
  target: <TargetPage />,
  optimize: <OptimizePage />,
  history: <HistoryPage />,
};

export const App = () => {
  const { state, dispatch, canUndo, canRedo } = useSession();

  return (
    <div className="app-shell">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-normal">Optimizador de crianzas Diosesmon</h1>
            <p className="text-sm text-slate-600">
              {state.pokemon.length} reproductores · objetivo {getSpeciesName(state.target.speciesId)} ·{" "}
              {state.budget.unlimited ? "presupuesto ilimitado" : formatCurrency(state.budget.money)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary h-10 w-10 px-0" type="button" disabled={!canUndo} onClick={() => dispatch({ type: "undo" })} title="Deshacer">
              <Undo2 className="h-4 w-4" />
            </button>
            <button className="btn-secondary h-10 w-10 px-0" type="button" disabled={!canRedo} onClick={() => dispatch({ type: "redo" })} title="Rehacer">
              <Redo2 className="h-4 w-4" />
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 pb-3">
          {routes.map((route) => {
            const Icon = route.icon;
            const active = route.id === state.activePage;
            return (
              <button
                key={route.id}
                className={active ? "btn-primary shrink-0" : "btn-secondary shrink-0"}
                type="button"
                onClick={() => dispatch({ type: "set-page", page: route.id })}
              >
                <Icon className="h-4 w-4" />
                {route.label}
              </button>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">{pageById[state.activePage]}</main>
    </div>
  );
};
