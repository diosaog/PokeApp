import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
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
  Tag,
  form,
  text,
  useCommand,
} from "../ui";

type Championship = Model<"ChampionshipRead">;
const labels: Record<Championship["state"], string> = {
  incomplete: "Liga pendiente de completar",
  ready: "Campeonato resuelto",
  bo3_required: "Empate por el campeonato",
  owner_decision_required: "Campeonato pendiente de decisión",
  frozen: "Campeón de Liga confirmado",
  legacy: "Historia de una temporada anterior",
};

/** The server decides the title from exact frozen facts. This view never ranks. */
export function ChampionshipReview({ seasonName }: { seasonName: string }) {
  const { season } = useApp(),
    path = `/v1/admin/seasons/${season}/championship`,
    query = useRead<Championship>(path, !!season),
    command = useCommand([
      path,
      `/v1/admin/seasons/${season}/setup`,
      `/v1/read/seasons/${season}/overview`,
      `/v1/read/seasons/${season}/league`,
      "/v1/read/seasons?offset=0",
    ]),
    [confirm, setConfirm] = useState(false),
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
  if (!data) return null;
  const disabled = command.pending || command.uncertain || query.isFetching,
    champion = data.players.find(
      (p) => p.trainer_id === data.champion_trainer_id,
    ),
    canFinish = data.state === "ready" && !!data.input_hash;
  return (
    <Card>
      <h2>Campeonato de Liga</h2>
      <p>El título se decide por los puntos totales acumulados oficiales.</p>
      <Tag>{labels[data.state]}</Tag>
      {champion && <h3>Campeón de Liga: {champion.display_name}</h3>}
      {data.resolution_type === "championship_bo3" && (
        <p>Desempate resuelto mediante un Mejor de 3 externo registrado.</p>
      )}
      {data.resolution_type === "triple_adjusted_deaths" && (
        <p>
          Empate triple: resuelto por las menores muertes competitivas
          ajustadas.
        </p>
      )}
      {data.state === "incomplete" && (
        <p>
          Completa y cierra todas las jornadas de Liga antes de revisar el
          campeonato final.
        </p>
      )}
      {data.state === "legacy" && (
        <p>
          Esta temporada conserva su historia anterior. No se recalcula ni se
          sustituye su título.
        </p>
      )}
      {data.state === "owner_decision_required" && (
        <p>
          No se puede finalizar todavía: el campeonato sigue sin resolverse con
          las reglas aprobadas. Se necesita una decisión del propietario.
        </p>
      )}
      {data.players.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption>Puntos finales y muertes oficiales</caption>
            <thead>
              <tr>
                <th>Entrenador</th>
                <th>Puntos totales</th>
                <th>Muertes ajustadas</th>
              </tr>
            </thead>
            <tbody>
              {data.players.map((player) => (
                <tr key={player.season_player_id}>
                  <td>{player.display_name}</td>
                  <td>{player.total_points}</td>
                  <td>{player.adjusted_deaths ?? "Sin evidencia oficial"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data.state === "bo3_required" && (
        <form
          key={`${data.input_hash}:${reset}`}
          onSubmit={(event) => {
            const values = form(event);
            if (disabled || !data.input_hash) return;
            void command.execute(`${path}/bo3`, {
              expected_revision: data.setup_revision,
              input_hash: data.input_hash,
              winner_season_player_id: text(values, "winner"),
              reason: text(values, "reason").trim(),
            } satisfies Model<"ChampionshipBo3Body">);
          }}
        >
          <p>
            Los dos líderes jugarán un Mejor de 3 externo para decidir el
            campeón. Registra su ganador cuando haya terminado.
          </p>
          <fieldset disabled={disabled}>
            <Field label="Ganador del Mejor de 3">
              <select name="winner" required defaultValue="">
                <option value="">Seleccionar el ganador del desempate</option>
                {data.tied_player_ids.map((id) => (
                  <option key={id} value={id}>
                    {
                      data.players.find((p) => p.season_player_id === id)
                        ?.display_name
                    }
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Resultado y motivo del desempate">
              <textarea name="reason" required maxLength={500} />
            </Field>
            <Submit pending={disabled}>Registrar ganador del desempate</Submit>
          </fieldset>
        </form>
      )}
      {data.state !== "legacy" && data.state !== "incomplete" && (
        <p>
          La regla de finalista está pendiente de una decisión del propietario;
          no se asigna un finalista automáticamente.
        </p>
      )}
      {canFinish && (
        <button
          className="button primary"
          disabled={disabled}
          onClick={() => setConfirm(true)}
        >
          Finalizar Liga
        </button>
      )}
      {data.state === "frozen" && (
        <p>
          El título y sus puntos están congelados para el archivo histórico y el
          Hall.
        </p>
      )}
      {!confirm && <CommandState command={command} />}
      {confirm && (
        <Modal
          title="Finalizar Liga"
          onClose={() => {
            if (!command.pending && !command.uncertain) setConfirm(false);
          }}
        >
          <p>
            Se confirmará el campeón de {seasonName} y se cerrará la revisión de
            resultados. Los premios ya concedidos se conservan.
          </p>
          <form
            key={`${data.input_hash}:${reset}`}
            onSubmit={async (event) => {
              const values = form(event);
              if (
                disabled ||
                !canFinish ||
                !data.input_hash ||
                text(values, "confirmation") !== seasonName
              )
                return;
              if (
                await command.execute(`/v1/admin/seasons/${season}/finish`, {
                  expected_revision: data.setup_revision,
                  input_hash: data.input_hash,
                } satisfies Model<"FinishSeasonBody">)
              )
                setConfirm(false);
            }}
          >
            <Field label={`Escribe ${seasonName} para confirmar`}>
              <input name="confirmation" required disabled={disabled} />
            </Field>
            <CommandState command={command} />
            <Submit pending={disabled || !canFinish}>
              Confirmar finalización
            </Submit>
          </form>
        </Modal>
      )}
    </Card>
  );
}
