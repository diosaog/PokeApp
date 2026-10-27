import { useEffect, useMemo, useState } from "react";
import { Coins, History, ReceiptText, Swords } from "lucide-react";
import { ApiError } from "../api/client";
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
import { transferLabels } from "./inventory";

type Overview = Model<"IncidentOverview">;
type Purchase = Overview["purchases"][number];
type Wallet = Overview["wallets"][number];
type Robbery = Overview["robberies"][number];
const statusLabels: Record<string, string> = {
  pending: "Disponible",
  used: "Usada",
  cancelled: "Cancelada",
  refunded: "Reembolsada",
};
const kindLabels: Record<string, string> = {
  purchase_cancel: "Compra cancelada",
  purchase_refund: "Compra reembolsada",
  coin_adjustment: "Corrección de monedas",
  robbery_cancel: "Robo anulado",
};
// Each save's physical delivery, in short (the full text is in Inventario).
const deliveryLabels: Record<string, string> = {
  DONOR_PHYSICAL_PENDING: "Retirada pendiente en el origen",
  DONOR_RECOVERY_REQUIRED: "Origen: recuperación necesaria",
  DONOR_VERIFIED: "Retirada verificada",
  DONOR_ABSENT_VERIFIED: "Origen sin el Pokémon: verificado",
  DONOR_BLOCKED_UNCERTAIN: "Origen bloqueado: asistencia",
  RECIPIENT_PHYSICAL_PENDING: "Entrega pendiente en el destino",
  RECIPIENT_RECOVERY_REQUIRED: "Destino: recuperación necesaria",
  RECIPIENT_VERIFIED: "Entrega verificada",
  RECIPIENT_BLOCKED_UNCERTAIN: "Destino bloqueado: asistencia",
};
const filters = [
  ["actionable", "Requieren atención"],
  ["pending", "Disponibles"],
  ["used", "Usadas"],
  ["closed", "Canceladas o reembolsadas"],
  ["all", "Todas"],
] as const;

// Economía e incidencias. Every action is the server's: it checks authority,
// state and the wallet lock, keeps the receipt for retries and never deletes
// history. Nothing shows as done before the server confirms it.
export function IncidentCenter() {
  const { season, holdAdminNavigation } = useApp();
  const path = `/v1/admin/seasons/${season}/incidents`;
  // An API without the center answers 503 (flag off) or 404 (before 062):
  // say so and stop polling until the screen is opened again.
  const [off, setOff] = useState(false);
  const q = useRead<Overview>(path, !!season, off ? undefined : 15000);
  const unavailable =
    q.error instanceof ApiError &&
    (q.error.code === "INCIDENTS_UNAVAILABLE" || q.error.status === 404);
  useEffect(() => setOff(unavailable), [unavailable]);
  const cmd = useCommand([path]);
  useEffect(
    () => (cmd.pending || cmd.uncertain ? holdAdminNavigation() : undefined),
    [cmd.pending, cmd.uncertain, holdAdminNavigation],
  );
  const [filter, setFilter] =
    useState<(typeof filters)[number][0]>("actionable");
  const [search, setSearch] = useState("");
  const [target, setTarget] = useState<{
    purchase: Purchase;
    action: "cancel" | "refund";
  } | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [robbery, setRobbery] = useState<Robbery | null>(null);
  const purchases = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    return (q.data?.purchases ?? []).filter(
      (p) =>
        (filter === "all" ||
          (filter === "actionable" &&
            (p.cancellable || p.refundable || p.linked_operation)) ||
          (filter === "closed" &&
            ["cancelled", "refunded"].includes(p.status)) ||
          p.status === filter) &&
        (!needle ||
          p.display_name.toLocaleLowerCase().includes(needle) ||
          p.item_name.toLocaleLowerCase().includes(needle)),
    );
  }, [q.data, filter, search]);
  if (unavailable)
    return (
      <Card className="incident-off">
        <h2>Centro de incidencias pendiente de activar</h2>
        <p>
          Cancelar y reembolsar compras o corregir monedas necesita la migración
          062 en la base de datos y activarlo en la API. Está construido y
          probado en local; todavía no está desplegado.
        </p>
      </Card>
    );
  if (q.isPending) return <Loading />;
  if (!q.data) return <Notice error={q.error} />;
  const balance = (trainer: string) =>
    q.data!.wallets.find((w) => w.trainer_id === trainer)?.balance;
  const open = q.data.robberies.filter(
    (r) =>
      !["COMMITTED", "RECONCILED", "CANCELLED"].includes(r.state ?? "") ||
      [r.source_obligation, r.destination_obligation].some(
        (o) => o && !o.endsWith("_VERIFIED"),
      ),
  );
  return (
    <div className="incident-center">
      <Notice error={q.error} />
      <div className="incident-kpis">
        {(
          [
            [Coins, "Monederos", q.data.wallets.length],
            [
              ReceiptText,
              "Requieren atención",
              q.data.purchases.filter(
                (p) => p.cancellable || p.refundable || p.linked_operation,
              ).length,
            ],
            [Swords, "Robos abiertos", open.length],
            [History, "Intervenciones", q.data.history.length],
          ] as const
        ).map(([Icon, label, value]) => (
          <Card key={label} className="incident-kpi">
            <Icon aria-hidden="true" />
            <strong>{value}</strong>
            <span>{label}</span>
          </Card>
        ))}
      </div>
      {!target && !robbery && !wallet && <CommandState command={cmd} />}

      <section aria-labelledby="incident-purchases" className="incident-block">
        <div className="incident-head">
          <h2 id="incident-purchases">Compras</h2>
          <input
            type="search"
            placeholder="Buscar entrenador u objeto"
            aria-label="Buscar compras"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <nav className="tabs" aria-label="Filtrar compras">
          {filters.map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={filter === id}
              className={filter === id ? "active" : ""}
              onClick={() => setFilter(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        {purchases.length ? (
          <ul className="incident-list">
            {purchases.map((p) => (
              <li key={p.id} className="incident-row" data-status={p.status}>
                <span className="incident-who">
                  <strong>{p.display_name}</strong>
                  <span>{p.item_name}</span>
                </span>
                <span className="incident-meta">
                  {p.total_price} PK₽ · {date(p.purchased_at)}
                </span>
                <Tag>{statusLabels[p.status] ?? p.status}</Tag>
                <span className="incident-actions">
                  {p.linked_operation ? (
                    <Tag>Vinculada a una operación de partida</Tag>
                  ) : (
                    <>
                      {p.cancellable && (
                        <button
                          type="button"
                          disabled={cmd.pending || cmd.uncertain}
                          onClick={() =>
                            setTarget({ purchase: p, action: "cancel" })
                          }
                        >
                          Cancelar
                        </button>
                      )}
                      {p.refundable && (
                        <button
                          type="button"
                          disabled={cmd.pending || cmd.uncertain}
                          onClick={() =>
                            setTarget({ purchase: p, action: "refund" })
                          }
                        >
                          Reembolsar
                        </button>
                      )}
                    </>
                  )}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>No hay compras con este filtro.</Empty>
        )}
      </section>

      <section aria-labelledby="incident-wallets" className="incident-block">
        <h2 id="incident-wallets">Monedas</h2>
        <div className="incident-wallets">
          {q.data.wallets.map((w) => (
            <Card key={w.trainer_id} className="incident-wallet">
              <strong>{w.display_name}</strong>
              <span className="coin-price">
                <Coins size={16} aria-hidden="true" /> {w.balance}{" "}
                <small>PK₽</small>
              </span>
              <button
                type="button"
                disabled={cmd.pending || cmd.uncertain}
                onClick={() => setWallet(w)}
              >
                Corregir
              </button>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="incident-robberies" className="incident-block">
        <h2 id="incident-robberies">Robos</h2>
        <p className="muted">
          Puedes anular un robo mientras no tenga decisión competitiva ni
          cambios en las partidas. Uno ya decidido o aplicado no se deshace
          cambiando un estado: requiere su propia conciliación, que protege las
          dos partidas.
        </p>
        {q.data.robberies.length ? (
          <ul className="incident-list">
            {q.data.robberies.map((r) => (
              <li key={r.authorization_id} className="incident-row">
                <span className="incident-who">
                  <strong>
                    {r.requester ?? "—"} → {r.donor ?? "—"}
                  </strong>
                  <span>{date(r.created_at)}</span>
                </span>
                <Tag>
                  {transferLabels[r.state ?? ""] ?? r.state ?? "Sin estado"}
                </Tag>
                <span className="incident-meta">
                  {[r.source_obligation, r.destination_obligation]
                    .filter((o): o is string => Boolean(o))
                    .map((o) => deliveryLabels[o] ?? "Estado no disponible")
                    .join(" · ") || "Sin entregas pendientes"}
                </span>
                {r.cancellable ? (
                  <button
                    type="button"
                    className="secondary"
                    disabled={cmd.pending || cmd.uncertain}
                    onClick={() => setRobbery(r)}
                  >
                    Anular robo
                  </button>
                ) : r.reconciliation_required ? (
                  <Tag>Requiere conciliación</Tag>
                ) : r.cancelled_by_admin ? (
                  <Tag>Anulado por administración</Tag>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <Empty>No hay robos en esta temporada.</Empty>
        )}
      </section>

      <section aria-labelledby="incident-history" className="incident-block">
        <h2 id="incident-history">Historial de intervenciones</h2>
        {q.data.history.length ? (
          <ul className="incident-list">
            {q.data.history.map((h) => (
              <li key={h.operation_id} className="incident-row">
                <span className="incident-who">
                  <strong>{kindLabels[h.kind] ?? h.kind}</strong>
                  <span>
                    {h.actor} → {h.target} · {date(h.created_at)}
                  </span>
                </span>
                <span className="incident-meta">
                  {h.amount > 0 ? "+" : ""}
                  {h.amount} PK₽ · {h.reason}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>Todavía no hay intervenciones.</Empty>
        )}
      </section>

      {target && (
        <Modal
          title={
            target.action === "cancel" ? "Cancelar compra" : "Reembolsar compra"
          }
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setTarget(null);
          }}
        >
          <dl className="incident-facts">
            <dt>Entrenador</dt>
            <dd>{target.purchase.display_name}</dd>
            <dt>Objeto</dt>
            <dd>{target.purchase.item_name}</dd>
            <dt>Compra</dt>
            <dd>
              {target.purchase.total_price} PK₽ ·{" "}
              {date(target.purchase.purchased_at)}
            </dd>
            <dt>Saldo</dt>
            <dd>
              {balance(target.purchase.trainer_id) ?? "—"} →{" "}
              {(balance(target.purchase.trainer_id) ?? 0) +
                target.purchase.total_price}{" "}
              PK₽
            </dd>
          </dl>
          <p>
            {target.action === "cancel"
              ? "La compra queda cancelada y se devuelven sus monedas una sola vez. El registro de la compra se conserva."
              : "La compra queda reembolsada y se devuelven sus monedas una sola vez. El efecto ya aplicado no se deshace."}
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                await cmd.execute(`${path}/purchases/${target.purchase.id}`, {
                  action: target.action,
                  reason: text(data, "reason"),
                } satisfies Model<"PurchaseResolveBody">)
              )
                setTarget(null);
            }}
          >
            <Field label="Motivo (queda en el historial)">
              <textarea name="reason" required minLength={5} maxLength={500} />
            </Field>
            <label className="check-row">
              <input type="checkbox" required /> He revisado el entrenador, el
              objeto y el importe.
            </label>
            <Submit
              pending={cmd.pending}
              disabled={cmd.pending || cmd.uncertain}
            >
              {target.action === "cancel"
                ? "Confirmar cancelación"
                : "Confirmar reembolso"}
            </Submit>
          </form>
          <CommandState command={cmd} />
        </Modal>
      )}
      {robbery && (
        <Modal
          title="Anular robo"
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setRobbery(null);
          }}
        >
          <dl className="incident-facts">
            <dt>Quien roba</dt>
            <dd>{robbery.requester ?? "—"}</dd>
            <dt>Víctima</dt>
            <dd>{robbery.donor ?? "—"}</dd>
            <dt>Estado</dt>
            <dd>
              {transferLabels[robbery.state ?? ""] ??
                robbery.state ??
                "Sin estado"}
            </dd>
            <dt>Se devuelve</dt>
            <dd>{robbery.price ?? 0} PK₽</dd>
          </dl>
          <p>
            Se libera la reserva de las dos partidas, el objeto de robo queda
            cancelado y sus monedas vuelven una sola vez a quien robaba. No se
            ha escrito nada en ninguna partida, así que no hay nada que deshacer
            en ellas. El historial lo conserva todo.
          </p>
          <form
            onSubmit={async (event) => {
              const data = form(event);
              if (
                await cmd.execute(
                  `${path}/robberies/${robbery.authorization_id}/cancel`,
                  {
                    reason: text(data, "reason"),
                  } satisfies Model<"RobberyCancelBody">,
                )
              )
                setRobbery(null);
            }}
          >
            <Field label="Motivo (queda en el historial)">
              <textarea name="reason" required minLength={5} maxLength={500} />
            </Field>
            <label className="check-row">
              <input type="checkbox" required /> He revisado los dos
              entrenadores y las consecuencias.
            </label>
            <Submit
              pending={cmd.pending}
              disabled={cmd.pending || cmd.uncertain}
            >
              Confirmar anulación
            </Submit>
          </form>
          <CommandState command={cmd} />
        </Modal>
      )}
      {wallet && (
        <CoinCorrection
          wallet={wallet}
          path={path}
          command={cmd}
          onClose={() => {
            if (!cmd.pending && !cmd.uncertain) setWallet(null);
          }}
        />
      )}
    </div>
  );
}

function CoinCorrection({
  wallet,
  path,
  command,
  onClose,
}: {
  wallet: Wallet;
  path: string;
  command: ReturnType<typeof useCommand>;
  onClose: () => void;
}) {
  const [amount, setAmount] = useState("");
  const value = /^-?\d+$/.test(amount.trim()) ? Number(amount) : NaN;
  const after = wallet.balance + (Number.isNaN(value) ? 0 : value);
  const invalid =
    Number.isNaN(value) || value === 0 || Math.abs(value) > 100000 || after < 0;
  return (
    <Modal
      title={`Corregir monedas · ${wallet.display_name}`}
      onClose={onClose}
    >
      <p>
        Añade o resta monedas con un movimiento nuevo en el libro. Nunca deja un
        saldo por debajo de cero.
      </p>
      <form
        onSubmit={async (event) => {
          const data = form(event);
          if (invalid) return;
          if (
            await command.execute(`${path}/coins`, {
              trainer_id: wallet.trainer_id,
              amount: value,
              reason: text(data, "reason"),
            } satisfies Model<"CoinAdjustBody">)
          )
            onClose();
        }}
      >
        <Field label="Cantidad (negativa para restar)">
          <input
            name="amount"
            inputMode="numeric"
            autoComplete="off"
            value={amount}
            onChange={(event) =>
              setAmount(event.target.value.replace(/[^\d-]/g, "").slice(0, 7))
            }
            required
          />
        </Field>
        <p className="incident-preview" role="status">
          Saldo: {wallet.balance} → {Number.isNaN(value) ? "—" : after} PK₽
          {after < 0 && " · no puede quedar por debajo de cero"}
        </p>
        <Field label="Motivo (queda en el historial)">
          <textarea name="reason" required minLength={5} maxLength={500} />
        </Field>
        <label className="check-row">
          <input type="checkbox" required /> He revisado el entrenador y la
          cantidad.
        </label>
        <Submit
          pending={command.pending}
          disabled={invalid || command.pending || command.uncertain}
        >
          Confirmar corrección
        </Submit>
      </form>
      <CommandState command={command} />
    </Modal>
  );
}
