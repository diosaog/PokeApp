import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Field,
  Loading,
  Notice,
  Submit,
  form,
  text,
  useCommand,
} from "../ui";

const blockingLabels = {
  participant_inactive:
    "Tu participación ya no está activa. El recuento se conserva para consulta.",
  season_inactive: "El recuento solo puede cambiar durante una Liga activa.",
  league_closed:
    "La última jornada ya está cerrada. El recuento y sus consecuencias oficiales se conservan.",
  membership_ineligible:
    "No tienes una plaza elegible en la jornada actual para cambiar este recuento.",
};

/** A personal live counter; totals and sporting history remain server-controlled. */
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
  useEffect(() => {
    if (!conflict) return;
    setReset((value) => value + 1);
  }, [conflict]);
  if (query.isPending) return <Loading />;
  if (query.error) return <Notice error={query.error} />;
  const current = query.data;
  if (!current) return null;
  const disabled =
    command.pending ||
    command.uncertain ||
    query.isFetching ||
    !current.editable;
  return (
    <Card className="wipe-revivals">
      <h2>Revividos tras wipe</h2>
      {!current.editable && (
        <p>
          Cantidad: <strong>{current.revived_after_wipe}</strong>
        </p>
      )}
      {current.blocking_reason && (
        <p className="muted">{blockingLabels[current.blocking_reason]}</p>
      )}
      {current.editable && (
        <form
          key={`${current.revision}:${reset}`}
          onSubmit={(event) => {
            const values = form(event),
              raw = text(values, "revived_after_wipe");
            if (disabled || !/^[0-9]+$/.test(raw)) return;
            const count = Number(raw);
            if (!Number.isSafeInteger(count) || count < 0 || count > 2147483647)
              return;
            void command.execute(
              path,
              {
                revived_after_wipe: count,
                expected_revision: current.revision,
              } satisfies Model<"SetWipeRevivalsBody">,
              "PUT",
            );
          }}
        >
          <fieldset disabled={disabled}>
            <Field label="Cantidad">
              <input
                name="revived_after_wipe"
                type="number"
                inputMode="numeric"
                min={0}
                max={2147483647}
                step={1}
                required
                defaultValue={current.revived_after_wipe}
              />
            </Field>
            <Submit pending={command.pending} disabled={disabled}>
              Actualizar
            </Submit>
          </fieldset>
        </form>
      )}
      <CommandState command={command} />
    </Card>
  );
}
