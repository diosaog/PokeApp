import { Copy, Lock, Plus, Shield, Trash2, Unlock } from "lucide-react";
import { useMemo, useState } from "react";

import { SpeciesSelect } from "@/components/common/SpeciesSelect";
import { StatGrid } from "@/components/common/StatGrid";
import { PokemonBadge } from "@/components/pokemon/PokemonBadge";
import { getSpeciesName, speciesById } from "@/data/species";
import { motivatingDemoPokemon } from "@/data/demoProject";
import type { PokemonInstance, PokemonSex } from "@/domain/pokemon/types";
import { sexLabels, statKeys } from "@/domain/pokemon/types";
import { createPokemonDraft, useSession } from "@/state/sessionStore";

const sanitizeDraft = (draft: PokemonInstance): PokemonInstance => {
  const species = speciesById.get(draft.speciesId);
  const sex = species?.genderless ? "genderless" : draft.sex;
  const clean: PokemonInstance = {
    id: draft.id,
    speciesId: draft.speciesId,
    sex,
    ivs: draft.ivs,
    canBreed: draft.canBreed,
    availableAtMinute: Math.max(0, Math.round(draft.availableAtMinute)),
    protected: draft.protected,
  };
  if (draft.nickname?.trim()) {
    clean.nickname = draft.nickname.trim();
  }
  if (draft.notes?.trim()) {
    clean.notes = draft.notes.trim();
  }
  if (draft.abilityId) {
    clean.abilityId = draft.abilityId;
  }
  if (draft.natureId) {
    clean.natureId = draft.natureId;
  }
  return clean;
};

export const BreedersPage = () => {
  const { state, dispatch } = useSession();
  const [draft, setDraft] = useState<PokemonInstance>(() => createPokemonDraft());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const filteredPokemon = useMemo(() => {
    const normalized = filter.trim().toLowerCase();
    if (!normalized) {
      return state.pokemon;
    }
    return state.pokemon.filter((pokemon) => {
      const species = getSpeciesName(pokemon.speciesId).toLowerCase();
      const nickname = pokemon.nickname?.toLowerCase() ?? "";
      return species.includes(normalized) || nickname.includes(normalized);
    });
  }, [filter, state.pokemon]);

  const resetDraft = (): void => {
    setDraft(createPokemonDraft());
    setEditingId(null);
  };

  const save = (): void => {
    const pokemon = sanitizeDraft(draft);
    dispatch({ type: editingId ? "update-pokemon" : "add-pokemon", pokemon });
    resetDraft();
  };

  const startEditing = (pokemon: PokemonInstance): void => {
    setDraft(pokemon);
    setEditingId(pokemon.id);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[460px_1fr]">
      <section className="surface p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-black">{editingId ? "Editar reproductor" : "Alta rapida"}</h2>
          <button className="btn-secondary" type="button" onClick={resetDraft}>
            <Plus className="h-4 w-4" />
            Nuevo
          </button>
        </div>

        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className="label">Mote</span>
            <input
              className="input"
              value={draft.nickname ?? ""}
              onChange={(event) => setDraft((current) => ({ ...current, nickname: event.target.value }))}
              placeholder="Opcional"
            />
          </label>
          <SpeciesSelect
            value={draft.speciesId}
            onChange={(speciesId) =>
              setDraft((current) => {
                const species = speciesById.get(speciesId);
                return { ...current, speciesId, sex: species?.genderless ? "genderless" : current.sex };
              })
            }
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1">
              <span className="label">Sexo</span>
              <select
                className="input"
                data-testid="pokemon-sex"
                value={draft.sex}
                onChange={(event) => setDraft((current) => ({ ...current, sex: event.target.value as PokemonSex }))}
              >
                {Object.entries(sexLabels).map(([sex, label]) => (
                  <option key={sex} value={sex}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1">
              <span className="label">Disponible en min.</span>
              <input
                className="input"
                min={0}
                type="number"
                value={draft.availableAtMinute}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    availableAtMinute: Math.max(0, Number.parseInt(event.target.value || "0", 10)),
                  }))
                }
              />
            </label>
          </div>
          <StatGrid value={draft.ivs} onChange={(ivs) => setDraft((current) => ({ ...current, ivs }))} />
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex items-center gap-2 rounded-md border border-slate-200 p-3 text-sm font-semibold">
              <input
                type="checkbox"
                checked={draft.canBreed}
                onChange={(event) => setDraft((current) => ({ ...current, canBreed: event.target.checked }))}
              />
              Puede criar
            </label>
            <label className="flex items-center gap-2 rounded-md border border-slate-200 p-3 text-sm font-semibold">
              <input
                type="checkbox"
                checked={draft.protected}
                onChange={(event) => setDraft((current) => ({ ...current, protected: event.target.checked }))}
              />
              Protegido
            </label>
          </div>
          <label className="grid gap-1">
            <span className="label">Notas</span>
            <textarea
              className="input min-h-20"
              value={draft.notes ?? ""}
              onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>
          <button className="btn-primary" type="button" onClick={save}>
            <Shield className="h-4 w-4" />
            {editingId ? "Guardar cambios" : "Guardar y anadir otro"}
          </button>
        </div>
      </section>

      <section className="surface p-4">
        <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_auto]">
          <div>
            <h2 className="text-lg font-black">Reproductores</h2>
            <p className="text-sm text-slate-600">{state.pokemon.length} Pokemon en memoria de esta sesion</p>
          </div>
          <button
            className="btn-secondary"
            type="button"
            onClick={() => dispatch({ type: "load-demo", pokemon: motivatingDemoPokemon })}
          >
            Cargar ejemplo sin sexos
          </button>
        </div>
        <input
          className="input mb-3"
          placeholder="Filtrar por mote o especie"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
        <div className="overflow-auto">
          <table className="min-w-full border-separate border-spacing-0 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-600">
                <th className="border-b border-slate-200 p-2">Pokemon</th>
                {statKeys.map((stat) => (
                  <th key={stat} className="border-b border-slate-200 p-2 text-center">
                    {stat}
                  </th>
                ))}
                <th className="border-b border-slate-200 p-2">Estado</th>
                <th className="border-b border-slate-200 p-2 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredPokemon.map((pokemon) => (
                <tr key={pokemon.id} className="align-middle">
                  <td className="border-b border-slate-100 p-2">
                    <button className="text-left" type="button" onClick={() => startEditing(pokemon)}>
                      <PokemonBadge pokemon={pokemon} />
                    </button>
                  </td>
                  {statKeys.map((stat) => (
                    <td key={stat} className="border-b border-slate-100 p-2 text-center font-semibold">
                      {pokemon.ivs[stat]}
                    </td>
                  ))}
                  <td className="border-b border-slate-100 p-2">
                    <div className="flex flex-wrap gap-1">
                      {!pokemon.canBreed ? <span className="badge border-red-200 bg-red-50 text-red-800">Esteril</span> : null}
                      {pokemon.protected ? <span className="badge border-slate-200 bg-slate-100">Protegido</span> : null}
                      {pokemon.sex === "unknown" ? <span className="badge border-amber-200 bg-amber-50 text-amber-800">Sexo?</span> : null}
                    </div>
                  </td>
                  <td className="border-b border-slate-100 p-2">
                    <div className="flex justify-end gap-1">
                      <button
                        className="btn-secondary h-9 min-h-9 w-9 px-0"
                        type="button"
                        title="Duplicar"
                        onClick={() => dispatch({ type: "duplicate-pokemon", id: pokemon.id })}
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                      <button
                        className="btn-secondary h-9 min-h-9 w-9 px-0"
                        type="button"
                        title={pokemon.protected ? "Desproteger" : "Proteger"}
                        onClick={() => dispatch({ type: "toggle-protected", id: pokemon.id })}
                      >
                        {pokemon.protected ? <Unlock className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                      </button>
                      <button
                        className="btn-danger h-9 min-h-9 w-9 px-0"
                        type="button"
                        title="Eliminar"
                        onClick={() => {
                          if (window.confirm("Eliminar este Pokemon?")) {
                            dispatch({ type: "delete-pokemon", id: pokemon.id });
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredPokemon.length === 0 ? (
                <tr>
                  <td className="p-6 text-center text-slate-500" colSpan={9}>
                    No hay reproductores que mostrar.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
