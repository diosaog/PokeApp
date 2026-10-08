import { useState, useEffect } from "react";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { Card, CommandState, Modal, Notice, useCommand } from "../ui";
import { ChampionshipReview } from "./championship";

export function LeagueOperations({
  data,
}: {
  data: Model<"LeagueGeneralRead">;
}) {
  const { me } = useApp(),
    day = data.days.find((d) => d.id === data.season.current_matchday_id);
  const eligible =
    data.season.status === "active" &&
    data.rows.some(
      (p) => p.trainer_id === me?.trainer_id && p.status === "active",
    );
  const [review, setReview] = useState(false);
  useEffect(() => {
    if (eligible && day?.status === "closed") setReview(true);
  }, [eligible, day?.status]);
  return (
    <>
      <DayOperations season={data.season.id} day={day} eligible={eligible} />
      {review && (
        <ChampionshipReview participant seasonName={data.season.name} />
      )}
    </>
  );
}
function DayOperations({
  season,
  day,
  eligible,
}: {
  season: string;
  day?: Model<"DayRead">;
  eligible: boolean;
}) {
  const base = `/v1/seasons/${season}/matchdays/${day?.id}`,
    query = useRead<Model<"DayState">>(
      base,
      eligible && !!day && day.status !== "closed",
    );
  const cmd = useCommand(),
    { holdAdminNavigation } = useApp();
  const [intent, setIntent] = useState<{
    op: "open" | "close";
    revision: number;
    base: string;
  } | null>(null);
  useEffect(() => {
    if ((cmd.pending || cmd.uncertain) && holdAdminNavigation)
      return holdAdminNavigation();
  }, [cmd.pending, cmd.uncertain, holdAdminNavigation]);
  const state = query.data,
    op =
      !eligible || day?.status === "closed"
        ? null
        : state?.state === "scheduled"
          ? "open"
          : state?.state === "open"
            ? "close"
            : null;
  const revision = op === "open" ? state?.revision : state?.results_revision;
  const stale =
    intent &&
    (intent.op !== op || intent.revision !== revision || intent.base !== base);
  const busy = cmd.pending || cmd.uncertain || query.isFetching;
  const label = op === "open" ? "Abrir jornada" : "Cerrar jornada";
  if (!eligible && !intent && !cmd.uncertain) return null;
  return (
    <Card>
      <h2>Jornada {day?.number}</h2>
      <Notice error={query.error} />
      {op && (
        <button
          className="button"
          disabled={busy}
          onClick={() => setIntent({ op, revision: revision!, base })}
        >
          {label}
        </button>
      )}
      {!intent && <CommandState command={cmd} />}
      {intent && (
        <Modal
          title={intent.op === "open" ? "Abrir jornada" : "Cerrar jornada"}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setIntent(null);
          }}
        >
          <p>
            {intent.op === "open"
              ? "Los participantes podrán registrar los combates de esta jornada."
              : "Se guardará la clasificación oficial y se concederán sus premios."}
          </p>
          {stale && (
            <p role="alert">
              La jornada cambió. Revisa su estado antes de confirmar.
            </p>
          )}
          <button
            className="button primary"
            disabled={busy || !!stale}
            onClick={async () => {
              if (
                await cmd.execute(
                  `${intent.base}/${intent.op}`,
                  intent.op === "open"
                    ? { expected_revision: intent.revision }
                    : { expected_results_revision: intent.revision },
                )
              )
                setIntent(null);
            }}
          >
            Confirmar
          </button>
          <CommandState command={cmd} />
        </Modal>
      )}
    </Card>
  );
}
