import { useState } from "react";
import { Scale } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Heading,
  Loading,
  Modal,
  Notice,
  Submit,
  Tag,
  date,
  form,
  number,
  text,
  useCommand,
} from "../ui";
import { WithSeason } from "./core";

function TrialForm({
  trial,
  mode,
  onClose,
}: {
  trial?: Model<"TrialView">;
  mode: "create" | "proposal" | "resolve" | "correct" | "cancel";
  onClose: () => void;
}) {
  const { season } = useApp(),
    overview = useOverview(),
    cmd = useCommand(),
    [verdict, setVerdict] = useState<"guilty" | "not_guilty">(
      trial?.verdict || "guilty",
    ),
    proposal = mode === "create" || mode === "proposal",
    decision = mode === "resolve" || mode === "correct";
  return (
    <Modal
      title={
        {
          create: "Abrir juicio",
          proposal: "Editar propuesta",
          resolve: "Registrar decisión de Discord",
          correct: "Corregir decisión",
          cancel: "Cancelar propuesta",
        }[mode]
      }
      onClose={() => {
        if (!cmd.pending && !cmd.uncertain) onClose();
      }}
    >
      <form
        onSubmit={async (event) => {
          const data = form(event);
          let body:
            | Model<"CreateTrialBody">
            | Model<"UpdateTrialBody">
            | Model<"ResolveTrialBody">
            | Model<"CorrectTrialBody">
            | Model<"CancelTrialBody">;
          if (proposal) {
            const fields = {
              title: text(data, "title"),
              description: text(data, "description"),
              evidence: text(data, "evidence"),
              is_public: data.has("public"),
            };
            body =
              mode === "create"
                ? { ...fields, accused_trainer_id: text(data, "accused") }
                : { ...fields, expected_case_revision: trial!.revision };
          } else if (decision) {
            const sanctions: Model<"ResolveTrialBody">["sanctions"] = [];
            if (verdict === "guilty") {
              if (data.has("store_ban"))
                sanctions.push({
                  type: "store_ban",
                  duration_matchdays: number(data, "ban_days"),
                });
              if (data.has("coins"))
                sanctions.push({
                  type: "coins_reduction",
                  amount: number(data, "coins_amount"),
                });
              if (data.has("points"))
                sanctions.push({
                  type: "points_reduction",
                  amount: text(data, "points_amount"),
                });
            }
            if (data.has("release"))
              sanctions.push({
                type: "pokemon_release",
                text: text(data, "release_text"),
              });
            if (data.has("other"))
              sanctions.push({ type: "other", text: text(data, "other_text") });
            body = {
              expected_case_revision: trial!.revision,
              verdict,
              decision_summary: text(data, "summary"),
              sanctions,
              ...(mode === "correct" ? { reason: text(data, "reason") } : {}),
            };
          } else
            body = {
              expected_case_revision: trial!.revision,
              reason: text(data, "reason"),
            };
          if (
            await cmd.execute(
              `/v1/seasons/${season}/trials${trial ? `/${trial.id}/${mode}` : ""}`,
              body,
              mode === "proposal" ? "PUT" : "POST",
            )
          )
            onClose();
        }}
      >
        {proposal ? (
          <>
            <Field label="Título">
              <input
                name="title"
                defaultValue={trial?.title}
                required
                maxLength={120}
              />
            </Field>
            {mode === "create" && (
              <Field label="Entrenador acusado">
                <select name="accused" required defaultValue="">
                  <option value="">Seleccionar entrenador</option>
                  {overview.data?.players.map((p) => (
                    <option key={p.id} value={p.trainer_id}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <Field label="Descripción">
              <textarea
                name="description"
                defaultValue={trial?.description}
                required
                maxLength={2000}
              />
            </Field>
            <Field label="Evidencias / referencia de Discord">
              <textarea
                name="evidence"
                defaultValue={trial?.detail?.evidence}
                maxLength={10000}
              />
            </Field>
            <label className="check">
              <input
                type="checkbox"
                name="public"
                defaultChecked={trial?.is_public ?? true}
              />
              Juicio público
            </label>
          </>
        ) : decision ? (
          <>
            <p>
              Registra el acuerdo explícito tomado en Discord. PokeApp aplica
              sus consecuencias; no hay votación dentro de la aplicación.
            </p>
            <Field label="Veredicto">
              <select
                value={verdict}
                onChange={(e) => setVerdict(e.target.value as typeof verdict)}
              >
                <option value="guilty">Culpable</option>
                <option value="not_guilty">No culpable</option>
              </select>
            </Field>
            <Field label="Resumen de la decisión">
              <textarea name="summary" required maxLength={2000} />
            </Field>
            <fieldset disabled={verdict === "not_guilty"}>
              <legend>Sanciones mecánicas</legend>
              <label className="check">
                <input type="checkbox" name="store_ban" />
                Store Ban
              </label>
              <Field label="Duración (jornadas)">
                <input
                  name="ban_days"
                  type="number"
                  min={1}
                  max={1000}
                  defaultValue={1}
                />
              </Field>
              <label className="check">
                <input type="checkbox" name="coins" />
                Reducción de monedas
              </label>
              <Field label="Monedas">
                <input
                  name="coins_amount"
                  type="number"
                  min={1}
                  step={1}
                  defaultValue={1}
                />
              </Field>
              <label className="check">
                <input type="checkbox" name="points" />
                Reducción de puntos
              </label>
              <Field label="Puntos exactos">
                <input
                  name="points_amount"
                  type="number"
                  min="0.01"
                  max="9999999999.99"
                  step="0.01"
                  defaultValue="1.00"
                />
              </Field>
            </fieldset>
            <label className="check">
              <input type="checkbox" name="release" />
              Liberación de Pokémon (nota)
            </label>
            <Field label="Detalle de la liberación">
              <textarea name="release_text" maxLength={2000} />
            </Field>
            <label className="check">
              <input type="checkbox" name="other" />
              Advertencia u otra nota
            </label>
            <Field label="Detalle de la nota">
              <textarea name="other_text" maxLength={2000} />
            </Field>
          </>
        ) : (
          <p>Se conservará el historial del juicio cancelado.</p>
        )}
        {(mode === "cancel" || mode === "correct") && (
          <Field label="Motivo">
            <textarea name="reason" required maxLength={500} />
          </Field>
        )}
        <CommandState command={cmd} />
        <Submit pending={cmd.pending || cmd.uncertain}>Confirmar</Submit>
      </form>
    </Modal>
  );
}
function TrialDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const { season, me } = useApp(),
    q = useRead<Model<"TrialView">>(`/v1/seasons/${season}/trials/${id}`),
    [mode, setMode] = useState<
      "proposal" | "resolve" | "correct" | "cancel" | null
    >(null);
  const trial = q.data,
    creator =
      trial?.detail?.history.find((h) => h.operation === "create")
        ?.actor_trainer_id === me?.trainer_id;
  return (
    <>
      <Modal title={trial?.title || "Juicio"} onClose={onClose}>
        <Notice error={q.error} />
        {q.isPending ? (
          <Loading />
        ) : (
          trial && (
            <>
              <Tag>
                #{trial.case_number ?? "Legacy"} · {trial.status}
              </Tag>
              <p>{trial.description}</p>
              <p>
                Veredicto:{" "}
                {trial.verdict === "guilty"
                  ? "Culpable"
                  : trial.verdict === "not_guilty"
                    ? "No culpable"
                    : "Sin decisión explícita"}
              </p>
              {trial.detail && (
                <>
                  <h3>Evidencias</h3>
                  <p className="pre-wrap">
                    {trial.detail.evidence || "Sin referencias adicionales."}
                  </p>
                  <div className="toolbar">
                    {trial.status === "open" && (
                      <>
                        <button onClick={() => setMode("resolve")}>
                          Registrar decisión
                        </button>
                        {creator && (
                          <>
                            <button onClick={() => setMode("proposal")}>
                              Editar propuesta
                            </button>
                            <button
                              className="danger"
                              onClick={() => setMode("cancel")}
                            >
                              Cancelar propuesta
                            </button>
                          </>
                        )}
                      </>
                    )}
                    {["resolved", "dismissed"].includes(trial.status) && (
                      <button onClick={() => setMode("correct")}>
                        Corregir decisión
                      </button>
                    )}
                  </div>
                  <h3>Historial</h3>
                  {trial.detail.history.map((h) => (
                    <article key={h.id} className="history-item">
                      <span className="eyebrow">
                        {date(h.created_at)} · {h.operation} · revisión{" "}
                        {h.revision}
                      </span>
                      <p>{h.decision_summary || h.details.description}</p>
                      {h.reason && <p>Motivo: {h.reason}</p>}
                      {h.sanctions.map((s) => (
                        <p key={s.type}>
                          {s.type}:{" "}
                          {"amount" in s
                            ? s.amount
                            : "duration_matchdays" in s
                              ? `${s.duration_matchdays} jornadas`
                              : s.text}
                        </p>
                      ))}
                    </article>
                  ))}
                </>
              )}
            </>
          )
        )}
      </Modal>
      {mode && trial && (
        <TrialForm trial={trial} mode={mode} onClose={() => setMode(null)} />
      )}
    </>
  );
}
export function TrialsPage() {
  const { season } = useApp(),
    q = useRead<Model<"TrialList">>(`/v1/seasons/${season}/trials`, !!season),
    [create, setCreate] = useState(false),
    [selected, setSelected] = useState("");
  return (
    <>
      <Heading
        eyebrow="ACUERDOS CLAROS. HISTORIAL COMPLETO."
        title="Juicios y sanciones."
      >
        La decisión se toma en Discord. Aquí queda registrada.
      </Heading>
      <WithSeason>
        <button className="button primary" onClick={() => setCreate(true)}>
          Abrir juicio
        </button>
        <Notice error={q.error} />
        {q.isPending ? (
          <Loading />
        ) : q.data?.cases.length ? (
          <div className="trainer-grid">
            {q.data.cases.map((t) => (
              <button
                key={t.id}
                className="card trial-card"
                onClick={() => setSelected(t.id)}
              >
                <Scale />
                <Tag>
                  #{t.case_number ?? "Legacy"} · {t.status}
                </Tag>
                <h2>{t.title}</h2>
                <p>{t.description}</p>
                <span className="text-link">Consultar historial →</span>
              </button>
            ))}
          </div>
        ) : (
          <Empty>No hay juicios visibles en esta temporada.</Empty>
        )}
      </WithSeason>
      {create && <TrialForm mode="create" onClose={() => setCreate(false)} />}
      {selected && (
        <TrialDetail id={selected} onClose={() => setSelected("")} />
      )}
    </>
  );
}
