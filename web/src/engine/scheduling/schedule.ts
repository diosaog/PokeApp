import type { PokemonInstance } from "@/domain/pokemon/types";
import type { ScheduleSummary, TimeConfig } from "@/domain/scheduling/types";

export const estimateSingleAttemptSchedule = (
  time: TimeConfig,
  parentA: PokemonInstance,
  parentB: PokemonInstance,
  nowMinute: number,
): ScheduleSummary => {
  const slots = Math.max(1, time.breedingSlots);
  const waitingMinutes = Math.max(0, parentA.availableAtMinute - nowMinute, parentB.availableAtMinute - nowMinute);
  const workMinutes = time.breedingDurationMinutes;
  const cooldownDelay =
    time.parentReuseMode === "cooldown" && time.cooldownStartsAt === "breeding_start"
      ? Math.max(0, time.parentCooldownMinutes - time.breedingDurationMinutes)
      : 0;
  const clockMinutes = waitingMinutes + workMinutes + cooldownDelay;
  const slotUtilization = clockMinutes === 0 ? 1 : Math.min(1, workMinutes / (clockMinutes * slots));
  const warnings: string[] = [];

  if (time.parentReuseMode === "cooldown" && time.parentCooldownMinutes > 0) {
    warnings.push("El tiempo incluye el modo de enfriamiento configurado, pero no demuestra una cola multigeneracional completa.");
  }

  if (time.parentReuseMode === "single_use") {
    warnings.push("El perfil marca progenitores de un solo uso; el siguiente intento consume su disponibilidad futura.");
  }

  return {
    workMinutes,
    clockMinutes,
    waitingMinutes,
    eggCount: 1,
    rounds: 1,
    slotUtilization,
    warnings,
  };
};
