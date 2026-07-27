import type { EngineWarning, OptimizationRequest, OptimizationResult } from "@/domain/optimization/types";
import { speciesById } from "@/data/species";
import { evaluatePairActions, splitDominatedActions } from "@/engine/optimizer/evaluate";

export type OptimizationProgress = (progress: { percent: number; message: string }) => void;

export const optimizeBreedingPlan = (
  request: OptimizationRequest,
  onProgress?: OptimizationProgress,
): OptimizationResult => {
  const started = performance.now();
  const warnings: EngineWarning[] = [];
  const actions = [];
  const totalPairs = Math.max(1, (request.pokemon.length * (request.pokemon.length - 1)) / 2);
  let evaluatedPairs = 0;
  const precise = request.searchMode === "precise";

  onProgress?.({ percent: 3, message: "Preparando parejas compatibles" });

  for (let indexA = 0; indexA < request.pokemon.length; indexA += 1) {
    const parentA = request.pokemon[indexA];
    if (!parentA) {
      continue;
    }

    for (let indexB = indexA + 1; indexB < request.pokemon.length; indexB += 1) {
      const parentB = request.pokemon[indexB];
      if (!parentB) {
        continue;
      }

      const pairActions = evaluatePairActions({
        parentA,
        parentB,
        speciesById,
        target: request.target,
        profile: request.profile,
        inventory: request.inventory,
        budget: request.budget,
        nowMinute: request.nowMinute,
        seed: request.seed + evaluatedPairs,
        precise,
        goal: request.goal,
      });
      actions.push(...pairActions);
      evaluatedPairs += 1;

      if (evaluatedPairs % 8 === 0) {
        onProgress?.({
          percent: Math.min(85, 5 + Math.round((evaluatedPairs / totalPairs) * 70)),
          message: "Evaluando objetos, sexo y probabilidades",
        });
      }
    }
  }

  if (request.profile.inheritance.powerItemMode === "unconfirmed") {
    warnings.push({
      code: "unconfirmed-power-items",
      message: "Los objetos recios se calculan con una regla configurable pendiente de confirmar.",
    });
  }

  onProgress?.({ percent: 88, message: "Eliminando acciones dominadas" });
  const { pareto, dominated } = splitDominatedActions(actions);
  const sorted = [...pareto].sort((a, b) => a.score - b.score);
  const recommendation = sorted[0] ?? null;
  const elapsedMs = Math.round(performance.now() - started);

  onProgress?.({ percent: 100, message: "Optimizacion completada" });

  return {
    recommendation: recommendation
      ? {
          ...recommendation,
          howCalculated: {
            ...recommendation.howCalculated,
            actionCount: actions.length,
            statesExplored: evaluatedPairs,
            elapsedMs,
          },
        }
      : null,
    alternatives: sorted.slice(1, 8),
    dominatedActions: dominated,
    optimality: precise ? "bounded_optimum" : "best_found",
    searchedExhaustively: false,
    warnings,
    elapsedMs,
    actionsEvaluated: actions.length,
    statesExplored: evaluatedPairs,
  };
};
