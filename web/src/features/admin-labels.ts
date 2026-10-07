const seasonLabels: Record<string, string> = {
  draft: "Borrador",
  active: "En curso",
  finished: "Liga finalizada",
  archived: "Archivada",
  discarded: "Descartada",
};
const participantLabels: Record<string, string> = {
  active: "Activo",
  retired: "Retirado",
  abandoned: "Abandono registrado",
  disqualified: "Descalificado de la Liga",
};
const dayLabels: Record<string, string> = {
  scheduled: "Preparada",
  open: "En juego",
  closed: "Cerrada",
  cancelled: "Cancelada",
};

export const seasonLabel = (value: string) =>
  seasonLabels[value] ?? "Estado pendiente de consultar";
export const participantLabel = (value: string) =>
  participantLabels[value] ?? "Estado pendiente de consultar";
export const dayLabel = (value: string) =>
  dayLabels[value] ?? "Estado pendiente de consultar";

const readinessLabels: Record<string, string> = {
  has_roster: "Añade participantes a la Liga.",
  has_valid_config: "Guarda una configuración válida para la plantilla actual.",
  has_initial_divisions: "Prepara las divisiones iniciales.",
  memberships_complete:
    "Completa el reparto de participantes entre las divisiones.",
  first_matchday_prepared: "Prepara la primera jornada.",
  match_pairs_complete: "Revisa los enfrentamientos de la primera jornada.",
  pointer_valid: "La jornada actual necesita revisión antes de continuar.",
  no_other_active_season:
    "Ya hay otra Liga en curso. Debe finalizar antes de activar esta.",
  is_draft: "La temporada ya ha salido de la preparación inicial.",
  initial_assignment_pending:
    "El reparto inicial ya está registrado; consulta la competición.",
};
export const readinessLabel = (value: string) =>
  readinessLabels[value] ??
  "Hay una condición de preparación pendiente. Actualiza los datos y revisa la temporada.";
