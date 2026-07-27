import React, { createContext, useContext, useMemo, useReducer } from "react";

import { createDefaultInventory } from "@/domain/economy/items";
import type { BudgetConfig, InventoryEntry, InventoryState } from "@/domain/economy/types";
import type { BreedingAction, OptimizationGoal, OptimizationResult, SearchMode } from "@/domain/optimization/types";
import type { BreedingTarget, IvConstraint, PokemonInstance, StatKey } from "@/domain/pokemon/types";
import { blankIvs, defaultTargetIvs } from "@/domain/pokemon/types";
import { applyPaidAttempt, calculateAttemptCost } from "@/engine/economy/costs";
import { diosesmonProfile } from "@/rules/diosesmon/profile";
import type { ServerProfile } from "@/rules/types";
import { parseProjectDocument, type ProjectDocument } from "@/schemas/projectSchema";
import { createId } from "@/utils/ids";

export type ActivePage = "setup" | "breeders" | "target" | "optimize" | "history";

export interface HistoryEntry {
  id: string;
  message: string;
  createdAt: string;
}

export interface AppState {
  activePage: ActivePage;
  profile: ServerProfile;
  budget: BudgetConfig;
  inventory: InventoryState;
  pokemon: PokemonInstance[];
  target: BreedingTarget;
  searchMode: SearchMode;
  optimizationGoal: OptimizationGoal;
  optimizationResult: OptimizationResult | null;
  history: HistoryEntry[];
  cooldownConfirmation: "unanswered" | "si_60" | "none" | "custom" | "unknown";
}

export interface HistoryState {
  present: AppState;
  undoStack: AppState[];
  redoStack: AppState[];
}

type SessionAction =
  | { type: "set-page"; page: ActivePage }
  | { type: "set-budget"; budget: BudgetConfig }
  | { type: "set-economy"; economy: ServerProfile["economy"] }
  | { type: "set-time"; time: ServerProfile["time"] }
  | { type: "set-inventory-entry"; itemId: keyof InventoryState; entry: InventoryEntry }
  | { type: "add-pokemon"; pokemon: PokemonInstance }
  | { type: "update-pokemon"; pokemon: PokemonInstance }
  | { type: "delete-pokemon"; id: string }
  | { type: "duplicate-pokemon"; id: string }
  | { type: "toggle-protected"; id: string }
  | { type: "set-target-species"; speciesId: string }
  | { type: "set-target-sex"; sex: BreedingTarget["sex"] }
  | { type: "set-target-constraint"; stat: StatKey; constraint: IvConstraint }
  | { type: "set-search-mode"; searchMode: SearchMode }
  | { type: "set-optimization-goal"; goal: OptimizationGoal }
  | { type: "set-optimization-result"; result: OptimizationResult | null }
  | { type: "record-egg"; action: BreedingAction; egg: PokemonInstance }
  | { type: "load-demo"; pokemon: PokemonInstance[] }
  | { type: "import-project"; document: ProjectDocument }
  | { type: "set-cooldown-confirmation"; value: AppState["cooldownConfirmation"]; customMinutes?: number }
  | { type: "undo" }
  | { type: "redo" };

export const createInitialState = (): AppState => ({
  activePage: "setup",
  profile: diosesmonProfile,
  budget: {
    unlimited: false,
    money: 50_000,
    metric: "replacement",
  },
  inventory: createDefaultInventory(diosesmonProfile.economy.defaultItemPrice),
  pokemon: [],
  target: {
    speciesId: "eevee",
    ivs: defaultTargetIvs(),
    sex: "any",
  },
  searchMode: "fast",
  optimizationGoal: "balanced",
  optimizationResult: null,
  history: [],
  cooldownConfirmation: "unanswered",
});

export const createPokemonDraft = (): PokemonInstance => ({
  id: createId("pkm"),
  speciesId: "eevee",
  sex: "unknown",
  ivs: blankIvs(),
  canBreed: true,
  availableAtMinute: 0,
  protected: false,
});

const pushHistory = (state: AppState, message: string): AppState => ({
  ...state,
  history: [
    {
      id: createId("hist"),
      message,
      createdAt: new Date().toISOString(),
    },
    ...state.history,
  ].slice(0, 100),
});

const withUndo = (state: HistoryState, next: AppState): HistoryState => ({
  present: next,
  undoStack: [state.present, ...state.undoStack].slice(0, 50),
  redoStack: [],
});

const replacePresent = (state: HistoryState, present: AppState): HistoryState => ({
  ...state,
  present,
});

const reducer = (state: HistoryState, action: SessionAction): HistoryState => {
  switch (action.type) {
    case "set-page":
      return replacePresent(state, { ...state.present, activePage: action.page });
    case "set-search-mode":
      return replacePresent(state, { ...state.present, searchMode: action.searchMode });
    case "set-optimization-goal":
      return replacePresent(state, { ...state.present, optimizationGoal: action.goal });
    case "set-optimization-result":
      return replacePresent(state, { ...state.present, optimizationResult: action.result });
    case "set-budget":
      return withUndo(state, pushHistory({ ...state.present, budget: action.budget }, "Presupuesto actualizado."));
    case "set-economy":
      return withUndo(
        state,
        pushHistory(
          { ...state.present, profile: { ...state.present.profile, economy: action.economy } },
          "Economia del perfil actualizada.",
        ),
      );
    case "set-time":
      return withUndo(
        state,
        pushHistory(
          { ...state.present, profile: { ...state.present.profile, time: action.time } },
          "Configuracion temporal actualizada.",
        ),
      );
    case "set-inventory-entry":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            inventory: {
              ...state.present.inventory,
              [action.itemId]: action.entry,
            },
          },
          "Inventario actualizado.",
        ),
      );
    case "add-pokemon":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            pokemon: [...state.present.pokemon, action.pokemon],
          },
          `Pokemon anadido: ${action.pokemon.nickname || action.pokemon.speciesId}.`,
        ),
      );
    case "update-pokemon":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            pokemon: state.present.pokemon.map((pokemon) =>
              pokemon.id === action.pokemon.id ? action.pokemon : pokemon,
            ),
          },
          `Pokemon editado: ${action.pokemon.nickname || action.pokemon.speciesId}.`,
        ),
      );
    case "delete-pokemon":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            pokemon: state.present.pokemon.filter((pokemon) => pokemon.id !== action.id),
          },
          "Pokemon eliminado.",
        ),
      );
    case "duplicate-pokemon": {
      const source = state.present.pokemon.find((pokemon) => pokemon.id === action.id);
      if (!source) {
        return state;
      }
      const duplicate: PokemonInstance = {
        ...source,
        id: createId("pkm"),
      };
      if (source.nickname) {
        duplicate.nickname = `${source.nickname} copia`;
      }
      return withUndo(
        state,
        pushHistory({ ...state.present, pokemon: [...state.present.pokemon, duplicate] }, "Pokemon duplicado."),
      );
    }
    case "toggle-protected":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            pokemon: state.present.pokemon.map((pokemon) =>
              pokemon.id === action.id ? { ...pokemon, protected: !pokemon.protected } : pokemon,
            ),
          },
          "Proteccion cambiada.",
        ),
      );
    case "set-target-species":
      return withUndo(
        state,
        pushHistory(
          { ...state.present, target: { ...state.present.target, speciesId: action.speciesId } },
          "Especie objetivo actualizada.",
        ),
      );
    case "set-target-sex":
      return withUndo(
        state,
        pushHistory({ ...state.present, target: { ...state.present.target, sex: action.sex } }, "Sexo objetivo actualizado."),
      );
    case "set-target-constraint":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            target: {
              ...state.present.target,
              ivs: {
                ...state.present.target.ivs,
                [action.stat]: action.constraint,
              },
            },
          },
          "Objetivo de IV actualizado.",
        ),
      );
    case "record-egg": {
      const cost = calculateAttemptCost({
        economy: state.present.profile.economy,
        inventory: state.present.inventory,
        budget: state.present.budget,
        items: action.action.items,
        forceSex: action.action.forcedSex !== undefined,
      });
      if (!cost.ok) {
        return state;
      }
      const paid = applyPaidAttempt(state.present.budget.money, state.present.budget.unlimited, cost);
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            budget: { ...state.present.budget, money: Math.max(0, paid.money) },
            inventory: paid.inventory,
            pokemon: [...state.present.pokemon, action.egg],
            optimizationResult: null,
          },
          `Huevo registrado: ${action.egg.nickname || action.egg.speciesId}.`,
        ),
      );
    }
    case "load-demo":
      return withUndo(
        state,
        pushHistory({ ...state.present, pokemon: action.pokemon, activePage: "breeders" }, "Ejemplo motivador cargado."),
      );
    case "import-project":
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            profile: {
              ...state.present.profile,
              economy: action.document.economy,
              time: action.document.time,
            },
            budget: action.document.budget,
            inventory: action.document.inventory as InventoryState,
            target: action.document.target as BreedingTarget,
            pokemon: action.document.pokemon as PokemonInstance[],
            optimizationResult: null,
            activePage: "optimize",
          },
          "Proyecto importado manualmente.",
        ),
      );
    case "set-cooldown-confirmation": {
      const customMinutes = action.customMinutes ?? state.present.profile.time.parentCooldownMinutes;
      const time =
        action.value === "si_60"
          ? { ...state.present.profile.time, parentReuseMode: "cooldown" as const, parentCooldownMinutes: 60 }
          : action.value === "none"
            ? { ...state.present.profile.time, parentReuseMode: "immediate" as const, parentCooldownMinutes: 0 }
            : action.value === "custom"
              ? { ...state.present.profile.time, parentReuseMode: "cooldown" as const, parentCooldownMinutes: customMinutes }
              : state.present.profile.time;
      return withUndo(
        state,
        pushHistory(
          {
            ...state.present,
            profile: { ...state.present.profile, time },
            cooldownConfirmation: action.value,
          },
          "Confirmacion de enfriamiento actualizada.",
        ),
      );
    }
    case "undo": {
      const previous = state.undoStack[0];
      if (!previous) {
        return state;
      }
      return {
        present: previous,
        undoStack: state.undoStack.slice(1),
        redoStack: [state.present, ...state.redoStack],
      };
    }
    case "redo": {
      const next = state.redoStack[0];
      if (!next) {
        return state;
      }
      return {
        present: next,
        undoStack: [state.present, ...state.undoStack],
        redoStack: state.redoStack.slice(1),
      };
    }
  }
};

export const sessionReducerForTests = reducer;

export const createInitialHistoryStateForTests = (): HistoryState => ({
  present: createInitialState(),
  undoStack: [],
  redoStack: [],
});

interface SessionContextValue {
  state: AppState;
  canUndo: boolean;
  canRedo: boolean;
  dispatch: React.Dispatch<SessionAction>;
  exportProject: () => ProjectDocument;
  importProjectFromJson: (json: string) => ProjectDocument;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export const SessionProvider = ({ children }: { children: React.ReactNode }) => {
  const [historyState, dispatch] = useReducer(reducer, {
    present: createInitialState(),
    undoStack: [],
    redoStack: [],
  });

  const value = useMemo<SessionContextValue>(() => {
    const exportProject = (): ProjectDocument => ({
      schemaVersion: 1,
      exportedAt: new Date().toISOString(),
      profileId: historyState.present.profile.id,
      budget: historyState.present.budget,
      economy: historyState.present.profile.economy,
      time: historyState.present.profile.time,
      inventory: historyState.present.inventory,
      target: historyState.present.target,
      pokemon: historyState.present.pokemon,
      history: historyState.present.history.map((entry) => entry.message),
    });

    const importProjectFromJson = (json: string): ProjectDocument => parseProjectDocument(JSON.parse(json) as unknown);

    return {
      state: historyState.present,
      canUndo: historyState.undoStack.length > 0,
      canRedo: historyState.redoStack.length > 0,
      dispatch,
      exportProject,
      importProjectFromJson,
    };
  }, [historyState]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

export const useSession = (): SessionContextValue => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession debe usarse dentro de SessionProvider.");
  }
  return context;
};
