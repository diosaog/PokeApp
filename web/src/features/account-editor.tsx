import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import { useApp } from "../state";
import { Card, Field, Notice, Submit, form, text } from "../ui";

export type AccountProfile = {
  trainer_id: string;
  display_name: string;
  photo_url: string | null;
  revision: number | null;
};
export const pinRecoveryKey = "pokeapp-pin-change-operation";

export function PinForm({
  recovery = false,
  adminTarget,
  renewal = false,
}: {
  recovery?: boolean;
  adminTarget?: string;
  renewal?: boolean;
}) {
  const { logout, holdAdminNavigation } = useApp();
  const [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [uncertain, setUncertain] = useState(false),
    [done, setDone] = useState(false);
  const intent = useRef<{
    key: string;
    body: {
      current_pin?: string;
      new_pin: string;
      confirmation: string;
      renewal_token?: string;
    };
  } | null>(null);
  const storageKey = adminTarget
    ? `${pinRecoveryKey}:${adminTarget}`
    : renewal
      ? `${pinRecoveryKey}:renewal`
      : pinRecoveryKey;
  useEffect(
    () => (pending || uncertain ? holdAdminNavigation() : undefined),
    [pending, uncertain, holdAdminNavigation],
  );
  async function send(resume: boolean) {
    const saved = intent.current;
    if (!saved || pending) return;
    setPending(true);
    setError(null);
    try {
      await api.request(
        adminTarget
          ? `/v1/admin/accounts/${adminTarget}/reset-pin`
          : renewal
            ? "/v1/auth/pin-renewal"
            : resume
              ? "/v1/auth/pin-change/resume"
              : "/v1/account/pin",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": saved.key,
          },
          body: JSON.stringify(saved.body),
        },
        !!adminTarget || (!resume && !renewal),
      );
      sessionStorage.removeItem(storageKey);
      intent.current = null;
      setUncertain(false);
      setDone(true);
      if (!adminTarget) logout();
    } catch (err) {
      setError(err);
      const unknown =
        !(err instanceof ApiError) ||
        err.status === 0 ||
        err.status >= 500 ||
        err.code === "PIN_RECONCILIATION_REQUIRED";
      setUncertain(unknown);
      if (!unknown) {
        intent.current = null;
        sessionStorage.removeItem(storageKey);
      }
    } finally {
      setPending(false);
    }
  }
  if (done)
    return (
      <p role="status">
        {adminTarget
          ? "PIN restablecido. El entrenador debe entrar con el nuevo PIN."
          : "PIN cambiado. Espera un instante y vuelve a entrar con el nuevo PIN."}
      </p>
    );
  return (
    <Card>
      <h2>
        {adminTarget
          ? "Restablecer PIN"
          : recovery
            ? "Recuperar cambio de PIN"
            : "Cambiar PIN"}
      </h2>
      <p>
        Se cerrarán las sesiones anteriores.{" "}
        {recovery && "Introduce los mismos PIN de la solicitud interrumpida."}
      </p>
      <form
        onSubmit={(event) => {
          const data = form(event);
          if (pending || uncertain) return;
          const body = {
            ...(!adminTarget && !renewal
              ? { current_pin: text(data, "current") }
              : { renewal_token: text(data, "renewal") }),
            new_pin: text(data, "new"),
            confirmation: text(data, "repeat"),
          };
          if (body.new_pin !== body.confirmation) {
            setError(new ApiError(422, "INVALID_PIN_CONFIRMATION"));
            return;
          }
          const key = recovery
            ? sessionStorage.getItem(storageKey)
            : (adminTarget || renewal
                ? sessionStorage.getItem(storageKey)
                : null) || crypto.randomUUID();
          if (!key) {
            setError(new ApiError(409, "ACCOUNT_RECONCILIATION_REQUIRED"));
            return;
          }
          intent.current = { key, body };
          sessionStorage.setItem(storageKey, key); // No PIN or credential is persisted.
          void send(recovery);
        }}
      >
        <fieldset disabled={pending || uncertain}>
          {(adminTarget || renewal) && (
            <>
              <p>
                Introduce la autorización de un solo uso entregada después de
                verificar la identidad. No es el código de registro.
              </p>
              <Field label="Código de renovación">
                <input
                  name="renewal"
                  type="password"
                  autoComplete="off"
                  minLength={43}
                  maxLength={128}
                  required
                />
              </Field>
            </>
          )}
          {[
            ["current", "PIN actual", "current-password"],
            ["new", "Nuevo PIN", "new-password"],
            ["repeat", "Repetir nuevo PIN", "new-password"],
          ]
            .filter(
              ([name]) => (!adminTarget && !renewal) || name !== "current",
            )
            .map(([name, label, autocomplete]) => (
              <Field key={name} label={label}>
                <input
                  name={name}
                  type="password"
                  inputMode="numeric"
                  pattern="[0-9]{4}"
                  minLength={4}
                  maxLength={4}
                  autoComplete={autocomplete}
                  required
                />
              </Field>
            ))}
          <Submit pending={pending}>
            {adminTarget ? "Restablecer PIN" : "Cambiar PIN"}
          </Submit>
        </fieldset>
      </form>
      <Notice error={error} />
      {uncertain && (
        <p role="status">
          El cambio aún no está confirmado. Conservamos la solicitud; no pruebes
          otro PIN.
          <button disabled={pending} onClick={() => void send(true)}>
            Comprobar la misma solicitud
          </button>
        </p>
      )}
    </Card>
  );
}

export function AccountEditor({
  profile,
  refresh,
}: {
  profile: AccountProfile;
  refresh: () => Promise<unknown>;
}) {
  const { me, setMe, holdAdminNavigation } = useApp();
  const [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [retry, setRetry] = useState(false),
    [success, setSuccess] = useState(false);
  const intent = useRef<{
    path: string;
    init: RequestInit;
    name?: string;
  } | null>(null);
  useEffect(
    () => (pending || retry ? holdAdminNavigation() : undefined),
    [pending, retry, holdAdminNavigation],
  );
  async function send() {
    if (!intent.current || pending) return;
    const saved = intent.current;
    setPending(true);
    setError(null);
    setSuccess(false);
    try {
      await api.request(saved.path, saved.init);
      if (saved.name && me) setMe({ ...me, display_name: saved.name });
      intent.current = null;
      setRetry(false);
      setSuccess(true);
      await refresh();
    } catch (err) {
      setError(err);
      const unknown =
        !!intent.current &&
        (!(err instanceof ApiError) || err.status === 0 || err.status >= 500);
      setRetry(unknown);
      if (!unknown) {
        intent.current = null;
        if (err instanceof ApiError && err.status === 409) await refresh();
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Card>
        <h2>Editar mi perfil</h2>
        <form
          onSubmit={(event) => {
            const data = form(event);
            if (pending || retry) return;
            const name = text(data, "display_name");
            intent.current = {
              path: "/v1/account/name",
              name,
              init: {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                  "Idempotency-Key": crypto.randomUUID(),
                },
                body: JSON.stringify({
                  display_name: name,
                  expected_revision: profile.revision,
                }),
              },
            };
            void send();
          }}
        >
          <fieldset disabled={pending || retry}>
            <Field label="Nombre de entrenador">
              <input
                key={profile.display_name}
                name="display_name"
                defaultValue={profile.display_name}
                maxLength={48}
                required
              />
            </Field>
            <Submit pending={pending}>Guardar nombre</Submit>
          </fieldset>
        </form>
        <form
          onSubmit={(event) => {
            const data = form(event);
            if (pending || retry) return;
            const photo = data.get("photo");
            if (
              !(photo instanceof File) ||
              !photo.size ||
              photo.size > 5 * 1024 * 1024
            ) {
              setError(new ApiError(422, "INVALID_PHOTO"));
              return;
            }
            intent.current = {
              path: `/v1/account/photo?expected_revision=${profile.revision}`,
              init: {
                method: "PUT",
                headers: {
                  "Content-Type": photo.type,
                  "Idempotency-Key": crypto.randomUUID(),
                },
                body: photo,
              },
            };
            void send();
          }}
        >
          <fieldset disabled={pending || retry}>
            <Field label="Foto de perfil">
              <input
                name="photo"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
              />
            </Field>
            <p>JPEG, PNG o WebP, máximo 5 MB. Retrato vertical recomendado.</p>
            <Submit pending={pending}>Guardar foto</Submit>
          </fieldset>
        </form>
        <Notice error={error} />
        {success && <p role="status">Perfil actualizado.</p>}
        {retry && (
          <button disabled={pending} onClick={() => void send()}>
            Reintentar la misma solicitud
          </button>
        )}
      </Card>
      <PinForm />
    </>
  );
}
