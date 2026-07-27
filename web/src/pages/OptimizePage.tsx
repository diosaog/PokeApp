import { Ban, FlaskConical, Play, RotateCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { SpeciesSelect } from "@/components/common/SpeciesSelect";
import { StatGrid } from "@/components/common/StatGrid";
import { formatCurrency, formatProbability } from "@/components/common/format";
import { RecommendationPanel } from "@/components/optimizer/RecommendationPanel";
import { getSpeciesName } from "@/data/species";
import type { OptimizationResult } from "@/domain/optimization/types";
import type { IvSpread, PokemonInstance, PokemonSex } from "@/domain/pokemon/types";
import { blankIvs, sexLabels } from "@/domain/pokemon/types";
import { createId } from "@/utils/ids";
import { useSession } from "@/state/sessionStore";
import { useOptimizerWorker } from "@/workers/useOptimizerWorker";

const optimalityText = {
  best_found: "Mejor estrategia encontrada",
  bounded_optimum: "Optima dentro de los limites de busqueda",
  demonstrated_next_action: "Optimo demostrado para el siguiente intento",
};

export const OptimizePage = () => {
  const { state, dispatch } = useSession();
  const [eggSpeciesId, setEggSpeciesId] = useState(state.target.speciesId);
  const [eggSex, setEggSex] = useState<PokemonSex>("unknown");
  const [eggIvs, setEggIvs] = useState<IvSpread>(() => blankIvs());
  const [eggNickname, setEggNickname] = useState("");
  const recommendation = state.optimizationResult?.recommendation ?? null;

  const onResult = useCallback(
    (result: OptimizationResult) => {
      dispatch({ type: "set-optimization-result", result });
      if (result.recommendation) {
        setEggSpeciesId(result.recommendation.offspringSpeciesId);
        setEggSex(result.recommendation.forcedSex ?? "unknown");
      }
    },
    [dispatch],
  );
  const optimizer = useOptimizerWorker(onResult);

  const request = useMemo(
    () => ({
      pokemon: state.pokemon,
      target: state.target,
      profile: state.profile,
      inventory: state.inventory,
      budget: state.budget,
      searchMode: state.searchMode,
      goal: state.optimizationGoal,
      nowMinute: 0,
      seed: 20260727,
    }),
    [state.budget, state.inventory, state.optimizationGoal, state.pokemon, state.profile, state.searchMode, state.target],
  );

  const canRun = state.pokemon.length >= 2 && !optimizer.running;

  const registerEgg = (): void => {
    if (!recommendation) {
      return;
    }

    const egg: PokemonInstance = {
      id: createId("egg"),
      speciesId: eggSpeciesId,
      sex: eggSex,
      ivs: eggIvs,
      canBreed: true,
      availableAtMinute: 0,
      protected: false,
    };
    if (eggNickname.trim()) {
      egg.nickname = eggNickname.trim();
    }
    dispatch({ type: "record-egg", action: recommendation, egg });
    setEggIvs(blankIvs());
    setEggNickname("");
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
      <section className="surface p-4 xl:col-span-2">
        <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
          <div>
            <h2 className="text-lg font-black">Optimizacion</h2>
            <p className="text-sm text-slate-600">
              {state.pokemon.length} reproductores · objetivo {getSpeciesName(state.target.speciesId)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              className="input w-auto"
              value={state.searchMode}
              onChange={(event) =>
                dispatch({ type: "set-search-mode", searchMode: event.target.value === "precise" ? "precise" : "fast" })
              }
            >
              <option value="fast">Busqueda rapida</option>
              <option value="precise">Busqueda precisa</option>
            </select>
            <select
              className="input w-auto"
              value={state.optimizationGoal}
              onChange={(event) => {
                const value = event.target.value;
                dispatch({
                  type: "set-optimization-goal",
                  goal: value === "cheapest" || value === "fastest" ? value : "balanced",
                });
              }}
            >
              <option value="balanced">Equilibrio</option>
              <option value="cheapest">Mas barato</option>
              <option value="fastest">Mas rapido</option>
            </select>
            <button className="btn-primary" type="button" disabled={!canRun} onClick={() => optimizer.run(request)}>
              <Play className="h-4 w-4" />
              Ejecutar
            </button>
            <button className="btn-secondary" type="button" disabled={!optimizer.running} onClick={optimizer.cancel}>
              <Ban className="h-4 w-4" />
              Cancelar
            </button>
          </div>
        </div>

        {optimizer.running || optimizer.progress > 0 ? (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-sm">
              <span>{optimizer.message}</span>
              <span className="font-bold">{optimizer.progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-200">
              <div className="h-2 rounded-full bg-moss" style={{ width: `${optimizer.progress}%` }} />
            </div>
          </div>
        ) : null}

        {optimizer.error ? (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800">
            {optimizer.error}
          </div>
        ) : null}
      </section>

      {state.optimizationResult ? (
        <section className="surface p-4 xl:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="label">Resultado</p>
              <h3 className="text-xl font-black">{optimalityText[state.optimizationResult.optimality]}</h3>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="badge border-slate-200 bg-white">
                Acciones: {state.optimizationResult.actionsEvaluated}
              </span>
              <span className="badge border-slate-200 bg-white">
                Estados: {state.optimizationResult.statesExplored}
              </span>
              <span className="badge border-slate-200 bg-white">{state.optimizationResult.elapsedMs} ms</span>
            </div>
          </div>
          {state.optimizationResult.warnings.length > 0 ? (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              {state.optimizationResult.warnings.map((warning) => (
                <p key={`${warning.code}-${warning.message}`}>{warning.message}</p>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {recommendation ? (
        <RecommendationPanel action={recommendation} pokemon={state.pokemon} />
      ) : (
        <section className="surface p-6 text-center xl:col-span-2">
          <FlaskConical className="mx-auto h-10 w-10 text-slate-400" />
          <h2 className="mt-2 text-lg font-black">Sin recomendacion calculada</h2>
          <p className="text-sm text-slate-600">
            Necesitas al menos dos reproductores viables y un objetivo definido.
          </p>
        </section>
      )}

      <aside className="surface p-4">
        <div className="mb-3 flex items-center gap-2">
          <RotateCw className="h-5 w-5 text-moss" />
          <h2 className="text-lg font-black">Registrar cria</h2>
        </div>
        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className="label">Mote</span>
            <input className="input" value={eggNickname} onChange={(event) => setEggNickname(event.target.value)} />
          </label>
          <SpeciesSelect label="Especie nacida" value={eggSpeciesId} onChange={setEggSpeciesId} />
          <label className="grid gap-1">
            <span className="label">Sexo real</span>
            <select
              className="input"
              data-testid="egg-sex"
              value={eggSex}
              onChange={(event) => setEggSex(event.target.value as PokemonSex)}
            >
              {Object.entries(sexLabels).map(([sex, label]) => (
                <option key={sex} value={sex}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <StatGrid value={eggIvs} onChange={setEggIvs} />
          <button className="btn-primary" type="button" disabled={!recommendation} onClick={registerEgg}>
            Registrar y recalcular luego
          </button>
        </div>
      </aside>

      <section className="surface p-4">
        <h2 className="mb-3 text-lg font-black">Alternativas</h2>
        <div className="grid gap-2">
          {state.optimizationResult?.alternatives.map((alternative) => (
            <div key={alternative.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold">{getSpeciesName(alternative.offspringSpeciesId)}</p>
                <span className="font-black">{formatCurrency(alternative.expectedTotalCost)}</span>
              </div>
              <p className="text-slate-600">
                Objetivo {formatProbability(alternative.directTargetProbability)} · util{" "}
                {formatProbability(alternative.usefulBreederProbability)}
              </p>
            </div>
          ))}
          {state.optimizationResult && state.optimizationResult.alternatives.length === 0 ? (
            <p className="text-sm text-slate-500">No hay alternativas no dominadas.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
};
