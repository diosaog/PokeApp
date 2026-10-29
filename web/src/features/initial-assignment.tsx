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
  opponent_missing:
    "Puedes preparar y sincronizar tu partida a solas. Para comenzar los enfrentamientos deben estar inscritos al menos dos entrenadores; no necesitan estar conectados.",
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
  const { season, me, holdAdminNavigation } = useApp(),
    path = `/v1/seasons/${season}/initial-assignment`,
    query = useRead<Assignment>(path, !!season),
    command = useCommand(),
    [reset, setReset] = useState(0);
  const conflict =
    command.error instanceof ApiError && command.error.status === 409
      ? command.error
      : null;
  useEffect(() => {
    if (
      administrative &&
      (command.pending || command.uncertain) &&
      holdAdminNavigation
    )
      return holdAdminNavigation();
  }, [administrative, command.pending, command.uncertain, holdAdminNavigation]);
  useEffect(() => {
    if (!conflict) return;
    setReset((value) => value + 1);
  }, [conflict]);
  if (query.isPending) return <Loading />;
  if (query.error)
    return (
      <>
        <Notice error={query.error} />
        <CommandState command={command} />
      </>
    );
  const data = query.data;
  if (!data || data.state === "legacy")
    return <CommandState command={command} />;
  const admin = administrative && me?.is_admin;
  // One league (division_sizes {A}) has no cut: everyone starts in the Liga.
  const single = !!data.division_sizes && data.division_sizes.B == null;
  const disabled = command.pending || command.uncertain || query.isFetching;
  return (
    <Card>
      <h2>{single ? "Inicio de la Liga" : "Reparto inicial A/B"}</h2>
      <p className="muted">
        Cuando todos tengan la Medalla 2
        {single ? ", empieza la Liga." : ", el reparto sigue las muertes."}
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
      {data.division_sizes &&
        (single ? (
          <p>{data.division_sizes.A} participantes.</p>
        ) : (
          <p>
            Capacidad configurada: A · {data.division_sizes.A}; B ·{" "}
            {data.division_sizes.B}.
          </p>
        ))}
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
              {player.proposed_division && single
                ? data.state === "assigned"
                  ? "En la Liga"
                  : "Propuesta: Liga"
                : player.proposed_division
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
          {data.blocking_reasons.map(
            (reason) =>
              blockingLabels[reason] && (
                <p key={reason}>{blockingLabels[reason]}</p>
              ),
          )}
        </>
      )}
      {data.state === "pending" &&
        data.ready &&
        !data.boundary_tie &&
        !single && <p className="muted">Sin empate en el corte.</p>}
      {data.state === "pending" && data.boundary_tie && !admin && (
        <p>Empate en el corte A/B: lo resuelve un administrador.</p>
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
              <Submit
                pending={command.pending}
                disabled={disabled || !data.ready}
              >
                {single
                  ? "Confirmar inicio de la Liga"
                  : "Confirmar reparto inicial"}
              </Submit>
            </fieldset>
          </form>
        </>
      )}
      <CommandState command={command} />
    </Card>
  );
}
