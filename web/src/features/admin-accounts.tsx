import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Empty,
  Heading,
  Loading,
  Notice,
  Tag,
  useCommand,
} from "../ui";
import { PinForm } from "./account-editor";

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
export function AdminAccountsPage() {
  const { me, holdAdminNavigation, adminOperationPending } = useApp(),
    [offset, setOffset] = useState(0);
  const path = `/v1/admin/accounts?offset=${offset}`;
  const accounts = useRead<AccountsPage>(path, !!me?.is_admin),
    command = useCommand([path, "/v1/accounts?offset=0", "/v1/read/trainers"]);
  const [confirm, setConfirm] = useState<ManagedAccount | null>(null),
    [pin, setPin] = useState<string | null>(null);
  useEffect(
    () =>
      command.pending || command.uncertain ? holdAdminNavigation() : undefined,
    [command.pending, command.uncertain, holdAdminNavigation],
  );
  if (!me?.is_admin)
    return <Empty>Esta pantalla está reservada a administradores.</Empty>;
  return (
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
              </div>
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
