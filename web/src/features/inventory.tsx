import { useState } from "react";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Loading,
  Modal,
  Notice,
  Submit,
  Tag,
  date,
  form,
  text,
  useCommand,
} from "../ui";

export function Inventory() {
  const { season } = useApp(),
    q = useRead<Model<"InventoryRead">>(
      `/v1/read/seasons/${season}/inventory`,
      !!season,
    ),
    cmd = useCommand([
      `/v1/read/seasons/${season}/inventory`,
      `/v1/read/seasons/${season}/overview`,
      `/v1/read/seasons/${season}/league`,
      `/v1/seasons/${season}/initial-assignment`,
    ]),
    [purchase, setPurchase] = useState<Model<"PurchaseRead"> | null>(null),
    trainers = useRead<Model<"TrainerRead">[]>(
      "/v1/read/trainers",
      !!season && !!purchase,
    );
  const targets =
    q.data?.targets.filter((t) =>
      purchase?.item_code === "robar_pokemon"
        ? t.visibility === "public_team_lock"
        : t.visibility === "own" &&
          (!["blindar_pokemon", "robbery_shield_voucher"].includes(
            purchase?.item_code || "",
          ) ||
            t.can_shield),
    ) || [];
  return (
    <>
      <h2>Tus compras y vales</h2>
      <Notice error={q.error} />
      {q.isPending ? (
        <Loading />
      ) : q.data?.purchases.length ? (
        <div className="trainer-grid">
          {q.data.purchases.map((p) => (
            <Card key={p.id}>
              <Tag>{p.status}</Tag>
              {p.acquisition_type === "reward" && <Tag>Vale de recompensa</Tag>}
              <h3>{p.item_name}</h3>
              <p>
                {date(p.purchased_at)} · {p.total_price} PK₽
              </p>
              {p.status === "pending" &&
                ([
                  "blindar_pokemon",
                  "revivir_pokemon",
                  "robar_pokemon",
                  "robbery_shield_voucher",
                ].includes(p.item_code) ? (
                  <button onClick={() => setPurchase(p)}>Canjear</button>
                ) : (
                  <p>
                    Este artículo todavía no tiene canje disponible en PokeApp.
                  </p>
                ))}
            </Card>
          ))}
        </div>
      ) : (
        <Empty>Aún no hay compras ni vales registrados.</Empty>
      )}
      {purchase && (
        <Modal
          title={`Canjear ${purchase.item_name}`}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setPurchase(null);
          }}
        >
          <p>
            El servidor comprobará la identidad, propiedad y elegibilidad del
            objetivo antes de consumir el vale.
          </p>
          {purchase.item_code === "robar_pokemon" && (
            <p>
              Se muestran los equipos públicos fijados de tus rivales. Sus cajas
              privadas no se publican aquí.
            </p>
          )}
          {["revivir_pokemon", "robar_pokemon"].includes(
            purchase.item_code,
          ) && (
            <p>
              El canje se registra en PokeApp. El cambio físico en la partida
              queda pendiente; el Launcher actual todavía no lo ejecuta.
            </p>
          )}
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                await cmd.execute(
                  `/v1/seasons/${season}/shop/purchases/${purchase.id}/redemptions`,
                  {
                    pokemon_entity_id: text(data, "target"),
                  } satisfies Model<"RedemptionBody">,
                )
              )
                setPurchase(null);
            }}
          >
            <Field label="Pokémon objetivo">
              <select name="target" required>
                <option value="">Seleccionar Pokémon</option>
                {targets.map((t) => (
                  <option key={t.pokemon_entity_id} value={t.pokemon_entity_id}>
                    {t.pokemon.nickname || t.pokemon.species} ·{" "}
                    {trainers.data?.find((p) => p.id === t.trainer_id)
                      ?.display_name || "Entrenador"}{" "}
                    · {t.location}
                  </option>
                ))}
              </select>
            </Field>
            {!targets.length && (
              <Empty>
                No hay objetivos con identidad confirmada disponibles. No se
                crean identidades a partir del apodo o la posición.
              </Empty>
            )}
            <CommandState command={cmd} />
            <Submit pending={cmd.pending || cmd.uncertain || !targets.length}>
              Confirmar canje
            </Submit>
          </form>
        </Modal>
      )}
    </>
  );
}
