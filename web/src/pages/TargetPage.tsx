import { Target } from "lucide-react";

import { SpeciesSelect } from "@/components/common/SpeciesSelect";
import type { IvConstraint, StatKey } from "@/domain/pokemon/types";
import { fullStatLabels, statKeys } from "@/domain/pokemon/types";
import { useSession } from "@/state/sessionStore";
import { clamp } from "@/utils/math";

const constraintLabel: Record<IvConstraint["kind"], string> = {
  any: "Indiferente",
  exact31: "Exactamente 31",
  min: "Minimo",
  range: "Rango",
  exact: "Valor exacto",
  preferred: "Preferido",
};

const defaultForKind = (kind: IvConstraint["kind"]): IvConstraint => {
  switch (kind) {
    case "any":
      return { kind: "any" };
    case "exact31":
      return { kind: "exact31" };
    case "min":
      return { kind: "min", value: 28 };
    case "range":
      return { kind: "range", min: 28, max: 31 };
    case "exact":
      return { kind: "exact", value: 0 };
    case "preferred":
      return { kind: "preferred", value: 31, weight: 1 };
  }
};

const updateConstraintNumber = (constraint: IvConstraint, field: "value" | "min" | "max" | "weight", value: number): IvConstraint => {
  const ivValue = field === "weight" ? clamp(value, 0, 10) : clamp(value, 0, 31);
  switch (constraint.kind) {
    case "min":
      return field === "value" ? { ...constraint, value: ivValue } : constraint;
    case "range":
      return field === "min" || field === "max" ? { ...constraint, [field]: ivValue } : constraint;
    case "exact":
      return field === "value" ? { ...constraint, value: ivValue } : constraint;
    case "preferred":
      return field === "value" || field === "weight" ? { ...constraint, [field]: ivValue } : constraint;
    case "any":
    case "exact31":
      return constraint;
  }
};

const ConstraintEditor = ({
  stat,
  constraint,
  onChange,
}: {
  stat: StatKey;
  constraint: IvConstraint;
  onChange: (constraint: IvConstraint) => void;
}) => (
  <div className="rounded-md border border-slate-200 p-3">
    <div className="mb-2 flex items-center justify-between gap-3">
      <p className="font-bold">{fullStatLabels[stat]}</p>
      <select
        className="input max-w-44"
        value={constraint.kind}
        onChange={(event) => onChange(defaultForKind(event.target.value as IvConstraint["kind"]))}
      >
        {Object.entries(constraintLabel).map(([kind, label]) => (
          <option key={kind} value={kind}>
            {label}
          </option>
        ))}
      </select>
    </div>

    {constraint.kind === "min" || constraint.kind === "exact" || constraint.kind === "preferred" ? (
      <label className="grid gap-1">
        <span className="label">Valor</span>
        <input
          className="input"
          min={0}
          max={31}
          type="number"
          value={constraint.value}
          onChange={(event) =>
            onChange(updateConstraintNumber(constraint, "value", Number.parseInt(event.target.value || "0", 10)))
          }
        />
      </label>
    ) : null}

    {constraint.kind === "range" ? (
      <div className="grid grid-cols-2 gap-2">
        <label className="grid gap-1">
          <span className="label">Min.</span>
          <input
            className="input"
            min={0}
            max={31}
            type="number"
            value={constraint.min}
            onChange={(event) =>
              onChange(updateConstraintNumber(constraint, "min", Number.parseInt(event.target.value || "0", 10)))
            }
          />
        </label>
        <label className="grid gap-1">
          <span className="label">Max.</span>
          <input
            className="input"
            min={0}
            max={31}
            type="number"
            value={constraint.max}
            onChange={(event) =>
              onChange(updateConstraintNumber(constraint, "max", Number.parseInt(event.target.value || "0", 10)))
            }
          />
        </label>
      </div>
    ) : null}

    {constraint.kind === "preferred" ? (
      <label className="mt-2 grid gap-1">
        <span className="label">Peso</span>
        <input
          className="input"
          min={0}
          max={10}
          step={0.5}
          type="number"
          value={constraint.weight}
          onChange={(event) =>
            onChange(updateConstraintNumber(constraint, "weight", Number.parseFloat(event.target.value || "0")))
          }
        />
      </label>
    ) : null}
  </div>
);

export const TargetPage = () => {
  const { state, dispatch } = useSession();

  return (
    <section className="surface p-4">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-berry" />
        <h2 className="text-lg font-black">Objetivo de crianza</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="grid content-start gap-3">
          <SpeciesSelect
            label="Especie objetivo"
            value={state.target.speciesId}
            onChange={(speciesId) => dispatch({ type: "set-target-species", speciesId })}
          />
          <label className="grid gap-1">
            <span className="label">Sexo objetivo</span>
            <select
              className="input"
              value={state.target.sex}
              onChange={(event) =>
                dispatch({
                  type: "set-target-sex",
                  sex: event.target.value as typeof state.target.sex,
                })
              }
            >
              <option value="any">Cualquiera</option>
              <option value="male">Macho</option>
              <option value="female">Hembra</option>
              <option value="genderless">Sin genero</option>
            </select>
          </label>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            Las estadisticas marcadas como preferidas influyen en la puntuacion, pero no cuentan como requisito directo.
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {statKeys.map((stat) => (
            <ConstraintEditor
              key={stat}
              stat={stat}
              constraint={state.target.ivs[stat]}
              onChange={(constraint) => dispatch({ type: "set-target-constraint", stat, constraint })}
            />
          ))}
        </div>
      </div>
    </section>
  );
};
