import { useEffect, useState } from "react";
import { Minus, Plus } from "lucide-react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { Card, CommandState, Loading, Notice, Submit, useCommand } from "../ui";

// Same bound as the server contract (WipeCount, 0..2^31-1).
const MAX_COUNT = 2147483647;
const blockingLabels = {
  participant_inactive:
    "Tu participación ya no está activa. El recuento se conserva para consulta.",
  season_inactive: "El recuento solo puede cambiar durante una Liga activa.",
  league_closed:
    "La última jornada ya está cerrada. El recuento y sus consecuencias oficiales se conservan.",
  membership_ineligible:
    "No tienes una plaza elegible en la jornada actual para cambiar este recuento.",
};

/**
 * The signed-in trainer's own live counter, under their licence card. The
 * server owns the value, its revision and every official consequence: − and
 * + only change a pending number that is sent with «Actualizar».
 */
export function WipeRevivals({ data }: { data: Model<"LeagueGeneralRead"> }) {
  const { me } = useApp();
  const own = data.rows.find((p) => p.trainer_id === me?.trainer_id);
  if (!own) return null;
  return (
    <OwnedWipeRevivals
      key={data.season.id}
      seasonId={data.season.id}
      dayId={data.season.current_matchday_id ?? null}
    />
  );
}

function OwnedWipeRevivals({
  seasonId,
  dayId,
}: {
  seasonId: string;
  dayId: string | null;
}) {
  const path = `/v1/seasons/${seasonId}/wipe-revivals`,
    query = useRead<Model<"WipeRevivalsRead">>(path),
    command = useCommand([
      path,
      `/v1/read/seasons/${seasonId}/league`,
      `/v1/seasons/${seasonId}/initial-assignment`,
      ...(dayId ? [`/v1/admin/seasons/${seasonId}/matchdays/${dayId}`] : []),
    ]),
    [reset, setReset] = useState(0);
  const conflict =
    command.error instanceof ApiError && command.error.status === 409
      ? command.error
      : null;
  // A rejected change goes back to the authoritative value.
  useEffect(() => {
    if (!conflict) return;
    setReset((value) => value + 1);
  }, [conflict]);
  if (query.isPending) return <Loading />;
  if (query.error) return <Notice error={query.error} />;
  const current = query.data;
  if (!current) return null;
  const busy = command.pending || command.uncertain || query.isFetching;
  return (
    <Card className="wipe-revivals">
      <h2>Revividos tras wipe</h2>
      {current.editable ? (
        <Stepper
          // A new authoritative value (after any confirmed or rejected
          // change) starts from the server's number again.
          key={`${current.revision}:${current.revived_after_wipe}:${reset}`}
          value={current.revived_after_wipe}
          busy={busy}
          pending={command.pending}
          onSubmit={(count) =>
            void command.execute(
              path,
              {
                revived_after_wipe: count,
                expected_revision: current.revision,
              } satisfies Model<"SetWipeRevivalsBody">,
              "PUT",
            )
          }
        />
      ) : (
        <p className="wipe-count">
          Cantidad: <strong>{current.revived_after_wipe}</strong>
        </p>
      )}
      {current.blocking_reason && (
        <p className="muted">{blockingLabels[current.blocking_reason]}</p>
      )}
      <CommandState command={command} />
    </Card>
  );
}

function Stepper({
  value,
  busy,
  pending,
  onSubmit,
}: {
  value: number;
  busy: boolean;
  pending: boolean;
  onSubmit: (count: number) => void;
}) {
  const [count, setCount] = useState(value);
  const valid = Number.isSafeInteger(count) && count >= 0 && count <= MAX_COUNT;
  const changed = count !== value;
  return (
    <form
      className="wipe-stepper"
      onSubmit={(event) => {
        event.preventDefault();
        if (busy || !valid || !changed) return;
        onSubmit(count);
      }}
    >
      <fieldset disabled={busy}>
        <legend className="sr-only">Revividos tras wipe</legend>
        <button
          type="button"
          className="icon-button"
          aria-label="Restar un revivido"
          disabled={count <= 0}
          onClick={() => setCount((n) => Math.max(0, n - 1))}
        >
          <Minus size={18} />
        </button>
        <output aria-live="polite" aria-label="Cantidad">
          {count}
        </output>
        <button
          type="button"
          className="icon-button"
          aria-label="Sumar un revivido"
          disabled={count >= MAX_COUNT}
          onClick={() => setCount((n) => Math.min(MAX_COUNT, n + 1))}
        >
          <Plus size={18} />
        </button>
        <Submit pending={pending} disabled={!valid || !changed}>
          Actualizar
        </Submit>
      </fieldset>
      {changed && <span className="caption">Sin guardar · antes: {value}</span>}
    </form>
  );
}
