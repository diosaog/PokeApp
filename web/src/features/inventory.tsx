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

// The competitive decision (adjudicated) and each save's physical delivery are
// shown separately; only RECONCILED/COMMITTED means both saves are verified.
export const transferLabels: Record<string, string> = {
  REQUESTED: "Robo solicitado · PokeApp comprueba que es válido",
  ELIGIBILITY_VERIFIED: "Robo válido · PokeApp lo está adjudicando",
  COMPETITIVELY_ADJUDICATED: "Robo adjudicado · definitivo",
  RECONCILED: "Robo completado · entregado en las dos partidas",
  PREPARING: "Robo pendiente · preparando guardados",
  WAITING_OTHER: "Esperando al otro entrenador",
  PENDING_SOURCE: "Guardados preparados · pendiente de la primera parte",
  VERIFYING_SOURCE: "Primera parte aplicada · verificación en curso",
  PENDING_DESTINATION: "Primera parte verificada · esperando la segunda parte",
  VERIFYING_BOTH: "Segunda parte aplicada · verificación en curso",
  BOTH_VERIFIED_PENDING_IDENTITY: "Verificación en curso",
  COMMITTED: "Robo completado",
  CANCELLED: "Robo cancelado · el objeto no se ha consumido",
  BLOCKED_UNCERTAIN: "Operación bloqueada",
};
export const obligationLabels: Record<string, string> = {
  DONOR_PHYSICAL_PENDING:
    "Retirada pendiente: abre tu Launcher con el juego cerrado. Tu sincronización normal está en pausa hasta entonces.",
  DONOR_RECOVERY_REQUIRED:
    "PokeApp no pudo preparar la retirada en tu partida actual. Abre tu Launcher para reintentarlo.",
  DONOR_VERIFIED: "Retirada verificada en tu partida.",
  DONOR_ABSENT_VERIFIED: "Tu partida ya no tenía ese Pokémon: verificado.",
  DONOR_BLOCKED_UNCERTAIN: "Retirada bloqueada: recuperación asistida.",
  RECIPIENT_PHYSICAL_PENDING:
    "Pendiente de recepción: aún no está en tu partida y no puedes usarlo. Abre tu Launcher para recibirlo.",
  RECIPIENT_RECOVERY_REQUIRED:
    "PokeApp no pudo preparar la entrega en tu partida actual (¿cajas llenas?). Libera un hueco y abre tu Launcher.",
  RECIPIENT_VERIFIED: "Pokémon recibido y verificado en tu partida.",
  RECIPIENT_BLOCKED_UNCERTAIN: "Entrega bloqueada: recuperación asistida.",
};
// Only the requester, and only before PokeApp decides; never the victim.
const withdrawable = [
  "REQUESTED",
  "PREPARING",
  "WAITING_OTHER",
  "PENDING_SOURCE",
];
// Inside PokeApp Launcher this same web adds a marker to its user agent; the
// Launcher intercepts the plain link below and opens its native quick-item panel.
const insideLauncher = () =>
  typeof navigator !== "undefined" &&
  navigator.userAgent.includes("PokeAppLauncher/");

export function Inventory() {
  const { season } = useApp();
  const q = useRead<Model<"InventoryRead">>(
    `/v1/read/seasons/${season}/inventory`,
    !!season,
  );
  const transfers = useRead<Model<"TransferListResponse">>(
    `/v1/seasons/${season}/transfers`,
    !!season,
  );
  const robberyEnabled = transfers.data?.transfer_enabled === true;
  const transferFor = (purchaseId: string) =>
    transfers.data?.items.find((t) => t.purchase_id === purchaseId);
  const cmd = useCommand([
    `/v1/seasons/${season}/transfers`,
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
    if (!purchase) return;
    const robbery = purchase.item_code === "robar_pokemon" && robberyEnabled;
    if (physicalItem(purchase.item_code) && !robbery) return;
    if (
      await cmd.execute(
        robbery
          ? `/v1/seasons/${season}/shop/purchases/${purchase.id}/transfer`
          : `/v1/seasons/${season}/shop/purchases/${purchase.id}/redemptions`,
        {
          pokemon_entity_id: target.pokemon_entity_id,
        } satisfies Model<"RedemptionBody"> & Model<"TransferRequestBody">,
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
      {!!q.data?.unlimited_items?.length && (
        <section aria-labelledby="unlimited-title">
          <h3 id="unlimited-title">Objetos ilimitados</h3>
          <div className="inventory-grid">
            {q.data.unlimited_items.map((item) => (
              <Card key={item.code} className="inventory-card">
                <div className="inventory-item">
                  <ItemIcon name={item.name} />
                  <h3>{item.label}</h3>
                </div>
                <Tag>∞ · Gratis</Tag>
                <p>{item.description}</p>
                {insideLauncher() ? (
                  <a href={`/__launcher/quick-items/${item.code}`}>
                    Añadir a mi partida
                  </a>
                ) : (
                  <p className="muted">
                    Disponible en PokeApp Launcher para añadirlo a tu partida.
                  </p>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}
      <CommandState command={cmd} />
      {q.isPending ? (
        <Loading />
      ) : q.data?.purchases.length ? (
        <div className="inventory-grid">
          {q.data.purchases.map((item) => {
            const transfer = transferFor(item.id);
            const robbery =
              item.item_code === "robar_pokemon" && robberyEnabled && !transfer;
            return (
              <Card key={item.id} className="inventory-card">
                <div className="inventory-item">
                  <ItemIcon name={item.item_name} code={item.item_code} />
                  <h3>{pokemonName("item", item.item_name)}</h3>
                </div>
                <Tag>
                  {transfer
                    ? (transferLabels[transfer.status] ??
                      "Estado del robo no disponible")
                    : physicalItem(item.item_code)
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
                  (transfer ? (
                    <p>
                      El robo solo se confirma cuando PokeApp verifica los dos
                      guardados. Mantén el Launcher abierto y sigue sus pasos.
                    </p>
                  ) : physicalItem(item.item_code) && !robbery ? (
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

      {!!transfers.data?.items.length && (
        <section aria-labelledby="transfers-title">
          <h3 id="transfers-title">Robos entre guardados</h3>
          {transfers.data.items.map((transfer) => (
            <Card key={transfer.authorization_id} className="inventory-card">
              <p>
                {transfer.side === "destination"
                  ? "Has solicitado este robo."
                  : "PokeApp ha decidido un robo sobre uno de tus Pokémon. No necesita tu aprobación."}
              </p>
              <Tag>
                {transferLabels[transfer.status] ??
                  "Estado del robo no disponible"}
              </Tag>
              {transfer.obligation && (
                <p>
                  {obligationLabels[transfer.obligation] ??
                    "Estado de la entrega no disponible"}
                </p>
              )}
              {transfer.side === "destination" &&
                withdrawable.includes(transfer.status) && (
                  <button
                    type="button"
                    disabled={cmd.pending}
                    onClick={() =>
                      cmd.execute(
                        `/v1/seasons/${season}/transfers/${transfer.authorization_id}/cancel`,
                        {},
                      )
                    }
                  >
                    Cancelar robo
                  </button>
                )}
            </Card>
          ))}
        </section>
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
