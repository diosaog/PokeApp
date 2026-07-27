export type ParentReuseMode = "immediate" | "cooldown" | "single_use";

export interface TimeConfig {
  breedingSlots: number;
  breedingDurationMinutes: number;
  parentReuseMode: ParentReuseMode;
  parentCooldownMinutes: number;
  cooldownStartsAt: "breeding_start" | "breeding_end";
}

export interface ScheduleSummary {
  workMinutes: number;
  clockMinutes: number;
  waitingMinutes: number;
  eggCount: number;
  rounds: number;
  slotUtilization: number;
  warnings: string[];
}
