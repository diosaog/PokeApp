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
  Tag,
  form,
  text,
  useCommand,
} from "../ui";

type Assignment = Model<"InitialAssignmentRead">;
const blockingLabels: Record<string, string> = {
  season_not_active:
    "La temporada debe estar activa para confirmar el reparto.",
  invalid_roster:
    "La plantilla debe coincidir con las capacidades configuradas.",
  config_not_effective: "Falta una configuración válida para el primer tramo.",
  progress_unobserved:
    "Hay progreso no observado / pendiente de sincronizar save.",
  death_inputs_unobserved:
    "Falta una observación completa de las muertes competitivas ajustadas.",
  cap_not_reached:
    "Todos los participantes requeridos deben alcanzar la Medalla 2.",
  initial_assignment_locked:
    "El estado actual de la temporada impide modificar el reparto.",
};

function BoundaryFields({ data }: { data: Assignment }) {
  const tie = data.boundary_tie!;
  const [selected, setSelected] = useState<string[]>(
    tie.player_ids.map(() => ""),
  );
  return (
    <section aria-label="Empate en el corte A/B">
      <h3>Empate en el corte A/B</h3>
      <p>
        {tie.player_ids.length} participantes comparten {tie.adjusted_deaths}{" "}
        muertes ajustadas; quedan {tie.places_in_a} plazas en A. Registra el
        orden acordado externamente y su motivo. El orden de los nombres en
        estas listas no decide el reparto.
      </p>
      {selected.map((value, index) => (
        <Field key={index} label={`Orden del empate · puesto ${index + 1}`}>
          <select
            name={`boundary-${index}`}
            required
            value={value}
            onChange={(event) =>
              setSelected(
                selected.map((old, i) =>
                  i === index ? event.target.value : old,
                ),
              )
            }
          >
            <option value="">Seleccionar según la decisión externa</option>
            {tie.player_ids.map((id) => (
              <option
                key={id}
                value={id}
                disabled={selected.some(
                  (chosen, i) => chosen === id && i !== index,
                )}
              >
                {data.players.find((p) => p.id === id)?.display_name}
              </option>
            ))}
          </select>
        </Field>
      ))}
      <Field label="Motivo de la decisión externa">
        <textarea name="boundary-reason" required maxLength={500} />
      </Field>
    </section>
  );
}

/** One aggregate read. Save observations alone establish progress readiness. */
export function InitialAssignment({
  administrative = false,
}: {
  administrative?: boolean;
}) {
  const { season, me } = useApp(),
    path = `/v1/seasons/${season}/initial-assignment`,
    query = useRead<Assignment>(path, !!season),
    command = useCommand(),
    [reset, setReset] = useState(0);
  const conflict =
    command.error instanceof ApiError && command.error.status === 409
      ? command.error
      : null;
  const refetch = query.refetch;
  useEffect(() => {
    if (!conflict) return;
    setReset((value) => value + 1);
    void refetch();
  }, [conflict, refetch]);
  if (query.isPending) return <Loading />;
  if (query.error) return <Notice error={query.error} />;
  const data = query.data;
  if (!data || data.state === "legacy") return null;
  const admin = administrative && me?.is_admin;
  const disabled = command.pending || command.uncertain || query.isFetching;
  return (
    <Card>
      <h2>Reparto inicial A/B</h2>
      <p>
        El primer tramo termina en la Medalla 2 inclusive. El progreso se
        obtiene leyendo el save; cuando todos alcancen el objetivo observado,
        las menores muertes competitivas ajustadas determinan el reparto.
      </p>
      <Tag>
        {data.state === "assigned"
          ? "Reparto registrado"
          : !data.ready
            ? "Preparación pendiente"
            : data.boundary_tie
              ? "Pendiente de decisión externa en el corte"
              : "Listo para confirmar el reparto"}
      </Tag>
      {data.division_sizes && (
        <p>
          Capacidad configurada: A · {data.division_sizes.A}; B ·{" "}
          {data.division_sizes.B}.
        </p>
      )}
      <div className="trainer-grid">
        {data.players.map((player) => (
          <section key={player.id} aria-label={player.display_name}>
            <h3>{player.display_name}</h3>
            <p>
              {player.progress_state !== "observed" ||
              player.observed_badges == null
                ? "Progreso no observado / pendiente de sincronizar save"
                : `${player.observed_badges} medallas observadas · ${player.cap_reached ? "Medalla 2 alcanzada" : "Medalla 2 pendiente"}`}
            </p>
            <p>
              Muertes competitivas ajustadas:{" "}
              {player.adjusted_deaths ?? "No observadas"}
            </p>
            <p>
              {player.proposed_division
                ? `${data.state === "assigned" ? "División" : "Propuesta"}: ${player.proposed_division}`
                : data.boundary_tie?.player_ids.includes(player.id)
                  ? "División pendiente de desempate"
                  : "División pendiente"}
            </p>
          </section>
        ))}
      </div>
      {data.state === "pending" && !data.ready && (
        <>
          <p>
            Se necesita una observación fiable y suficiente de cada
            participante, junto con una configuración y una temporada
            preparadas. La conexión de subida del save todavía está pendiente;
            no se acredita el progreso manualmente.
          </p>
          {data.blocking_reasons.map(
            (reason) =>
              blockingLabels[reason] && (
                <p key={reason}>{blockingLabels[reason]}</p>
              ),
          )}
        </>
      )}
      {data.state === "pending" && data.ready && !data.boundary_tie && (
        <p>
          No hay empate que cruce el corte. Los empates dentro de una misma
          división no requieren ninguna decisión.
        </p>
      )}
      {data.state === "pending" && data.boundary_tie && !admin && (
        <p>
          Un empate cruza el corte A/B. Un administrador debe registrar la
          decisión deportiva externa antes de confirmar el reparto.
        </p>
      )}
      {admin && data.state === "pending" && (
        <>
          <form
            key={`${data.input_hash}:${reset}`}
            onSubmit={(event) => {
              const values = form(event);
              if (!data.ready || !data.config_version_id || disabled) return;
              const body: Model<"FinalizeInitialAssignmentBody"> = {
                config_version_id: data.config_version_id,
                expected_setup_revision: data.setup_revision,
                expected_roster_revision: data.roster_revision,
                input_hash: data.input_hash,
                ...(data.boundary_tie
                  ? {
                      tie_resolution: {
                        input_hash: data.input_hash,
                        orders: [
                          {
                            player_ids: data.boundary_tie.player_ids.map(
                              (_, i) => text(values, `boundary-${i}`),
                            ),
                            reason: text(values, "boundary-reason").trim(),
                          },
                        ],
                      },
                    }
                  : {}),
              };
              void command.execute(
                `/v1/admin/seasons/${season}/initial-assignment/finalize`,
                body,
              );
            }}
          >
            <fieldset disabled={disabled || !data.ready}>
              {data.ready && data.boundary_tie && (
                <BoundaryFields data={data} />
              )}
              <Submit pending={disabled || !data.ready}>
                Confirmar reparto inicial
              </Submit>
            </fieldset>
          </form>
          <CommandState command={command} />
        </>
      )}
    </Card>
  );
}
