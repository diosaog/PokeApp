import { AlertTriangle, Clock, Coins, Info, Trophy } from "lucide-react";

import { formatCurrency, formatMinutes, formatProbability } from "@/components/common/format";
import { itemById } from "@/domain/economy/items";
import type { BreedingAction } from "@/domain/optimization/types";
import type { PokemonInstance } from "@/domain/pokemon/types";
import { getEggGroupName, getSpeciesName } from "@/data/species";
import { PokemonBadge } from "@/components/pokemon/PokemonBadge";

const itemLabel = (itemId: string): string => itemById.get(itemId as never)?.names.es ?? itemId;

export const RecommendationPanel = ({
  action,
  pokemon,
  title = "Mejor siguiente crianza",
}: {
  action: BreedingAction;
  pokemon: PokemonInstance[];
  title?: string;
}) => {
  const parentA = pokemon.find((candidate) => candidate.id === action.parentAId);
  const parentB = pokemon.find((candidate) => candidate.id === action.parentBId);
  const mother = pokemon.find((candidate) => candidate.id === action.motherId);
  const father = pokemon.find((candidate) => candidate.id === action.fatherId);

  return (
    <article className="surface p-4">
      <div className="mb-4 flex items-center gap-2">
        <Trophy className="h-5 w-5 text-apricot" />
        <h2 className="text-lg font-black uppercase tracking-normal">{title}</h2>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-slate-200 p-3">
          <p className="label mb-2">Progenitores</p>
          <div className="grid gap-3">
            {parentA ? <PokemonBadge pokemon={parentA} /> : null}
            {parentB ? <PokemonBadge pokemon={parentB} /> : null}
          </div>
          <div className="mt-3 text-sm text-slate-700">
            <p>Madre: {mother ? mother.nickname || getSpeciesName(mother.speciesId) : "Sin confirmar"}</p>
            <p>Padre: {father ? father.nickname || getSpeciesName(father.speciesId) : "Sin confirmar"}</p>
          </div>
        </div>

        <div className="rounded-md border border-slate-200 p-3">
          <p className="label mb-2">Descendencia y compatibilidad</p>
          <p className="text-xl font-black">{getSpeciesName(action.offspringSpeciesId)}</p>
          <p className="text-sm text-slate-600">
            Grupo huevo: {action.sharedEggGroups.map(getEggGroupName).join(", ")}
          </p>
          <p className="mt-2 text-sm">
            Sexo: {action.forcedSex ? `Forzar ${action.forcedSex}` : "No forzar"}
          </p>
        </div>

        <div className="rounded-md border border-slate-200 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Coins className="h-4 w-4 text-moss" />
            <p className="label">Coste</p>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt>Crianza</dt>
            <dd className="text-right font-bold">{formatCurrency(action.cost.breedingCost)}</dd>
            <dt>Objetos comprados</dt>
            <dd className="text-right font-bold">{formatCurrency(action.cost.purchasedItemsCost)}</dd>
            <dt>Valor consumido</dt>
            <dd className="text-right font-bold">{formatCurrency(action.cost.consumedItemsValue)}</dd>
            <dt>Forzar sexo</dt>
            <dd className="text-right font-bold">{formatCurrency(action.cost.forcedSexCost)}</dd>
            <dt>Total directo</dt>
            <dd className="text-right font-black">{formatCurrency(action.cost.directCashCost)}</dd>
            <dt>Coste esperado</dt>
            <dd className="text-right font-black">{formatCurrency(action.expectedTotalCost)}</dd>
          </dl>
        </div>

        <div className="rounded-md border border-slate-200 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Clock className="h-4 w-4 text-sea" />
            <p className="label">Tiempo y probabilidad</p>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt>Intento</dt>
            <dd className="text-right font-bold">{formatMinutes(action.schedule.clockMinutes)}</dd>
            <dt>Tiempo esperado</dt>
            <dd className="text-right font-black">{formatMinutes(action.expectedTotalMinutes)}</dd>
            <dt>Objetivo directo</dt>
            <dd className="text-right font-bold">{formatProbability(action.directTargetProbability)}</dd>
            <dt>Reproductor util</dt>
            <dd className="text-right font-bold">{formatProbability(action.usefulBreederProbability)}</dd>
          </dl>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-slate-200 p-3">
        <p className="label mb-2">Objetos</p>
        {action.items.length === 0 ? (
          <p className="text-sm text-slate-600">Sin objetos.</p>
        ) : (
          <ul className="grid gap-1 text-sm">
            {action.items.map((item) => (
              <li key={`${item.parent}-${item.itemId}`}>
                {item.parent === "parentA" ? "Primer progenitor" : "Segundo progenitor"}: {itemLabel(item.itemId)}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-slate-200 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Info className="h-4 w-4 text-sea" />
            <p className="label">Motivo</p>
          </div>
          <ul className="grid gap-1 text-sm text-slate-700">
            {action.explanation.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <p className="label mb-2">Como se calculo</p>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt>Profundidad</dt>
            <dd className="text-right font-bold">{action.howCalculated.depth}</dd>
            <dt>Acciones</dt>
            <dd className="text-right font-bold">{action.howCalculated.actionCount}</dd>
            <dt>Estados</dt>
            <dd className="text-right font-bold">{action.howCalculated.statesExplored}</dd>
            <dt>Semilla</dt>
            <dd className="text-right font-bold">{action.howCalculated.seed}</dd>
            <dt>Calculo</dt>
            <dd className="text-right font-bold">{action.howCalculated.elapsedMs} ms</dd>
          </dl>
        </div>
      </div>

      {action.warnings.length > 0 ? (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="mb-2 flex items-center gap-2 font-bold text-amber-900">
            <AlertTriangle className="h-4 w-4" />
            Advertencias
          </div>
          <ul className="grid gap-1 text-sm text-amber-900">
            {action.warnings.map((warning) => (
              <li key={`${warning.code}-${warning.message}`}>{warning.message}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
};
