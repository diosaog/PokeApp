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
};

function TieOrderFields({
  group,
  index,
  name,
}: {
  group: Model<"TieGroup">;
  index: number;
  name: (id: string) => string;
}) {
  const [selected, setSelected] = useState<string[]>(
    group.player_ids.map(() => ""),
  );
  return (
    <fieldset>
      <legend>
        División {group.division} · posiciones {group.position}–
        {group.position_end}
      </legend>
      <p>
        {group.wins} {group.wins === 1 ? "victoria" : "victorias"} ·{" "}
        {group.adjusted_deaths}{" "}
        {group.adjusted_deaths === 1
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
          label={`Posición ${group.position + place} · división ${group.division}`}
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
            <option value="">Seleccionar según la decisión externa</option>
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
        label={`Motivo del desempate · división ${group.division} · posición ${group.position}`}
      >
        <textarea name={`tie-${index}-reason`} required maxLength={500} />
      </Field>
    </fieldset>
  );
}

export function DailyTieFields({
  review,
  name,
}: {
  review?: Model<"RankingReview">;
  name: (id: string) => string;
}) {
  if (!review) return null;
  return (
    <section aria-label="Resolución de empates">
      <h3>Registrar decisión externa</h3>
      <p>
        Introduce el orden acordado y su motivo. Los nombres de la lista no
        constituyen un criterio de desempate.
      </p>
      {review.groups.map((group, index) =>
        group.consequences.length > 0 ? (
          <TieOrderFields
            key={`${review.input_hash}:${index}`}
            group={group}
            index={index}
            name={name}
          />
        ) : (
          <p key={`${review.input_hash}:${index}`}>
            División {group.division}: {group.player_ids.map(name).join(", ")}{" "}
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
