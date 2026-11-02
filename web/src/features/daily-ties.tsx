import { useState } from "react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { Field, text } from "../ui";

export function tieReview(error: unknown) {
  return error instanceof ApiError ? error.ranking : undefined;
}

const consequenceLabels: Record<
  Model<"TieGroup">["consequences"][number],
  string
> = {
  points: "puntos",
  coins: "monedas",
  podium: "podio",
  movement: "ascensos o descensos",
  last_b_reward: "robo del último de B",
  single_league_prize: "premio extra de Blindar o Robar Pokémon",
  matchday_prize: "premio extra de Blindar o Robar Pokémon",
};

const pairs = (ids: string[]) =>
  ids.flatMap((a, i) => ids.slice(i + 1).map((b) => [a, b] as const));

// One league has no division letter: its groups are simply «Liga». Inside a
// sentence the noun is lowercase but the letter stays («división A»).
const where = (group: Model<"TieGroup">, single: boolean) =>
  single ? "Liga" : `División ${group.division}`;
const whereInline = (group: Model<"TieGroup">, single: boolean) =>
  single ? "liga" : `división ${group.division}`;

function TieOrderFields({
  group,
  index,
  name,
  single,
  battlesRequired,
}: {
  group: Model<"TieGroup">;
  index: number;
  name: (id: string) => string;
  single: boolean;
  battlesRequired: boolean;
}) {
  const [selected, setSelected] = useState<string[]>(
    group.player_ids.map(() => ""),
  );
  return (
    <fieldset>
      <legend>
        {where(group, single)} · posiciones {group.position}–
        {group.position_end}
      </legend>
      <p>
        {group.wins} {group.wins === 1 ? "victoria" : "victorias"} ·{" "}
        {group.segment_deaths ?? group.adjusted_deaths}{" "}
        {battlesRequired
          ? group.segment_deaths === 1
            ? "muerte de progresión"
            : "muertes de progresión"
          : group.adjusted_deaths === 1
            ? "muerte competitiva ajustada"
            : "muertes competitivas ajustadas"}{" "}
        por participante.
      </p>
      <p>
        Afecta a:{" "}
        {group.consequences
          .map((effect) => consequenceLabels[effect])
          .join(", ")}
        .
      </p>
      {selected.map((value, place) => (
        <Field
          key={place}
          label={`Posición ${group.position + place} · ${whereInline(group, single)}`}
        >
          <select
            name={`tie-${index}-${place}`}
            value={value}
            required
            onChange={(event) =>
              setSelected(
                selected.map((old, i) =>
                  i === place ? event.target.value : old,
                ),
              )
            }
          >
            <option value="">
              {battlesRequired
                ? "Seleccionar según los combates 1v1"
                : "Seleccionar según la decisión externa"}
            </option>
            {group.player_ids.map((id) => (
              <option
                key={id}
                value={id}
                disabled={selected.some(
                  (chosen, i) => chosen === id && i !== place,
                )}
              >
                {name(id)}
              </option>
            ))}
          </select>
        </Field>
      ))}
      <Field
        label={`Motivo del desempate · ${whereInline(group, single)} · posición ${group.position}`}
      >
        <textarea name={`tie-${index}-reason`} required maxLength={500} />
      </Field>
      {battlesRequired && (
        <>
          <p>
            Registra cada combate 1v1 adicional entre los empatados. No suma
            puntos ni victorias normales. Si los resultados no permiten un orden
            completo, el cierre seguirá pendiente.
          </p>
          {pairs(group.player_ids).map(([a, b], pair) => (
            <fieldset key={`${a}:${b}`}>
              <legend>
                1v1: {name(a)} / {name(b)}
              </legend>
              <Field label={`Ganador 1v1 · ${name(a)} / ${name(b)}`}>
                <select name={`tie-${index}-battle-${pair}-winner`} required>
                  <option value="">Resultado pendiente</option>
                  {[a, b].map((id) => (
                    <option key={id} value={id}>
                      {name(id)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={`Fecha del 1v1 · ${name(a)} / ${name(b)}`}>
                <input
                  type="datetime-local"
                  name={`tie-${index}-battle-${pair}-played`}
                  required
                />
              </Field>
              <Field label={`Evidencia del 1v1 · ${name(a)} / ${name(b)}`}>
                <textarea
                  name={`tie-${index}-battle-${pair}-evidence`}
                  required
                  maxLength={500}
                />
              </Field>
            </fieldset>
          ))}
        </>
      )}
    </fieldset>
  );
}

export function DailyTieFields({
  review,
  name,
  single = false,
}: {
  review?: Model<"RankingReview">;
  name: (id: string) => string;
  single?: boolean;
}) {
  if (!review) return null;
  const global = single || review.ranking_rule === "wins_segment_deaths_v2";
  return (
    <section aria-label="Resolución de empates">
      <h3>
        {review.ranking_rule === "wins_segment_deaths_v2"
          ? "Registrar desempates 1v1"
          : "Registrar decisión externa"}
      </h3>
      <p>
        {review.ranking_rule === "wins_segment_deaths_v2"
          ? "El orden debe estar respaldado por los resultados reales de los combates extra, su fecha y evidencia."
          : "Introduce el orden acordado y su motivo. Los nombres de la lista no constituyen un criterio de desempate."}
      </p>
      {review.groups.map((group, index) =>
        group.consequences.length > 0 ? (
          <TieOrderFields
            key={`${review.input_hash}:${index}`}
            group={group}
            index={index}
            name={name}
            single={global}
            battlesRequired={
              review.ranking_rule === "wins_segment_deaths_v2" ||
              group.segment_deaths != null
            }
          />
        ) : (
          <p key={`${review.input_hash}:${index}`}>
            {where(group, global)}: {group.player_ids.map(name).join(", ")}{" "}
            comparten posición {group.position}. Este empate no necesita
            resolución.
          </p>
        ),
      )}
    </section>
  );
}

export function readTieResolution(
  data: FormData,
  review?: Model<"RankingReview">,
): Model<"TieResolution"> | undefined {
  if (!review) return;
  const orders = review.groups.flatMap((group, index) =>
    group.consequences.length
      ? [
          {
            player_ids: group.player_ids.map((_, place) =>
              text(data, `tie-${index}-${place}`),
            ),
            reason: text(data, `tie-${index}-reason`).trim(),
            ...(review.ranking_rule === "wins_segment_deaths_v2" ||
            group.segment_deaths != null
              ? {
                  battles: pairs(group.player_ids).map(([a, b], pair) => {
                    const date = new Date(
                      text(data, `tie-${index}-battle-${pair}-played`),
                    );
                    return {
                      player_a_id: a,
                      player_b_id: b,
                      winner_id: text(
                        data,
                        `tie-${index}-battle-${pair}-winner`,
                      ),
                      played_at: Number.isNaN(date.getTime())
                        ? ""
                        : date.toISOString(),
                      evidence: text(
                        data,
                        `tie-${index}-battle-${pair}-evidence`,
                      ).trim(),
                    };
                  }),
                }
              : {}),
          },
        ]
      : [],
  );
  if (!orders.length) return;
  orders.sort((a, b) =>
    [...a.player_ids]
      .sort()
      .join(",")
      .localeCompare([...b.player_ids].sort().join(",")),
  );
  return { input_hash: review.input_hash, orders };
}
