import type { OptimizationRequest, OptimizationResult } from "@/domain/optimization/types";
import { optimizeBreedingPlan } from "@/engine/optimizer/optimizer";

type WorkerRequest = {
  type: "optimize";
  request: OptimizationRequest;
};

type WorkerResponse =
  | { type: "progress"; percent: number; message: string }
  | { type: "result"; result: OptimizationResult }
  | { type: "error"; message: string };

const post = (message: WorkerResponse): void => {
  self.postMessage(message);
};

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  if (event.data.type !== "optimize") {
    return;
  }

  try {
    const result = optimizeBreedingPlan(event.data.request, (progress) => {
      post({ type: "progress", percent: progress.percent, message: progress.message });
    });
    post({ type: "result", result });
  } catch (error) {
    post({ type: "error", message: error instanceof Error ? error.message : "Error desconocido." });
  }
};
