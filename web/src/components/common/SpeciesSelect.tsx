import { useMemo, useState } from "react";

import { findSpecies, getSpeciesName } from "@/data/species";

export const SpeciesSelect = ({
  value,
  onChange,
  label = "Especie",
}: {
  value: string;
  onChange: (speciesId: string) => void;
  label?: string;
}) => {
  const [query, setQuery] = useState("");
  const options = useMemo(() => findSpecies(query).slice(0, 20), [query]);

  return (
    <label className="grid gap-1">
      <span className="label">{label}</span>
      <input
        className="input"
        placeholder="Buscar por nombre"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <select
        className="input"
        data-testid="species-select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((species) => (
          <option key={species.id} value={species.id}>
            {species.names.es} / {species.names.en}
          </option>
        ))}
        {!options.some((species) => species.id === value) ? <option value={value}>{getSpeciesName(value)}</option> : null}
      </select>
    </label>
  );
};
