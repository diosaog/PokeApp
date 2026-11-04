import { useEffect, useState } from "react";
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
  useCommand,
} from "../ui";

export function Enrollment() {
  const { season, holdAdminNavigation } = useApp();
  const path = `/v1/admin/seasons/${season}/enrollment`;
  const preview = useRead<Model<"EnrollmentPreview">>(path);
  const cmd = useCommand();
  const [trainer, setTrainer] = useState("");
  const [review, setReview] = useState<{
    trainer: string;
    name: string;
    preview: Model<"EnrollmentPreview">;
  } | null>(null);
  const busy = cmd.pending || cmd.uncertain;
  const stale =
    !!review && review.preview.preview_hash !== preview.data?.preview_hash;
  useEffect(() => {
    if (busy && holdAdminNavigation) return holdAdminNavigation();
  }, [busy, holdAdminNavigation]);
  return (
    <Card>
      <h2>Añadir entrenador</h2>
      <p>
        Se incorporará a la jornada en curso o a la siguiente, con 0 puntos y
        las monedas de las jornadas ya cerradas.
      </p>
      {preview.isPending && <Loading />}
      <Notice error={preview.error} />
      {preview.data && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const selected = preview.data?.eligible_trainers.find(
              (t) => t.id === trainer,
            );
            if (!selected || !preview.data || busy) return;
            setReview({
              trainer: selected.id,
              name: selected.display_name,
              preview: structuredClone(preview.data),
            });
          }}
        >
          <Field label="Entrenador">
            <select
              value={trainer}
              onChange={(event) => setTrainer(event.target.value)}
              required
              disabled={busy}
            >
              <option value="">Seleccionar cuenta</option>
              {preview.data.eligible_trainers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.display_name}
                </option>
              ))}
            </select>
          </Field>
          {preview.data.eligible_trainers.length === 0 && (
            <p className="muted">
              No hay cuentas disponibles. Crea o invita primero a la cuenta
              desde Administración.
            </p>
          )}
          <Submit pending={false} disabled={busy || !trainer}>
            Revisar incorporación
          </Submit>
        </form>
      )}
      {!review && <CommandState command={cmd} />}
      {review && (
        <Modal
          title={`Incorporar entrenador a ${review.preview.season_name}`}
          onClose={() => {
            if (!busy) setReview(null);
          }}
        >
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (busy || stale) return;
              if (
                await cmd.execute(path, {
                  trainer_id: review.trainer,
                  preview_hash: review.preview.preview_hash,
                } satisfies Model<"EnrollmentBody">)
              ) {
                setReview(null);
                setTrainer("");
              }
            }}
          >
            <p>
              <strong>{review.name}</strong>
            </p>
            <ul>
              <li>Puntos iniciales: {review.preview.initial_points}.</li>
              <li>Jornadas completadas: {review.preview.closed_matchdays}.</li>
              <li>Monedas iniciales: {review.preview.initial_coins}.</li>
              <li>
                Participará desde: J{review.preview.first_matchday_number} (
                {review.preview.matchday_status === "open"
                  ? "en curso"
                  : review.preview.matchday_status === "scheduled"
                    ? "preparada"
                    : "próxima jornada"}
                ).
              </li>
              <li>Nuevos enfrentamientos: {review.preview.new_matchups}.</li>
            </ul>
            <p>
              Deberá registrar su partida oficial con el Launcher. La primera
              sincronización válida establece su punto de partida; las medallas
              ya obtenidas no dan monedas adicionales. Los resultados anteriores
              se conservan.
            </p>
            {stale && (
              <p role="alert">
                La Liga ha cambiado. Cierra esta confirmación y revisa una nueva
                incorporación.
              </p>
            )}
            <Submit pending={cmd.pending} disabled={busy || stale}>
              Confirmar incorporación
            </Submit>
            <CommandState command={cmd} />
          </form>
        </Modal>
      )}
    </Card>
  );
}
