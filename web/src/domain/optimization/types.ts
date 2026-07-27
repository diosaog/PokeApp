import type { BudgetConfig, CostBreakdown, EquippedItem, InventoryState } from "@/domain/economy/types";
import type { BreedingTarget, PokemonInstance, PokemonSex } from "@/domain/pokemon/types";
import type { ScheduleSummary } from "@/domain/scheduling/types";
import type { ServerProfile } from "@/rules/types";

export type SearchMode = "fast" | "precise";

export type OptimizationGoal = "balanced" | "cheapest" | "fastest";

export type OptimalityLabel =
  | "best_found"
  | "bounded_optimum"
  | "demonstrated_next_action";

export interface EngineWarning {
  code: string;
  message: string;
}

export interface BreedingAction {
  id: string;
  parentAId: string;
  parentBId: string;
  motherId?: string;
  fatherId?: string;
  offspringSpeciesId: string;
  sharedEggGroups: string[];
  items: EquippedItem[];
  forcedSex?: PokemonSex;
  cost: CostBreakdown;
  schedule: ScheduleSummary;
  directTargetProbability: number;
  usefulBreederProbability: number;
  expectedImprovement: number;
  expectedTotalCost: number;
  expectedTotalMinutes: number;
  score: number;
  warnings: EngineWarning[];
  explanation: string[];
  howCalculated: {
    inheritedStats: number;
    actionCount: number;
    statesExplored: number;
    simulations: number;
    seed: number;
    depth: number;
    elapsedMs: number;
  };
}

export interface OptimizationRequest {
  pokemon: PokemonInstance[];
  target: BreedingTarget;
  profile: ServerProfile;
  inventory: InventoryState;
  budget: BudgetConfig;
  searchMode: SearchMode;
  goal: OptimizationGoal;
  nowMinute: number;
  seed: number;
}

export interface OptimizationResult {
  recommendation: BreedingAction | null;
  alternatives: BreedingAction[];
  dominatedActions: BreedingAction[];
  optimality: OptimalityLabel;
  searchedExhaustively: boolean;
  warnings: EngineWarning[];
  elapsedMs: number;
  actionsEvaluated: number;
  statesExplored: number;
}
