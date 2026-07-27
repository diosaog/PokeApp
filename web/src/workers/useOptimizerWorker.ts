import { useCallback, useRef, useState } from "react";

import type { OptimizationRequest, OptimizationResult } from "@/domain/optimization/types";

type WorkerResponse =
  | { type: "progress"; percent: number; message: string }
  | { type: "result"; result: OptimizationResult }
  | { type: "error"; message: string };

export interface OptimizerWorkerState {
  running: boolean;
  progress: number;
  message: string;
  error: string | null;
}

export const useOptimizerWorker = (onResult: (result: OptimizationResult) => void) => {
  const workerRef = useRef<Worker | null>(null);
  const [state, setState] = useState<OptimizerWorkerState>({
    running: false,
    progress: 0,
    message: "Listo",
    error: null,
  });

  const cancel = useCallback(() => {
    workerRef.current?.terminate();
    workerRef.current = null;
    setState({
      running: false,
      progress: 0,
      message: "Optimizacion cancelada",
      error: null,
    });
  }, []);

  const run = useCallback(
    (request: OptimizationRequest) => {
      workerRef.current?.terminate();
      const worker = new Worker(new URL("./optimizer.worker.ts", import.meta.url), { type: "module" });
      workerRef.current = worker;
      setState({
        running: true,
        progress: 0,
        message: "Iniciando optimizacion",
        error: null,
      });

      worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
        const response = event.data;
        if (response.type === "progress") {
          setState((current) => ({
            ...current,
            progress: response.percent,
            message: response.message,
          }));
          return;
        }

        if (response.type === "result") {
          worker.terminate();
          workerRef.current = null;
          onResult(response.result);
          setState({
            running: false,
            progress: 100,
            message: "Optimizacion completada",
            error: null,
          });
          return;
        }

        worker.terminate();
        workerRef.current = null;
        setState({
          running: false,
          progress: 0,
          message: "Error de optimizacion",
          error: response.message,
        });
      };

      worker.postMessage({ type: "optimize", request });
    },
    [onResult],
  );

  return { ...state, run, cancel };
};
