import { getSpeciesName } from "@/data/species";
import type { PokemonInstance } from "@/domain/pokemon/types";
import { sexLabels } from "@/domain/pokemon/types";

export const PokemonBadge = ({ pokemon }: { pokemon: PokemonInstance }) => {
  const name = pokemon.nickname || getSpeciesName(pokemon.speciesId);
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-sea text-sm font-black text-white">
        {initial}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold">{name}</p>
        <p className="truncate text-xs text-slate-600">
          {getSpeciesName(pokemon.speciesId)} · {sexLabels[pokemon.sex]}
        </p>
      </div>
    </div>
  );
};
