import { useEffect, useState } from "react";
import { ApiError, errorText } from "../api/client";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Field,
  Loading,
  Modal,
  Notice,
  Submit,
  form,
  text,
  useCommand,
} from "../ui";

function HistoryReview({
  season,
  player,
  close,
}: {
  season: string;
  player: Model<"SeasonSetup">["participants"][number];
  close: () => void;
}) {
  const base = `/v1/admin/seasons/${season}/participants/${player.id}/death-history`;
  const query = useRead<Model<"DeathHistoryRead">>(base);
  const command = useCommand([
    base,
    `/v1/read/seasons/${season}/league`,
    `/v1/read/seasons/${season}/overview`,
  ]);
  const { holdAdminNavigation } = useApp();
  const [source, setSource] = useState<Model<"DeathHistoryRead"> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (query.data && !source) setSource(query.data);
  }, [query.data, source]);
  useEffect(() => {
    if ((command.pending || command.uncertain) && holdAdminNavigation)
      return holdAdminNavigation();
  }, [command.pending, command.uncertain, holdAdminNavigation]);
  const busy = command.pending || command.uncertain;
  const canReconcile =
    source?.can_reconcile &&
    source.wipe_counter != null &&
    source.wipe_revision != null;
  const stale =
    source &&
    query.data &&
    (source.revision !== query.data.revision ||
      source.source_sha256 !== query.data.source_sha256 ||
      source.wipe_revision !== query.data.wipe_revision);
  return (
    <Modal
      title={`Historial de muertes · ${player.display_name}`}
      onClose={() => {
        if (!busy) close();
      }}
    >
      <Notice error={query.error} />
      {query.isPending && <Loading />}
      {source && (
        <>
          <p>
            Muertos confirmados:{" "}
            <strong>
              {source.known ? source.actual_deaths : "Desconocido"}
            </strong>
            . Muertes registradas con evidencia individual:{" "}
            {source.recorded_deaths}.
          </p>
          <p>
            Esta confirmación queda auditada y vinculada a la partida
            sincronizada. No modifica cierres anteriores ni supone que mover un
            Pokémon fuera de la caja sea revivirlo.
          </p>
          {source.blocking_reason && (
            <p role="alert">
              {errorText(new ApiError(409, source.blocking_reason))}
            </p>
          )}
          <form
            onSubmit={async (event) => {
              const values = form(event);
              if (
                busy ||
                query.isFetching ||
                stale ||
                !canReconcile ||
                !source.source_sha256 ||
                !values.has("confirm")
              )
                return;
              const counts = ["actual", "wipe", "segment"].map((name) =>
                text(values, name),
              );
              const reason = text(values, "reason").trim(),
                evidence = text(values, "evidence").trim();
              if (
                counts.some(
                  (value) =>
                    !/^\d+$/.test(value) ||
                    !Number.isSafeInteger(Number(value)) ||
                    Number(value) > 2147483647,
                ) ||
                !reason ||
                !evidence ||
                Number(counts[1]) > Number(counts[0]) ||
                Number(counts[2]) > Number(counts[0])
              ) {
                setError(
                  "Introduce los tres recuentos enteros y su evidencia. Los revividos tras wipe y las muertes de progresión no pueden superar el total histórico.",
                );
                return;
              }
              setError("");
              const body: Model<"DeathHistoryBody"> = {
                actual_deaths: Number(counts[0]),
                wipe_deaths: Number(counts[1]),
                segment_deaths: Number(counts[2]),
                source_sha256: source.source_sha256,
                expected_revision: source.revision,
                reason,
                evidence,
                revived_entity_ids: values.getAll("revived").map(String).sort(),
              };
              if (await command.execute(base, body, "PUT")) close();
            }}
          >
            <fieldset
              disabled={busy || !canReconcile || !!stale || query.isFetching}
            >
              <Field label="Muertos">
                <input
                  name="actual"
                  type="number"
                  min={0}
                  max={2147483647}
                  step={1}
                  required
                />
              </Field>
              <Field label="Muertes revividas tras wipe">
                <input
                  name="wipe"
                  type="number"
                  min={0}
                  max={2147483647}
                  step={1}
                  required
                />
              </Field>
              <p className="muted">
                El contador de wipe actual es{" "}
                {source.wipe_counter ?? "Desconocido"}; cada muerte
                correspondiente cuenta una vez y tiene una penalización total de
                0,2 puntos.
              </p>
              <Field label="Muertes de la progresión actual">
                <input
                  name="segment"
                  type="number"
                  min={0}
                  max={2147483647}
                  step={1}
                  required
                />
              </Field>
              <p className="muted">
                Incluye solo las muertes de este tramo de progresión. No
                atribuyas a la siguiente jornada muertes de una fase de combates
                anterior.
              </p>
              {source.observed_dead_entities
                .filter(
                  (entity) =>
                    entity.has_recorded_death && !entity.currently_dead,
                )
                .map((entity) => (
                  <label className="check" key={entity.pokemon_entity_id}>
                    <input
                      name="revived"
                      value={entity.pokemon_entity_id}
                      type="checkbox"
                    />
                    Confirmo que{" "}
                    {entity.display_name ||
                      entity.nickname ||
                      entity.species ||
                      `Pokémon ${entity.pokemon_entity_id.slice(0, 8)}`}{" "}
                    fue revivido y puede registrar una muerte posterior.
                  </label>
                ))}
              <Field label="Motivo de la confirmación">
                <textarea name="reason" maxLength={500} required />
              </Field>
              <Field label="Evidencia del historial y del tramo de progresión">
                <textarea name="evidence" maxLength={2000} required />
              </Field>
              <label className="check">
                <input name="confirm" type="checkbox" required />
                He revisado la partida y confirmo estos recuentos; no son
                valores estimados.
              </label>
              {error && <p role="alert">{error}</p>}
              <Submit
                pending={command.pending}
                disabled={busy || !canReconcile || !!stale}
              >
                Confirmar historial auditado
              </Submit>
            </fieldset>
            {stale && (
              <p role="alert">
                La partida o el historial cambiaron. Conservamos tu edición.{" "}
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setSource(query.data!)}
                >
                  Revisar evidencia actual
                </button>
              </p>
            )}
            {!canReconcile && (
              <p>
                Sincroniza una partida completa y revisa las operaciones
                pendientes antes de confirmar el historial.
              </p>
            )}
            <CommandState command={command} />
          </form>
        </>
      )}
    </Modal>
  );
}

export function DeathHistory({ setup }: { setup: Model<"SeasonSetup"> }) {
  const { adminOperationPending } = useApp();
  const [target, setTarget] = useState("");
  const player = setup.participants.find((entry) => entry.id === target);
  return (
    <Card>
      <h2>Historial de muertes</h2>
      <p>
        Si el historial anterior no está demostrado, confírmalo con evidencia
        antes de abrir la jornada. Las muertes no desaparecen al revivir o
        cambiar la caja.
      </p>
      {setup.participants.map((entry) => (
        <button
          key={entry.id}
          disabled={adminOperationPending || !!target}
          onClick={() => setTarget(entry.id)}
        >
          Revisar historial · {entry.display_name}
        </button>
      ))}
      {player && (
        <HistoryReview
          key={player.id}
          season={setup.season.id}
          player={player}
          close={() => setTarget("")}
        />
      )}
    </Card>
  );
}
