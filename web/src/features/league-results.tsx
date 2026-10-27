import { useState } from "react";
import type { Model, Overview } from "../api/types";
import { TrainerPhoto } from "../pokemon/presentation";
import { useRead } from "../state";
import { Card, CommandState, Loading, Modal, Notice, useCommand } from "../ui";

export function ParticipantResults({
  data,
  dayId,
  dayNumber,
}: {
  data: Overview;
  dayId: string;
  dayNumber?: number;
}) {
  const sid = data.season.id;
  const base = `/v1/seasons/${sid}/matchdays/${dayId}`;
  const q = useRead<Model<"DayState">>(base);
  const cmd = useCommand([
    base,
    `/v1/read/seasons/${sid}/overview`,
    `/v1/admin/seasons/${sid}/matchdays/${dayId}`,
  ]);
  const [selected, setSelected] = useState<
    Model<"DayState">["matches"][number] | null
  >(null);
  const [winner, setWinner] = useState<string | null>(null);
  const name = (id: string) =>
    data.players.find((player) => player.id === id)?.display_name ||
    "Entrenador";
  if (q.isPending) return <Loading />;
  if (q.error) return <Notice error={q.error} />;
  const day = q.data!;
  const recorded = day.matches.filter((match) => match.winner_id).length;
  const editable = day.state === "open" && day.current_matchday_id === dayId;
  const openMatch = (match: Model<"DayState">["matches"][number]) => {
    if (!editable || cmd.pending || cmd.uncertain) return;
    setSelected(match);
    setWinner(match.winner_id);
  };
  const save = async () => {
    if (!selected || winner === selected.winner_id) return;
    if (
      await cmd.execute(
        `${base}/results`,
        {
          expected_results_revision: day.results_revision,
          results: [
            {
              match_id: selected.id,
              winner_season_player_id: winner,
            },
          ],
        } satisfies Model<"ResultsBody">,
        "PUT",
      )
    ) {
      setSelected(null);
    }
  };
  return (
    <Card>
      <div className="section-row league-match-heading">
        <div>
          <h2>Jornada {dayNumber ?? ""}</h2>
          <p className="muted">
            {recorded}/{day.matches.length} resultados registrados
          </p>
        </div>
        <span className={`matchday-state ${editable ? "is-open" : ""}`}>
          {editable ? "Jornada abierta" : "Resultado oficial"}
        </span>
      </div>
      <p>
        {editable
          ? "Toca un combate para elegir el ganador. Puedes revisar cualquier resultado antes de cerrar la jornada."
          : "Esta jornada ya no admite cambios ordinarios. Las correcciones oficiales se realizan desde Administración."}
      </p>
      {/* While the dialog is open the page behind it is inert: the dialog
          shows the outcome, including the retry of an uncertain save. */}
      {!selected && <CommandState command={cmd} />}
      <div className="league-match-grid">
        {day.matches.map((match) => {
          const winnerName = match.winner_id ? name(match.winner_id) : null;
          const content = (
            <>
              <div
                className={`match-trainer ${match.winner_id === match.player_a_id ? "is-winner" : ""}`}
              >
                <TrainerPhoto name={name(match.player_a_id)} />
                <strong>{name(match.player_a_id)}</strong>
              </div>
              <span className="match-vs">VS</span>
              <div
                className={`match-trainer ${match.winner_id === match.player_b_id ? "is-winner" : ""}`}
              >
                <strong>{name(match.player_b_id)}</strong>
                <TrainerPhoto name={name(match.player_b_id)} />
              </div>
              <div className="match-result">
                {winnerName ? `GANADOR: ${winnerName}` : "PENDIENTE"}
              </div>
            </>
          );
          return editable ? (
            <button
              type="button"
              className="league-match-card"
              key={match.id}
              onClick={() => openMatch(match)}
            >
              {content}
            </button>
          ) : (
            <article className="league-match-card" key={match.id}>
              {content}
            </article>
          );
        })}
      </div>
      {selected && (
        <Modal
          title="¿Quién ganó?"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setSelected(null);
          }}
        >
          <p>
            {name(selected.player_a_id)} contra {name(selected.player_b_id)}
          </p>
          <div className="winner-picker">
            {[selected.player_a_id, selected.player_b_id].map((id) => (
              <button
                type="button"
                key={id}
                className={winner === id ? "is-selected" : ""}
                aria-pressed={winner === id}
                onClick={() => setWinner(id)}
              >
                <TrainerPhoto name={name(id)} />
                <span>{name(id)}</span>
              </button>
            ))}
            <button
              type="button"
              className={winner === null ? "is-selected" : ""}
              aria-pressed={winner === null}
              onClick={() => setWinner(null)}
            >
              Sin resultado
            </button>
          </div>
          <button
            type="button"
            className="button primary"
            disabled={
              cmd.pending || cmd.uncertain || winner === selected.winner_id
            }
            aria-busy={cmd.pending || undefined}
            onClick={() => void save()}
          >
            {cmd.pending ? "Guardando…" : "Guardar resultado"}
          </button>
          <CommandState command={cmd} />
        </Modal>
      )}
    </Card>
  );
}
