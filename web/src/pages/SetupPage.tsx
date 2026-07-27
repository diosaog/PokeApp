import { CheckCircle2, HelpCircle, SlidersHorizontal } from "lucide-react";

import { breedingItems } from "@/domain/economy/items";
import type { InventoryEntry } from "@/domain/economy/types";
import { formatCurrency, formatMinutes } from "@/components/common/format";
import { useSession } from "@/state/sessionStore";
import { clamp } from "@/utils/math";

const numberValue = (value: string, fallback = 0): number => {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const SetupPage = () => {
  const { state, dispatch } = useSession();
  const { budget, profile, inventory } = state;

  const updateInventory = (itemId: keyof typeof inventory, patch: Partial<InventoryEntry>): void => {
    const current = inventory[itemId];
    dispatch({
      type: "set-inventory-entry",
      itemId,
      entry: {
        ...current,
        ...patch,
      },
    });
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_1.4fr]">
      <section className="surface p-4">
        <div className="mb-4 flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5 text-moss" />
          <h2 className="text-lg font-black">Perfil y presupuesto</h2>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="label">Dinero actual</span>
            <input
              className="input"
              min={0}
              type="number"
              value={budget.money}
              disabled={budget.unlimited}
              onChange={(event) =>
                dispatch({
                  type: "set-budget",
                  budget: { ...budget, money: Math.max(0, numberValue(event.target.value)) },
                })
              }
            />
          </label>
          <label className="grid gap-1">
            <span className="label">Metrica a optimizar</span>
            <select
              className="input"
              value={budget.metric}
              onChange={(event) =>
                dispatch({
                  type: "set-budget",
                  budget: { ...budget, metric: event.target.value === "cash" ? "cash" : "replacement" },
                })
              }
            >
              <option value="replacement">Coste economico</option>
              <option value="cash">Desembolso real</option>
            </select>
          </label>
          <label className="flex items-center gap-2 rounded-md border border-slate-200 p-3 text-sm font-semibold">
            <input
              type="checkbox"
              checked={budget.unlimited}
              onChange={(event) =>
                dispatch({
                  type: "set-budget",
                  budget: { ...budget, unlimited: event.target.checked },
                })
              }
            />
            Presupuesto ilimitado
          </label>
          <div className="rounded-md border border-slate-200 p-3 text-sm">
            <p className="font-bold">{profile.name}</p>
            <p className="text-slate-600">
              Crianza {formatCurrency(profile.economy.breedingBaseCost)} · {formatMinutes(profile.economy.breedingDurationMinutes)}
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="label">Coste crianza</span>
            <input
              className="input"
              min={0}
              type="number"
              value={profile.economy.breedingBaseCost}
              onChange={(event) =>
                dispatch({
                  type: "set-economy",
                  economy: { ...profile.economy, breedingBaseCost: numberValue(event.target.value) },
                })
              }
            />
          </label>
          <label className="grid gap-1">
            <span className="label">Forzar sexo</span>
            <input
              className="input"
              min={0}
              type="number"
              value={profile.economy.forcedSexCost}
              onChange={(event) =>
                dispatch({
                  type: "set-economy",
                  economy: { ...profile.economy, forcedSexCost: numberValue(event.target.value) },
                })
              }
            />
          </label>
          <label className="grid gap-1">
            <span className="label">Duracion crianza</span>
            <input
              className="input"
              min={0}
              type="number"
              value={profile.time.breedingDurationMinutes}
              onChange={(event) => {
                const minutes = numberValue(event.target.value);
                dispatch({
                  type: "set-time",
                  time: { ...profile.time, breedingDurationMinutes: minutes },
                });
                dispatch({
                  type: "set-economy",
                  economy: { ...profile.economy, breedingDurationMinutes: minutes },
                });
              }}
            />
          </label>
          <label className="grid gap-1">
            <span className="label">Ranuras</span>
            <input
              className="input"
              min={1}
              type="number"
              value={profile.time.breedingSlots}
              onChange={(event) =>
                dispatch({
                  type: "set-time",
                  time: { ...profile.time, breedingSlots: Math.max(1, Math.round(numberValue(event.target.value, 1))) },
                })
              }
            />
          </label>
        </div>
      </section>

      <section className="surface p-4">
        <div className="mb-4 flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-sea" />
          <h2 className="text-lg font-black">Reglas confirmadas y pendientes</h2>
        </div>
        <div className="grid gap-2">
          {profile.notices.map((notice) => (
            <div key={notice.id} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold">{notice.label}</p>
                <span
                  className={
                    notice.status === "confirmed"
                      ? "badge border-green-200 bg-green-50 text-green-800"
                      : "badge border-amber-200 bg-amber-50 text-amber-800"
                  }
                >
                  {notice.status === "confirmed" ? "Confirmado" : "Pendiente"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-600">{notice.details}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-2 font-bold text-amber-900">
            <HelpCircle className="h-4 w-4" />
            Enfriamiento de progenitores
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button
              className="btn-secondary"
              type="button"
              onClick={() => dispatch({ type: "set-cooldown-confirmation", value: "si_60" })}
            >
              Si, 60 minutos
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => dispatch({ type: "set-cooldown-confirmation", value: "none" })}
            >
              No existe
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => dispatch({ type: "set-cooldown-confirmation", value: "unknown" })}
            >
              No estoy seguro
            </button>
            <label className="flex items-center gap-2">
              <input
                className="input"
                min={0}
                type="number"
                value={profile.time.parentCooldownMinutes}
                onChange={(event) =>
                  dispatch({
                    type: "set-cooldown-confirmation",
                    value: "custom",
                    customMinutes: clamp(numberValue(event.target.value), 0, 600),
                  })
                }
              />
              <span className="text-sm font-semibold">min</span>
            </label>
          </div>
        </div>
      </section>

      <section className="surface p-4 xl:col-span-2">
        <h2 className="mb-4 text-lg font-black">Inventario de objetos</h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {breedingItems.map((item) => {
            const entry = inventory[item.id];
            return (
              <div key={item.id} className="rounded-md border border-slate-200 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold">{item.names.es}</p>
                    <p className="text-xs text-slate-600">{item.names.en}</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs font-bold">
                    <input
                      type="checkbox"
                      checked={entry.enabled}
                      onChange={(event) => updateInventory(item.id, { enabled: event.target.checked })}
                    />
                    Disponible
                  </label>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <label className="grid gap-1">
                    <span className="label">Unid.</span>
                    <input
                      className="input"
                      min={0}
                      type="number"
                      value={entry.owned}
                      onChange={(event) => updateInventory(item.id, { owned: Math.max(0, Math.round(numberValue(event.target.value))) })}
                    />
                  </label>
                  <label className="grid gap-1">
                    <span className="label">Precio</span>
                    <input
                      className="input"
                      min={0}
                      type="number"
                      value={entry.price}
                      onChange={(event) => updateInventory(item.id, { price: Math.max(0, numberValue(event.target.value)) })}
                    />
                  </label>
                  <label className="flex items-end gap-2 pb-2 text-xs font-bold">
                    <input
                      type="checkbox"
                      checked={entry.autoBuy}
                      onChange={(event) => updateInventory(item.id, { autoBuy: event.target.checked })}
                    />
                    Comprar
                  </label>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
