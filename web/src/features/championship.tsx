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
  residual_required: "Desempate externo pendiente",
  tiebreak_required: "Desempate del título pendiente",
  battle_required: "Combate por el título pendiente",
  owner_decision_required: "Campeonato pendiente de decisión",
  frozen: "Campeón de Liga confirmado",
  legacy: "Historia de una temporada anterior",
};

const unresolvedReasons: Record<string, string> = {
  league_net_championship_tie_rule_required:
    "Hay un empate exacto en los puntos netos finales. La regla para decidir el campeón aún no está definida; no se aplicarán automáticamente muertes, victorias ni un Mejor de 3.",
  championship_deaths_unavailable:
    "Faltan muertes oficiales fiables para comparar a los líderes empatados. No se puede asignar un campeón con datos desconocidos.",
};

/** The server decides the title from exact frozen facts. This view never ranks. */
export function ChampionshipReview({
  seasonName,
  participant = false,
}: {
  seasonName: string;
  participant?: boolean;
}) {
  const { season, holdAdminNavigation } = useApp(),
    base = `/v1/${participant ? "" : "admin/"}seasons/${season}`,
    path = `${base}/championship`,
    query = useRead<Championship>(path, !!season),
    command = useCommand([
      path,
      `/v1/admin/seasons/${season}/setup`,
      `/v1/read/seasons/${season}/overview`,
      `/v1/read/seasons/${season}/league`,
      "/v1/read/seasons?offset=0",
    ]),
    [confirm, setConfirm] = useState(false),
    [tiebreakOpen, setTiebreakOpen] = useState(false),
    [reset, setReset] = useState(0);
  const conflict =
    command.error instanceof ApiError && command.error.status === 409
      ? command.error
      : null;
  useEffect(() => {
    if ((command.pending || command.uncertain) && holdAdminNavigation)
      return holdAdminNavigation();
  }, [command.pending, command.uncertain, holdAdminNavigation]);
  useEffect(() => {
    if (!conflict) return;
    setReset((value) => value + 1);
  }, [conflict]);
  useEffect(() => {
    setTiebreakOpen(
      !participant &&
        (query.data?.state === "tiebreak_required" ||
          query.data?.state === "battle_required"),
    );
  }, [participant, query.data?.state, query.data?.input_hash]);
  if (query.isPending) return <Loading />;
  if (query.error)
    return (
      <>
        <Notice error={query.error} />
        <CommandState command={command} />
      </>
    );
  const data = query.data;
  if (!data) return null;
  const disabled = command.pending || command.uncertain || query.isFetching,
    champion = data.players.find(
      (p) => p.trainer_id === data.champion_trainer_id,
    ),
    canFinish = data.state === "ready" && !!data.input_hash,
    titleTie =
      data.state === "tiebreak_required" || data.state === "battle_required",
    actualHistory =
      titleTie ||
      data.tiebreak_method != null ||
      data.players.some((player) => player.actual_deaths != null);
  return (
    <Card>
      <h2>Campeonato de Liga</h2>
      <p>El título se decide por los puntos totales acumulados oficiales.</p>
      <Tag>{labels[data.state]}</Tag>
      {champion && <h3>Campeón de Liga: {champion.display_name}</h3>}
      {data.resolution_type === "championship_bo3" && (
        <p>Desempate resuelto mediante un Mejor de 3 externo registrado.</p>
      )}
      {data.resolution_type === "total_actual_deaths" && (
        <p>Desempate del título confirmado por Muertes totales del Locke.</p>
      )}
      {data.resolution_type === "championship_1v1" && (
        <p>
          Desempate del título confirmado por Combate de desempate 1v1
          registrado.
        </p>
      )}
      {["triple_adjusted_deaths", "multiple_adjusted_deaths"].includes(
        data.resolution_type ?? "",
      ) && <p>Desempate resuelto por menos muertes ajustadas oficiales.</p>}
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
          {unresolvedReasons[data.blocking_reason ?? ""] ??
            "El campeonato sigue pendiente de una revisión excepcional. No se puede finalizar ni asignar un campeón hasta que el servidor confirme la resolución."}
        </p>
      )}
      {titleTie && (
        <p>
          {data.state === "battle_required"
            ? "Las muertes totales del Locke también están empatadas. Hace falta registrar los combates de desempate."
            : "Hay un empate en el primer puesto por puntos NETOS acumulados."}{" "}
          El campeón sigue provisional hasta que Administración confirme el
          desempate.
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
                <th>
                  {actualHistory
                    ? "Muertes totales del Locke"
                    : "Muertes ajustadas"}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.players.map((player) => (
                <tr key={player.season_player_id}>
                  <td>{player.display_name}</td>
                  <td>{player.total_points}</td>
                  <td>
                    {(actualHistory
                      ? player.actual_deaths
                      : player.adjusted_deaths) ?? "Sin evidencia oficial"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data.resolution_type === "championship_residual" && (
        <p>Desempate externo registrado.</p>
      )}
      {participant &&
        [
          "bo3_required",
          "residual_required",
          "tiebreak_required",
          "battle_required",
        ].includes(data.state) && (
          <p>
            Administración debe registrar el resultado del desempate externo.
          </p>
        )}
      {!participant && titleTie && (
        <button
          className="button primary"
          disabled={disabled}
          onClick={() => setTiebreakOpen(true)}
        >
          Resolver desempate del título
        </button>
      )}
      {!participant && titleTie && tiebreakOpen && (
        <Modal
          title="Desempate del título de Liga"
          onClose={() => {
            if (!command.pending && !command.uncertain) setTiebreakOpen(false);
          }}
        >
          <ChampionshipTiebreak
            key={`${data.input_hash}:${data.state}:${data.setup_revision}:${reset}`}
            data={data}
            path={path}
            command={command}
            disabled={disabled}
          />
        </Modal>
      )}
      {!participant &&
        (data.state === "bo3_required" ||
          data.state === "residual_required") && (
          <form
            key={`${data.input_hash}:${reset}`}
            onSubmit={(event) => {
              const values = form(event);
              if (disabled || !data.input_hash) return;
              void command.execute(
                `${path}/${data.state === "bo3_required" ? "bo3" : "residual"}`,
                {
                  expected_revision: data.setup_revision,
                  input_hash: data.input_hash,
                  winner_season_player_id: text(values, "winner"),
                  reason: text(values, "reason").trim(),
                } satisfies Model<"ChampionshipBo3Body">,
              );
            }}
          >
            <p>
              {data.state === "bo3_required"
                ? "Los dos líderes jugarán un Mejor de 3 externo. Registra su ganador."
                : "Persiste el empate tras comparar muertes. Registra la resolución externa entre los candidatos indicados."}
            </p>
            <fieldset disabled={disabled}>
              <Field
                label={
                  data.state === "bo3_required"
                    ? "Ganador del Mejor de 3"
                    : "Ganador del desempate externo"
                }
              >
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
              <Submit pending={command.pending} disabled={disabled}>
                Registrar ganador del desempate
              </Submit>
            </fieldset>
          </form>
        )}
      {data.state !== "legacy" && data.state !== "incomplete" && (
        <p className="muted">Sin finalista automático.</p>
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
      {!confirm && !(titleTie && tiebreakOpen && !participant) && (
        <CommandState command={command} />
      )}
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
                await command.execute(`${base}/finish`, {
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
            <Submit pending={command.pending} disabled={disabled || !canFinish}>
              Confirmar finalización
            </Submit>
          </form>
        </Modal>
      )}
    </Card>
  );
}

type TiebreakMethod = "total_actual_deaths" | "championship_1v1";

function ChampionshipTiebreak({
  data,
  path,
  command,
  disabled,
}: {
  data: Championship;
  path: string;
  command: ReturnType<typeof useCommand>;
  disabled: boolean;
}) {
  const [method, setMethod] = useState<TiebreakMethod>(
      data.state === "battle_required"
        ? "championship_1v1"
        : "total_actual_deaths",
    ),
    [battleRows, setBattleRows] = useState([0]),
    [nextRow, setNextRow] = useState(1);
  const candidates = data.players.filter((player) =>
      data.tied_player_ids.includes(player.season_player_id),
    ),
    deathsKnown = candidates.every((player) => player.actual_deaths != null),
    deathComparisonUnavailable =
      data.state === "battle_required" || !deathsKnown;
  return (
    <form
      onSubmit={async (event) => {
        const values = form(event);
        if (
          disabled ||
          !data.input_hash ||
          text(values, "confirmation") !== "yes" ||
          (method === "total_actual_deaths" && deathComparisonUnavailable)
        )
          return;
        const body: Model<"ChampionshipTiebreakBody"> = {
          expected_revision: data.setup_revision,
          input_hash: data.input_hash,
          confirmation: true,
          method,
          reason: text(values, "title-reason").trim(),
          ...(method === "championship_1v1"
            ? {
                winner_season_player_id: text(values, "title-winner"),
                battles: battleRows.map((row) => {
                  const played = new Date(
                    text(values, `title-battle-${row}-played`),
                  );
                  return {
                    player_a_id: text(values, `title-battle-${row}-a`),
                    player_b_id: text(values, `title-battle-${row}-b`),
                    winner_id: text(values, `title-battle-${row}-winner`),
                    played_at: Number.isNaN(played.getTime())
                      ? ""
                      : played.toISOString(),
                    evidence: text(
                      values,
                      `title-battle-${row}-evidence`,
                    ).trim(),
                  };
                }),
              }
            : {}),
        };
        await command.execute(`${path}/tiebreak`, body);
      }}
    >
      <p>
        Esta decisión solo resuelve el título final. Conserva los puntos NETOS,
        las victorias, las muertes oficiales y los premios de las jornadas.
      </p>
      <fieldset disabled={disabled}>
        <legend>Método de desempate</legend>
        <label>
          <input
            type="radio"
            name="title-method"
            value="total_actual_deaths"
            checked={method === "total_actual_deaths"}
            disabled={data.state === "battle_required"}
            onChange={() => setMethod("total_actual_deaths")}
          />
          Muertes totales del Locke
        </label>
        <p className="muted">
          Opción preferida: compara cada muerte histórica una sola vez,
          incluidas las de Pokémon revividos con comodines o tras wipes.
        </p>
        <label>
          <input
            type="radio"
            name="title-method"
            value="championship_1v1"
            checked={method === "championship_1v1"}
            onChange={() => setMethod("championship_1v1")}
          />
          Combate de desempate 1v1
        </label>
        {data.state === "battle_required" && (
          <p role="status">
            La comparación de muertes ya está registrada y sigue empatada.
            Registra la resolución mediante combates 1v1.
          </p>
        )}
        {method === "total_actual_deaths" && !deathsKnown && (
          <p role="status">
            Falta historial oficial de muertes. No se contará como cero:
            registra un desempate 1v1.
          </p>
        )}
        <ul>
          {candidates.map((player) => (
            <li key={player.season_player_id}>
              {player.display_name}:{" "}
              {player.actual_deaths ?? "sin evidencia oficial"} muertes
              históricas
            </li>
          ))}
        </ul>
        {method === "championship_1v1" && (
          <>
            <p>
              Registra únicamente los combates 1v1 ya jugados. Deben acreditar
              un ganador único entre todos los candidatos; la aplicación no
              elige emparejamientos ni organiza un torneo.
            </p>
            <Field label="Ganador del título por 1v1">
              <select name="title-winner" required defaultValue="">
                <option value="">Seleccionar al ganador registrado</option>
                {candidates.map((player) => (
                  <option
                    key={player.season_player_id}
                    value={player.season_player_id}
                  >
                    {player.display_name}
                  </option>
                ))}
              </select>
            </Field>
            {battleRows.map((row, index) => (
              <div key={row}>
                <TitleBattleFields
                  candidates={candidates}
                  row={row}
                  index={index}
                />
                {candidates.length > 2 && battleRows.length > 1 && (
                  <button
                    type="button"
                    className="button"
                    onClick={() =>
                      setBattleRows((rows) => rows.filter((id) => id !== row))
                    }
                  >
                    Quitar combate {index + 1}
                  </button>
                )}
              </div>
            ))}
            {candidates.length > 2 && (
              <button
                type="button"
                className="button"
                disabled={battleRows.length >= 1000}
                onClick={() => {
                  setBattleRows((rows) => [...rows, nextRow]);
                  setNextRow((value) => value + 1);
                }}
              >
                Añadir combate ya jugado
              </button>
            )}
          </>
        )}
        <Field label="Motivo de la confirmación del título">
          <textarea name="title-reason" required maxLength={500} />
        </Field>
        <label>
          <input type="checkbox" name="confirmation" value="yes" required />{" "}
          Confirmo el método y la evidencia del desempate
        </label>
        <Submit
          pending={command.pending}
          disabled={
            disabled ||
            (method === "total_actual_deaths" && deathComparisonUnavailable)
          }
        >
          Confirmar desempate del título
        </Submit>
      </fieldset>
      <CommandState command={command} />
    </form>
  );
}

function TitleBattleFields({
  candidates,
  row,
  index,
}: {
  candidates: Championship["players"];
  row: number;
  index: number;
}) {
  const fixed = candidates.length === 2,
    [a, setA] = useState(fixed ? candidates[0].season_player_id : ""),
    [b, setB] = useState(fixed ? candidates[1].season_player_id : "");
  const name = (id: string) =>
    candidates.find((player) => player.season_player_id === id)?.display_name;
  return (
    <fieldset>
      <legend>Combate 1v1 {index + 1}</legend>
      {fixed ? (
        <>
          <p>
            {name(a)} / {name(b)}
          </p>
          <input type="hidden" name={`title-battle-${row}-a`} value={a} />
          <input type="hidden" name={`title-battle-${row}-b`} value={b} />
        </>
      ) : (
        <>
          <Field label={`Participante A del combate ${index + 1}`}>
            <select
              name={`title-battle-${row}-a`}
              value={a}
              required
              onChange={(event) => setA(event.target.value)}
            >
              <option value="">Seleccionar participante</option>
              {candidates.map((player) => (
                <option
                  key={player.season_player_id}
                  value={player.season_player_id}
                  disabled={player.season_player_id === b}
                >
                  {player.display_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={`Participante B del combate ${index + 1}`}>
            <select
              name={`title-battle-${row}-b`}
              value={b}
              required
              onChange={(event) => setB(event.target.value)}
            >
              <option value="">Seleccionar participante</option>
              {candidates.map((player) => (
                <option
                  key={player.season_player_id}
                  value={player.season_player_id}
                  disabled={player.season_player_id === a}
                >
                  {player.display_name}
                </option>
              ))}
            </select>
          </Field>
        </>
      )}
      <Field label={`Ganador del combate ${index + 1}`}>
        <select
          key={`${a}:${b}`}
          name={`title-battle-${row}-winner`}
          required
          defaultValue=""
        >
          <option value="">Seleccionar el resultado jugado</option>
          {[a, b].filter(Boolean).map((id) => (
            <option key={id} value={id}>
              {name(id)}
            </option>
          ))}
        </select>
      </Field>
      <Field label={`Fecha del combate ${index + 1}`}>
        <input
          type="datetime-local"
          name={`title-battle-${row}-played`}
          required
        />
      </Field>
      <Field label={`Evidencia del combate ${index + 1}`}>
        <textarea
          name={`title-battle-${row}-evidence`}
          required
          maxLength={500}
        />
      </Field>
    </fieldset>
  );
}
