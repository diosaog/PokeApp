import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Field,
  Heading,
  Loading,
  Notice,
  Tag,
  useCommand,
} from "../ui";
import { PinForm } from "./account-editor";
import { gameName } from "./progress";
import { participantLabel, seasonLabel } from "./admin-labels";

type ManagedAccount = {
  trainer_id: string;
  display_name: string;
  globally_enabled: boolean;
  is_admin: boolean;
  provisioned: boolean;
  revision: number;
};
type AccountsPage = {
  items: ManagedAccount[];
  offset: number;
  has_more: boolean;
};
type AccountDetail = {
  trainer_id: string;
  display_name: string;
  globally_enabled: boolean;
  is_admin: boolean;
  provisioned: boolean;
  deleted: boolean;
  credential: { version: number; reset_required: boolean } | null;
  session_guard: {
    blocked: boolean;
    sessions_valid_from: string | null;
  } | null;
  pin_change_pending: boolean;
  personal_save: { game: string | null; uploaded_at: string } | null;
  seasons: {
    season_id: string;
    name: string;
    status: string;
    participant_status: string;
    bound_game: string | null;
    save_uploaded_at: string | null;
    coin_balance: string;
  }[];
  history: Record<string, number>;
};
const historyLabels: Record<string, string> = {
  seasons: "temporadas",
  coin_transactions: "movimientos de monedas",
  saves: "partidas de temporada",
  pokemon: "Pokémon registrados",
  hall_of_fame: "entradas del Hall",
  cups: "participaciones en Copas",
  trials: "juicios",
  robberies: "robos sufridos",
};
// One account's real state and the tools to repair it. Every action is
// checked again on the server (administrator, operation id, audit).
function AccountRepair({ account }: { account: ManagedAccount }) {
  const { me } = useApp();
  const path = `/v1/admin/accounts/${account.trainer_id}`;
  const detail = useRead<AccountDetail>(path);
  const command = useCommand([
    path,
    "/v1/admin/accounts?offset=0",
    "/v1/accounts?offset=0",
  ]);
  const [confirm, setConfirm] = useState<"" | "sessions" | "unlink" | "delete">(
    "",
  );
  const [typed, setTyped] = useState("");
  const d = detail.data;
  const self = account.trainer_id === me?.trainer_id;
  async function run(action: string, body: unknown = {}) {
    if (await command.execute(`${path}/${action}`, body)) {
      setConfirm("");
      setTyped("");
    }
  }
  if (detail.isPending) return <Loading />;
  if (!d) return <Notice error={detail.error} />;
  const history = Object.entries(d.history).filter(([, n]) => n > 0);
  return (
    <section
      className="account-repair"
      aria-label={`Estado de ${d.display_name}`}
    >
      <dl className="account-facts">
        <dt>Acceso</dt>
        <dd>
          {d.globally_enabled ? "Habilitado" : "Deshabilitado"}
          {d.session_guard?.blocked ? " · bloqueado" : ""}
        </dd>
        <dt>Credencial</dt>
        <dd>
          {d.credential
            ? `Versión ${d.credential.version}${d.credential.reset_required ? " · requiere renovar el PIN" : ""}`
            : "Sin credencial de acceso"}
          {d.pin_change_pending ? " · cambio de PIN pendiente" : ""}
        </dd>
        <dt>Sesiones</dt>
        <dd>
          {d.session_guard?.sessions_valid_from
            ? `Válidas desde ${new Date(d.session_guard.sessions_valid_from).toLocaleString("es-ES")}`
            : "Sin cierres de sesión forzados"}
        </dd>
        <dt>Partida activa</dt>
        <dd>
          {d.personal_save
            ? `Pokémon ${gameName(d.personal_save.game)} · sincronizada ${new Date(d.personal_save.uploaded_at).toLocaleString("es-ES")}`
            : "Ninguna sincronizada"}
        </dd>
      </dl>
      {d.seasons.length > 0 && (
        <>
          <h3>Temporadas</h3>
          <ul>
            {d.seasons.map((s) => (
              <li key={s.season_id}>
                {s.name} ({seasonLabel(s.status)}) ·{" "}
                {participantLabel(s.participant_status)}
                {s.bound_game
                  ? ` · compite con Pokémon ${gameName(s.bound_game)}`
                  : " · sin partida vinculada"}
                {` · ${s.coin_balance} monedas`}
              </li>
            ))}
          </ul>
          <p className="muted">
            Para retirarle de una temporada usa Administración › Liga ›
            Entrenadores; su historial se conserva.
          </p>
        </>
      )}
      <CommandState command={command} />
      <div className="section-row">
        <button
          disabled={command.pending || self || !d.provisioned}
          onClick={() => setConfirm("sessions")}
        >
          Cerrar todas sus sesiones
        </button>
        <button
          disabled={command.pending || !d.personal_save}
          onClick={() => setConfirm("unlink")}
        >
          Desvincular partida activa
        </button>
        <button
          className="danger"
          disabled={command.pending || self || d.is_admin}
          title={
            d.is_admin
              ? "Una cuenta de administración no se borra desde aquí."
              : self
                ? "No puedes borrar tu propia cuenta."
                : undefined
          }
          onClick={() => setConfirm("delete")}
        >
          Borrar cuenta…
        </button>
      </div>
      {confirm === "sessions" && (
        <div
          className="notice"
          role="region"
          aria-label="Confirmar cierre de sesiones"
        >
          <p>
            Se cerrará la sesión de {d.display_name} en todos sus equipos (web y
            Launcher). Podrá volver a entrar con su PIN.
          </p>
          <button
            disabled={command.pending}
            onClick={() => void run("revoke-sessions")}
          >
            Confirmar cierre de sesiones
          </button>
          <button onClick={() => setConfirm("")}>Cancelar</button>
        </div>
      )}
      {confirm === "unlink" && (
        <div
          className="notice"
          role="region"
          aria-label="Confirmar desvinculación"
        >
          <p>
            Se quitará su partida activa de «Mi PC» y «Entrenadores». Las
            temporadas no cambian. Su Launcher volverá a enviar la partida que
            tenga elegida en la próxima sincronización: si era la equivocada,
            pídele que elija la correcta en «Cambiar partida».
          </p>
          <button
            disabled={command.pending}
            onClick={() => void run("unlink-personal-save")}
          >
            Confirmar desvinculación
          </button>
          <button onClick={() => setConfirm("")}>Cancelar</button>
        </div>
      )}
      {confirm === "delete" && (
        <div className="notice" role="region" aria-label="Confirmar borrado">
          <p>
            <strong>Borrar la cuenta de {d.display_name}.</strong> Se eliminan
            su acceso, PIN, sesiones, foto y partida activa. No se puede
            deshacer.
          </p>
          {history.length ? (
            <p>
              Tiene historial (
              {history
                .map(([k, n]) => `${n} ${historyLabels[k] || k}`)
                .join(", ")}
              ): se conserva a nombre de «Entrenador eliminado» para no alterar
              clasificaciones, resultados ni auditoría.
            </p>
          ) : (
            <p>No tiene historial de competición.</p>
          )}
          <Field label={`Escribe ${d.display_name} para confirmar`}>
            <input
              value={typed}
              autoComplete="off"
              onChange={(e) => setTyped(e.target.value)}
            />
          </Field>
          <button
            className="danger"
            disabled={command.pending || typed !== d.display_name}
            onClick={() => void run("delete", { confirmation: typed })}
          >
            Borrar definitivamente
          </button>
          <button onClick={() => setConfirm("")}>Cancelar</button>
        </div>
      )}
    </section>
  );
}
// `embedded`: inside Administración › Cuentas y sistema (no page heading).
export function AdminAccountsPage({
  embedded = false,
}: {
  embedded?: boolean;
}) {
  const { me, holdAdminNavigation, adminOperationPending } = useApp(),
    [offset, setOffset] = useState(0);
  const path = `/v1/admin/accounts?offset=${offset}`;
  const accounts = useRead<AccountsPage>(path, !!me?.is_admin),
    command = useCommand([path, "/v1/accounts?offset=0", "/v1/read/trainers"]);
  const [confirm, setConfirm] = useState<ManagedAccount | null>(null),
    [pin, setPin] = useState<string | null>(null),
    [repair, setRepair] = useState<string | null>(null);
  useEffect(
    () =>
      command.pending || command.uncertain ? holdAdminNavigation() : undefined,
    [command.pending, command.uncertain, holdAdminNavigation],
  );
  if (!me?.is_admin)
    return <Empty>Esta pantalla está reservada a administradores.</Empty>;
  return (
    <>
      {embedded ? (
        <h2>Cuentas de entrenadores</h2>
      ) : (
        <>
          <Heading eyebrow="ADMINISTRACIÓN" title="Cuentas de entrenadores">
            Crear una cuenta no añade participantes ni genera recompensas.
          </Heading>
          <Link
            to="/admin"
            aria-disabled={adminOperationPending}
            onClick={(e) => {
              if (adminOperationPending) e.preventDefault();
            }}
          >
            Organizar mi Liga · añadir cuentas existentes desde Participantes
          </Link>
        </>
      )}
      <p>
        La incorporación conserva las reglas actuales: solo en borrador, antes
        de preparar divisiones y jornadas. No se añade historial retroactivo.
      </p>
      <Notice error={accounts.error} />
      <CommandState command={command} />
      {accounts.isPending ? (
        <Loading />
      ) : (
        <div className="trainer-grid">
          {accounts.data?.items.map((a) => (
            <Card key={a.trainer_id}>
              <h2>{a.display_name}</h2>
              <Tag>{a.globally_enabled ? "Habilitada" : "Deshabilitada"}</Tag>
              {a.is_admin && <Tag>Administración</Tag>}
              {!a.provisioned && (
                <p>
                  Identidad de acceso pendiente. No se vincula ni se crea
                  automáticamente desde aquí.
                </p>
              )}
              <div className="section-row">
                <button
                  disabled={
                    adminOperationPending ||
                    !a.provisioned ||
                    a.trainer_id === me.trainer_id
                  }
                  onClick={() => {
                    setPin(null);
                    setConfirm(a);
                  }}
                >
                  {a.globally_enabled
                    ? "Deshabilitar cuenta"
                    : "Habilitar cuenta"}
                </button>
                <button
                  disabled={
                    adminOperationPending ||
                    !a.provisioned ||
                    !a.globally_enabled ||
                    a.trainer_id === me.trainer_id
                  }
                  onClick={() => {
                    setConfirm(null);
                    setPin(pin === a.trainer_id ? null : a.trainer_id);
                  }}
                >
                  Gestionar PIN
                </button>
                <button
                  disabled={adminOperationPending}
                  aria-expanded={repair === a.trainer_id}
                  onClick={() =>
                    setRepair(repair === a.trainer_id ? null : a.trainer_id)
                  }
                >
                  Estado y herramientas
                </button>
              </div>
              {repair === a.trainer_id && <AccountRepair account={a} />}
              {confirm?.trainer_id === a.trainer_id && (
                <section
                  role="region"
                  aria-label={`Confirmar estado de ${a.display_name}`}
                >
                  <p>
                    {confirm.globally_enabled
                      ? "Se bloqueará el acceso. Sus datos e historial se conservarán."
                      : "Se permitirá de nuevo el acceso a esta cuenta."}
                  </p>
                  {confirm.revision !== a.revision && (
                    <p role="alert">
                      La cuenta cambió. Vuelve a revisar la acción.
                    </p>
                  )}
                  <button
                    disabled={
                      adminOperationPending || confirm.revision !== a.revision
                    }
                    onClick={async () => {
                      if (
                        await command.execute(
                          `/v1/admin/accounts/${a.trainer_id}/status`,
                          {
                            enabled: !confirm.globally_enabled,
                            expected_revision: confirm.revision,
                          },
                          "PUT",
                        )
                      )
                        setConfirm(null);
                    }}
                  >
                    Confirmar cambio de acceso
                  </button>
                  <button
                    disabled={adminOperationPending}
                    onClick={() => setConfirm(null)}
                  >
                    Cancelar
                  </button>
                </section>
              )}
              {pin === a.trainer_id && <PinForm adminTarget={a.trainer_id} />}
            </Card>
          ))}
        </div>
      )}
      <div className="section-row">
        <button
          disabled={offset === 0 || adminOperationPending}
          onClick={() => setOffset(offset - 50)}
        >
          Anteriores
        </button>
        <button
          disabled={!accounts.data?.has_more || adminOperationPending}
          onClick={() => setOffset(offset + 50)}
        >
          Siguientes
        </button>
      </div>
    </>
  );
}
