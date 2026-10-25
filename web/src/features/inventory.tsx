import { useState } from "react";
import type { Model } from "../api/types";
import { pokemonName } from "../pokemon/localization";
import { ItemIcon, TrainerPhoto } from "../pokemon/presentation";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Loading,
  Notice,
  Tag,
  date,
  useCommand,
} from "../ui";
import { PokemonSelectorModal, type PokemonTarget } from "./pokemon-selector";

const pokemonActions = [
  "blindar_pokemon",
  "revivir_pokemon",
  "robar_pokemon",
  "robbery_shield_voucher",
];

function isDead(target: PokemonTarget) {
  return target.location.toLowerCase().startsWith("caja 8");
}

export const itemUseLabels: Record<string, string> = {
  AVAILABLE: "Objeto disponible",
  LEGACY_PENDING: "Canje histórico · archivo pendiente de verificar",
  EXPIRED: "Autorización caducada · requiere revisión",
  UNKNOWN: "Estado físico no disponible",
  PREPARED: "Aplicación pendiente",
  PENDING_APPLICATION: "Aplicación pendiente",
  APPLIED_VERIFIED: "Aplicación verificada",
  FAILED_RECOVERABLE: "Error recuperable",
  RECOVERY_REQUIRED: "Recuperación necesaria",
  BLOCKED_UNCERTAIN: "Operación bloqueada",
};
const physicalItem = (code: string) =>
  ["revivir_pokemon", "robar_pokemon"].includes(code);

export function Inventory() {
  const { season } = useApp();
  const q = useRead<Model<"InventoryRead">>(
    `/v1/read/seasons/${season}/inventory`,
    !!season,
  );
  const cmd = useCommand([
    `/v1/read/seasons/${season}/inventory`,
    `/v1/read/seasons/${season}/overview`,
    `/v1/read/seasons/${season}/league`,
    `/v1/seasons/${season}/initial-assignment`,
  ]);
  const [purchase, setPurchase] = useState<Model<"PurchaseRead"> | null>(null);
  const [robberyTrainer, setRobberyTrainer] = useState<string | null>(null);
  const trainers = useRead<Model<"TrainerRead">[]>(
    "/v1/read/trainers",
    !!season && !!purchase,
  );

  const candidateTrainers =
    trainers.data?.filter((trainer) =>
      q.data?.targets.some(
        (target) =>
          target.visibility === "public_team_lock" &&
          target.trainer_id === trainer.id &&
          !target.pokemon.status_flags?.includes("robado") &&
          !target.pokemon.status_flags?.includes("blindado"),
      ),
    ) || [];
  const selectedTrainer = candidateTrainers.find(
    (trainer) => trainer.id === robberyTrainer,
  );
  const targets: PokemonTarget[] =
    q.data?.targets.filter((target) => {
      if (purchase?.item_code === "robar_pokemon") {
        return (
          target.visibility === "public_team_lock" &&
          target.trainer_id === robberyTrainer &&
          !target.pokemon.status_flags?.includes("robado") &&
          !target.pokemon.status_flags?.includes("blindado")
        );
      }
      if (target.visibility !== "own") return false;
      if (purchase?.item_code === "revivir_pokemon") return isDead(target);
      if (purchase?.item_code === "blindar_pokemon")
        return !isDead(target) && target.can_shield;
      if (purchase?.item_code === "robbery_shield_voucher")
        return target.can_shield;
      return false;
    }) || [];
  const usesPokemonSelector = pokemonActions.includes(
    purchase?.item_code || "",
  );

  async function redeem(target: PokemonTarget) {
    if (!purchase || physicalItem(purchase.item_code)) return;
    if (
      await cmd.execute(
        `/v1/seasons/${season}/shop/purchases/${purchase.id}/redemptions`,
        {
          pokemon_entity_id: target.pokemon_entity_id,
        } satisfies Model<"RedemptionBody">,
      )
    ) {
      setPurchase(null);
      setRobberyTrainer(null);
    }
  }

  return (
    <>
      <h2>Inventario</h2>
      <p className="muted">Tus compras y vales · disponibles para canjear</p>
      <Notice error={q.error} />
      <CommandState command={cmd} />
      {q.isPending ? (
        <Loading />
      ) : q.data?.purchases.length ? (
        <div className="inventory-grid">
          {q.data.purchases.map((item) => {
            return (
              <Card key={item.id} className="inventory-card">
                <div className="inventory-item">
                  <ItemIcon name={item.item_name} code={item.item_code} />
                  <h3>{pokemonName("item", item.item_name)}</h3>
                </div>
                <Tag>
                  {physicalItem(item.item_code)
                    ? (itemUseLabels[item.physical_state ?? "UNKNOWN"] ??
                      "Estado físico no disponible")
                    : ((
                        {
                          pending: "Objeto disponible",
                          used: "Canjeado",
                          cancelled: "Cancelado",
                          refunded: "Reembolsado",
                        } as Record<string, string>
                      )[item.status] ?? "Estado no disponible")}
                </Tag>
                {item.acquisition_type === "reward" && (
                  <Tag>Vale de recompensa</Tag>
                )}
                <p>
                  {date(item.purchased_at)} · {item.total_price} PK₽
                </p>
                {item.status === "pending" &&
                  (physicalItem(item.item_code) ? (
                    <p>
                      La aplicación física mediante Launcher aún no está
                      habilitada. El objeto se conserva sin consumir.
                    </p>
                  ) : pokemonActions.includes(item.item_code) ? (
                    <button
                      type="button"
                      onClick={() => {
                        setPurchase(item);
                        setRobberyTrainer(null);
                      }}
                    >
                      Canjear
                    </button>
                  ) : (
                    <p>
                      Este artículo todavía no tiene un canje disponible en
                      PokeApp.
                    </p>
                  ))}
              </Card>
            );
          })}
        </div>
      ) : (
        <Empty>Aún no hay compras ni vales registrados.</Empty>
      )}

      {purchase?.item_code === "robar_pokemon" && !robberyTrainer && (
        <TrainerPickerModal
          trainers={candidateTrainers}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setPurchase(null);
          }}
          onSelect={setRobberyTrainer}
        />
      )}
      {purchase &&
        usesPokemonSelector &&
        (purchase.item_code !== "robar_pokemon" || robberyTrainer) && (
          <PokemonSelectorModal
            title={`Canjear ${pokemonName("item", purchase.item_name)}`}
            targets={targets}
            onClose={() => {
              if (!cmd.pending && !cmd.uncertain) {
                setPurchase(null);
                setRobberyTrainer(null);
              }
            }}
            onConfirm={redeem}
            confirmLabel={
              purchase.item_code === "blindar_pokemon"
                ? "Sí, blindar"
                : purchase.item_code === "revivir_pokemon"
                  ? "Sí, revivir"
                  : purchase.item_code === "robbery_shield_voucher"
                    ? "Sí, blindar"
                    : "Sí, robar"
            }
            confirmation={(target) =>
              purchase.item_code === "robar_pokemon"
                ? `¿Quieres robar a ${target.pokemon.nickname || target.pokemon.species} de ${selectedTrainer?.display_name || "este entrenador"}?`
                : purchase.item_code === "revivir_pokemon"
                  ? `¿Quieres revivir a ${target.pokemon.nickname || target.pokemon.species}?`
                  : `¿Quieres blindar a ${target.pokemon.nickname || target.pokemon.species}?`
            }
            emptyText={
              purchase.item_code === "revivir_pokemon"
                ? "No hay Pokémon muertos disponibles para revivir."
                : purchase.item_code === "robar_pokemon"
                  ? "Ese entrenador no tiene Pokémon públicos disponibles para robar."
                  : "No hay Pokémon vivos elegibles para blindar."
            }
          />
        )}
    </>
  );
}

function TrainerPickerModal({
  trainers,
  onClose,
  onSelect,
}: {
  trainers: Model<"TrainerRead">[];
  onClose: () => void;
  onSelect: (trainerId: string) => void;
}) {
  return (
    <div className="trainer-picker-layer">
      <div
        className="trainer-picker-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="trainer-picker-title"
      >
        <div className="dialog-heading">
          <h2 id="trainer-picker-title">Elige un entrenador</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Cerrar"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <p>Después elegirás un Pokémon público de su equipo oficial.</p>
        <div className="trainer-selector-grid">
          {trainers.map((trainer) => (
            <button
              type="button"
              className="trainer-selector-card"
              key={trainer.id}
              onClick={() => onSelect(trainer.id)}
            >
              <TrainerPhoto name={trainer.display_name} />
              <span>{trainer.display_name}</span>
            </button>
          ))}
        </div>
        {!trainers.length && (
          <Empty>No hay rivales con un Pokémon público disponible.</Empty>
        )}
      </div>
    </div>
  );
}
