import { useState } from "react";
import { Link } from "react-router-dom";
import type { Model } from "../api/types";
import { pokemonName } from "../pokemon/localization";
import { ItemIcon, TrainerPhoto } from "../pokemon/presentation";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Loading,
  Modal,
  Notice,
  Tag,
  date,
  useCommand,
} from "../ui";
import { PokemonSelectorModal, type PokemonTarget } from "./pokemon-selector";
import {
  deliveriesPath,
  friendshipPath,
  infiniteItemPath,
  insideLauncher,
  launcherDeliversShopObjects,
  launcherRaisesFriendship,
  launcherRevives,
  launcherTrainsPokemon,
  revivePath,
  shopObjectsPath,
  trainingItemPath,
} from "../launcher";
import { gameName } from "./progress";
import { LauncherDownload } from "./launcher-download";

const pokemonActions = [
  "blindar_pokemon",
  "revivir_pokemon",
  "robar_pokemon",
  "robbery_shield_voucher",
];

// The trainer's own dead box (070: Box 8 unless the administrator set another).
function isDead(target: PokemonTarget, deadBox: number) {
  return Number(/^caja (\d+)/i.exec(target.location)?.[1]) === deadBox;
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
const physicalCodes = ["revivir_pokemon", "robar_pokemon"];

// 072: a pending paid object goes to the bag through PokeApp Launcher (once);
// Captura Extra is used here; what the game cannot hold says so honestly.
function ObjectUse({
  purchase,
  leagueGame,
  disabled,
  onUse,
}: {
  purchase: Model<"PurchaseRead">;
  leagueGame?: string | null;
  disabled: boolean;
  onUse: () => void;
}) {
  const use = purchase.use;
  if (
    use?.mode === "training" ||
    ["menta_naturaleza", "chapa_plateada", "chapa_dorada"].includes(
      purchase.item_code ?? "",
    )
  ) {
    const name =
      purchase.item_code === "menta_naturaleza"
        ? "Menta de Naturaleza"
        : purchase.item_code === "chapa_plateada"
          ? "Chapa Plateada"
          : "Chapa Dorada";
    return insideLauncher() ? (
      launcherTrainsPokemon() ? (
        <Link
          className="button primary"
          to={trainingItemPath(purchase.item_code)}
        >
          {purchase.training_status === "RESERVED"
            ? "Comprobar aplicación"
            : `Usar ${name}`}
        </Link>
      ) : (
        <p className="muted">
          Actualiza PokeApp Launcher a la versión 0.26.9 o posterior para usar{" "}
          {name}.
        </p>
      )
    ) : (
      <p className="muted">
        Usa {name} desde tu inventario en PokeApp Launcher 0.26.9 o posterior.
      </p>
    );
  }
  if (purchase.delivery?.status === "RESERVED")
    return (
      <p className="muted">PokeApp Launcher la está añadiendo a tu bolsa.</p>
    );
  if (use?.mode === "permission")
    return (
      <button type="button" disabled={disabled} onClick={onUse}>
        Usar
      </button>
    );
  if (use?.mode === "unavailable" || use?.compatible === false)
    return (
      <p className="muted">
        {use.mode === "unavailable"
          ? "No existe en los juegos de 3DS."
          : `No existe en tu Pokémon ${gameName(leagueGame)}.`}{" "}
        El administrador puede devolverte sus monedas.
      </p>
    );
  if (use?.mode === "bag" || use?.mode === "choice")
    return insideLauncher() ? (
      launcherDeliversShopObjects() ? (
        <Link className="button primary" to={shopObjectsPath}>
          Añadir a la bolsa
        </Link>
      ) : (
        <p className="muted">
          Actualiza PokeApp Launcher para añadirla a tu bolsa.
        </p>
      )
    ) : (
      <p className="muted">
        Se añade a la bolsa de tu partida con PokeApp Launcher.
      </p>
    );
  return <p className="muted">Sin canje disponible.</p>;
}

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
// Why a request ended without effect; the comodín stays available.
function cancelledReason(reason?: string | null) {
  if (reason === "TRANSFER_EXPIRED")
    return "La solicitud caducó antes de poder comprobarse.";
  if (reason?.startsWith("TRANSFER_PLAN_"))
    return "No se pudo preparar. Comprueba que tienes un hueco libre en las Cajas 1 a 6 y vuelve a intentarlo.";
  return null;
}

export function Inventory() {
  const { season, me } = useApp();
  const q = useRead<Model<"InventoryRead">>(
    `/v1/read/seasons/${season}/inventory`,
    !!season,
  );
  // An API from before the Launcher item flow omits `physical_items`: revive
  // and robbery then keep that API's direct redemption and no robbery reads.
  const launcherFlow = q.data?.physical_items === true;
  const physicalItem = (code: string) =>
    launcherFlow && physicalCodes.includes(code);
  const transfers = useRead<Model<"TransferListResponse">>(
    `/v1/seasons/${season}/transfers`,
    !!season && launcherFlow,
  );
  const robberyEnabled = transfers.data?.transfer_enabled === true;
  // A cancelled attempt leaves the comodín free for another one.
  const transferFor = (purchaseId: string) =>
    transfers.data?.items.find(
      (t) => t.purchase_id === purchaseId && t.status !== "CANCELLED",
    );
  const cmd = useCommand([
    `/v1/seasons/${season}/transfers`,
    `/v1/read/seasons/${season}/inventory`,
    `/v1/read/seasons/${season}/overview`,
    `/v1/read/seasons/${season}/league`,
    `/v1/seasons/${season}/initial-assignment`,
  ]);
  const [purchase, setPurchase] = useState<Model<"PurchaseRead"> | null>(null);
  const [robberyTrainer, setRobberyTrainer] = useState<string | null>(null);
  const [unlimitedInfo, setUnlimitedInfo] = useState<
    NonNullable<Model<"InventoryRead">["unlimited_items"]>[number] | null
  >(null);
  // Rotation, rivals and their Pokémon are the server's: nothing is decided here.
  const board = useRead<Model<"RobberyBoardResponse">>(
    `/v1/seasons/${season}/robbery/board`,
    !!season && purchase?.item_code === "robar_pokemon",
  );
  const league = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season && !!purchase,
  );
  const deadBox =
    league.data?.rows?.find((row) => row.trainer_id === me?.trainer_id)
      ?.dead_box_number ?? 7;

  const selectedTrainer = board.data?.trainers.find(
    (trainer) => trainer.trainer_id === robberyTrainer,
  );
  const targets: PokemonTarget[] =
    purchase?.item_code === "robar_pokemon"
      ? (selectedTrainer?.targets ?? []).map((target) => ({
          ...target,
          trainer_id: selectedTrainer!.trainer_id,
          visibility: "rival_save" as const,
          can_shield: false,
        }))
      : (q.data?.targets ?? []).filter((target) => {
          if (target.visibility !== "own") return false;
          if (purchase?.item_code === "revivir_pokemon")
            return isDead(target, deadBox);
          if (purchase?.item_code === "blindar_pokemon")
            return !isDead(target, deadBox) && target.can_shield;
          if (purchase?.item_code === "robbery_shield_voucher")
            return target.can_shield;
          return false;
        });
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
        <section
          aria-labelledby="unlimited-title"
          className="unlimited-section"
        >
          <h3 id="unlimited-title">Objetos ilimitados</h3>
          {/* Compact rows: a small icon, the name, ∞ and one action. Inside
              PokeApp Launcher the action opens its native popup (quantity,
              bag limit, confirmation); the effect goes to the bag, never to a
              Pokémon. */}
          <ul className="unlimited-list">
            {q.data.unlimited_items.map((item) => (
              <li key={item.code} className="unlimited-row">
                <ItemIcon name={item.name} />
                <span className="unlimited-text">
                  <strong>{item.label}</strong>
                  <span id={`unlimited-${item.code}`}>{item.description}</span>
                </span>
                <Tag>∞ · Gratis</Tag>
                {insideLauncher() ? (
                  <Link
                    className="button primary"
                    to={infiniteItemPath(item.code)}
                    aria-describedby={`unlimited-${item.code}`}
                  >
                    Añadir a la bolsa
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="button primary"
                    aria-describedby={`unlimited-${item.code}`}
                    onClick={() => setUnlimitedInfo(item)}
                  >
                    Añadir a la bolsa
                  </button>
                )}
              </li>
            ))}
            {/* «Felicidad máxima»: free and unlimited, applied by PokeApp
                Launcher 0.26.12+ to one Pokémon of the current party (its
                native dialog shows the party, the current value and asks for
                confirmation). Shown only where it can work: never a promise
                to a browser or an older Launcher. */}
            {insideLauncher() && launcherRaisesFriendship() && (
              <li className="unlimited-row">
                <ItemIcon name="Soothe Bell" />
                <span className="unlimited-text">
                  <strong>Felicidad máxima</strong>
                  <span id="unlimited-felicidad">
                    Sube a 255 la felicidad de un Pokémon de tu equipo. No
                    cambia nada más ni lo hace evolucionar por sí sola.
                  </span>
                </span>
                <Tag>∞ · Gratis</Tag>
                <Link
                  className="button primary"
                  to={friendshipPath}
                  aria-describedby="unlimited-felicidad"
                >
                  Subir felicidad
                </Link>
              </li>
            )}
          </ul>
        </section>
      )}
      {unlimitedInfo && (
        <Modal
          title={unlimitedInfo.label}
          onClose={() => setUnlimitedInfo(null)}
        >
          <div className="unlimited-dialog">
            <ItemIcon name={unlimitedInfo.name} />
            <p>
              <strong>Gratis e ilimitado.</strong> Se añade a la bolsa de tu
              partida desde PokeApp Launcher.
            </p>
          </div>
          <LauncherDownload />
        </Modal>
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
              <Card
                key={item.id}
                className={`inventory-card item-${transfer ? "transfer" : item.status}`}
              >
                <div className="inventory-item">
                  <ItemIcon name={item.item_name} code={item.item_code} />
                  <h3>{pokemonName("item", item.item_name)}</h3>
                </div>
                <Tag>
                  {transfer
                    ? (transferLabels[transfer.status] ??
                      "Estado del robo no disponible")
                    : item.training_status === "RESERVED"
                      ? "Aplicándose"
                      : item.training_status === "APPLIED"
                        ? "Usado"
                        : physicalItem(item.item_code)
                          ? (itemUseLabels[item.physical_state ?? "UNKNOWN"] ??
                            "Estado físico no disponible")
                          : item.delivery?.status === "DELIVERED"
                            ? "En tu bolsa"
                            : item.delivery?.status === "USED"
                              ? "Usado"
                              : item.delivery?.status === "RESERVED"
                                ? "Entregándose"
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
                {item.delivery?.status === "DELIVERED" && (
                  <p className="muted">
                    {item.delivery.item_name ?? item.item_name} · Pokémon{" "}
                    {gameName(item.delivery.game)}
                    {item.delivery.finished_at &&
                      ` · ${date(item.delivery.finished_at)}`}
                  </p>
                )}
                {item.status === "pending" &&
                  (transfer ? (
                    <p className="muted">Se entrega con el Launcher.</p>
                  ) : item.item_code === "revivir_pokemon" &&
                    physicalItem(item.item_code) ? (
                    insideLauncher() ? (
                      launcherRevives() ? (
                        <Link className="button primary" to={revivePath}>
                          Revivir Pokémon
                        </Link>
                      ) : (
                        <p className="muted">
                          Actualiza PokeApp Launcher a la versión 0.26.13 o
                          posterior para usar este comodín.
                        </p>
                      )
                    ) : (
                      <p className="muted">
                        Se usa desde tu inventario en PokeApp Launcher, cuando
                        quieras. Queda guardado hasta entonces.
                      </p>
                    )
                  ) : physicalItem(item.item_code) && !robbery ? (
                    <p className="muted">
                      Ahora mismo no se puede aplicar. No se ha consumido.
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
                    <ObjectUse
                      purchase={item}
                      leagueGame={q.data?.league_game}
                      disabled={cmd.pending || cmd.uncertain}
                      onUse={() =>
                        cmd.execute(
                          `/v1/seasons/${season}/shop/purchases/${item.id}/use`,
                          {},
                        )
                      }
                    />
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
              {transfer.status === "CANCELLED" &&
                cancelledReason(transfer.reason) && (
                  <p className="muted">{cancelledReason(transfer.reason)}</p>
                )}
              {transfer.obligation && (
                <p>
                  {obligationLabels[transfer.obligation] ??
                    "Estado de la entrega no disponible"}
                </p>
              )}
              {transfer.obligation?.endsWith("_PENDING") &&
                insideLauncher() && (
                  <Link className="text-link" to={deliveriesPath}>
                    Abrir la entrega en el Launcher →
                  </Link>
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
          trainers={board.data?.trainers ?? []}
          round={board.data?.round}
          ownSave={board.data?.own_official_save !== false}
          loading={board.isPending}
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
                  ? "Ese entrenador no tiene Pokémon disponibles para robar."
                  : "No hay Pokémon vivos elegibles para blindar."
            }
          />
        )}
    </>
  );
}

function TrainerPickerModal({
  trainers,
  round,
  ownSave,
  loading,
  onClose,
  onSelect,
}: {
  trainers: Model<"RobberyBoardResponse">["trainers"];
  round?: number;
  ownSave: boolean;
  loading: boolean;
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
        <p>
          Después elegirás uno de sus Pokémon de su última partida oficial.
          {round != null && ` Ronda de robos ${round}.`}
        </p>
        {!ownSave && (
          <p className="muted">
            Tu partida de la Liga todavía no está disponible. Sincronízala con
            el Launcher.
          </p>
        )}
        {loading ? (
          <Loading />
        ) : (
          <div className="trainer-selector-grid">
            {trainers.map((trainer) => (
              <button
                type="button"
                className="trainer-selector-card"
                key={trainer.trainer_id}
                disabled={trainer.status !== "available" || !ownSave}
                onClick={() => onSelect(trainer.trainer_id)}
              >
                <TrainerPhoto name={trainer.display_name} />
                <span>{trainer.display_name}</span>
                {trainer.message && (
                  <small className="muted">{trainer.message}</small>
                )}
              </button>
            ))}
          </div>
        )}
        {!loading && !trainers.length && (
          <Empty>No hay más entrenadores en esta temporada.</Empty>
        )}
      </div>
    </div>
  );
}
