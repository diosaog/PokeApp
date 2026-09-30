import type { Model, Overview } from "../api/types";
import { useRead } from "../state";
import {
  Card,
  CommandState,
  Field,
  Loading,
  Notice,
  Submit,
  useCommand,
} from "../ui";

export function ParticipantResults({
  data,
  dayId,
}: {
  data: Overview;
  dayId: string;
}) {
  const sid = data.season.id;
  const base = `/v1/seasons/${sid}/matchdays/${dayId}`;
  const q = useRead<Model<"DayState">>(base);
  const cmd = useCommand([
    base,
    `/v1/read/seasons/${sid}/overview`,
    `/v1/admin/seasons/${sid}/matchdays/${dayId}`,
  ]);
  const name = (id: string) =>
    data.players.find((p) => p.id === id)?.display_name || "Entrenador";
  if (q.isPending) return <Loading />;
  if (q.error) return <Notice error={q.error} />;
  const day = q.data!;
  return (
    <Card>
      <h2>Registrar resultados</h2>
      <p>
        Cualquier participante activo puede registrar o cambiar el ganador de
        estos combates mientras la jornada siga abierta.
      </p>
      <CommandState command={cmd} />
      {day.state === "open" && day.current_matchday_id === dayId ? (
        <form
          key={`${sid}:${dayId}:${day.results_revision}`}
          onSubmit={(event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            const results = day.matches
              .map((m) => ({
                match_id: m.id,
                winner_season_player_id: String(values.get(m.id) || "") || null,
              }))
              .filter(
                (r, i) =>
                  r.winner_season_player_id !== day.matches[i].winner_id,
              );
            if (!results.length) return;
            void cmd.execute(
              `${base}/results`,
              {
                expected_results_revision: day.results_revision,
                results,
              } satisfies Model<"ResultsBody">,
              "PUT",
            );
          }}
        >
          <fieldset disabled={cmd.pending || cmd.uncertain}>
            {day.matches.map((m) => (
              <Field
                key={m.id}
                label={`Ganador: ${name(m.player_a_id)} / ${name(m.player_b_id)}`}
              >
                <select name={m.id} defaultValue={m.winner_id || ""}>
                  <option value="">Sin resultado</option>
                  <option value={m.player_a_id}>{name(m.player_a_id)}</option>
                  <option value={m.player_b_id}>{name(m.player_b_id)}</option>
                </select>
              </Field>
            ))}
            {day.matches.length > 0 && (
              <Submit pending={cmd.pending || cmd.uncertain}>
                Guardar resultados
              </Submit>
            )}
          </fieldset>
        </form>
      ) : (
        <p>
          Esta jornada ya no admite cambios ordinarios. Las correcciones
          oficiales se realizan desde Administración.
        </p>
      )}
    </Card>
  );
}
