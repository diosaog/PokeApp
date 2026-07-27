import type { IvSpread, StatKey } from "@/domain/pokemon/types";
import { statKeys, statLabels } from "@/domain/pokemon/types";
import { clamp } from "@/utils/math";

export const StatGrid = ({
  value,
  onChange,
}: {
  value: IvSpread;
  onChange: (next: IvSpread) => void;
}) => {
  const update = (stat: StatKey, raw: string): void => {
    const parsed = Number.parseInt(raw, 10);
    onChange({
      ...value,
      [stat]: Number.isNaN(parsed) ? 0 : clamp(parsed, 0, 31),
    });
  };

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
      {statKeys.map((stat) => (
        <label key={stat} className="grid gap-1">
          <span className="label">{statLabels[stat]}</span>
          <input
            className="input text-center"
            data-testid={`iv-${stat}`}
            min={0}
            max={31}
            type="number"
            value={value[stat]}
            onChange={(event) => update(stat, event.target.value)}
          />
        </label>
      ))}
    </div>
  );
};
