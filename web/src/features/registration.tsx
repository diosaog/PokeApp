import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import { Field, Notice, Submit, form, text } from "../ui";
export const registrationRecoveryKey = "pokeapp-registration-operation";

export function RegistrationForm({
  onRegistered,
  onCancel,
  bootstrapRequired = false,
}: {
  onRegistered: (name: string) => void;
  onCancel: () => void;
  bootstrapRequired?: boolean;
}) {
  const [pending, setPending] = useState(false),
    [uncertain, setUncertain] = useState(false),
    [error, setError] = useState<unknown>(null);
  const intent = useRef<{
    key: string;
    body: {
      trainer_name: string;
      pin: string;
      confirmation: string;
      access_code: string;
      bootstrap_token?: string;
    };
  } | null>(null);
  async function send() {
    const saved = intent.current;
    if (!saved || pending) return;
    setPending(true);
    setError(null);
    try {
      await api.request(
        "/v1/auth/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": saved.key,
          },
          body: JSON.stringify(saved.body),
        },
        false,
      );
      intent.current = null;
      sessionStorage.removeItem(registrationRecoveryKey);
      setUncertain(false);
      onRegistered(saved.body.trainer_name);
    } catch (err) {
      setError(err);
      const unknown =
        !(err instanceof ApiError) || err.status === 0 || err.status >= 500;
      setUncertain(unknown);
      if (!unknown) {
        intent.current = null;
        sessionStorage.removeItem(registrationRecoveryKey);
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <h2>Crea tu cuenta de entrenador</h2>
      <p>
        Tu perfil es independiente de la Liga. Un administrador podrá
        incorporarte a una temporada.
      </p>
      {sessionStorage.getItem(registrationRecoveryKey) && (
        <p role="status">
          Hay un registro pendiente. Introduce los mismos datos para
          comprobarlo.
        </p>
      )}
      <form
        onSubmit={(event) => {
          const data = form(event);
          if (pending || uncertain) return;
          const body = {
            trainer_name: text(data, "name"),
            pin: text(data, "pin"),
            confirmation: text(data, "repeat"),
            access_code: text(data, "access"),
            ...(bootstrapRequired
              ? { bootstrap_token: text(data, "bootstrap") }
              : {}),
          };
          if (body.pin !== body.confirmation) {
            setError(new ApiError(422, "INVALID_PIN_CONFIRMATION"));
            return;
          }
          const key =
            sessionStorage.getItem(registrationRecoveryKey) ||
            crypto.randomUUID();
          intent.current = { key, body };
          sessionStorage.setItem(registrationRecoveryKey, key);
          void send();
        }}
      >
        <fieldset disabled={pending || uncertain}>
          <Field label="Nombre de entrenador">
            <input
              name="name"
              required
              maxLength={48}
              autoComplete="username"
            />
          </Field>
          <Field label="PIN de cuatro cifras">
            <input
              name="pin"
              type="password"
              required
              pattern="[0-9]{4}"
              minLength={4}
              maxLength={4}
              inputMode="numeric"
              autoComplete="new-password"
            />
          </Field>
          <Field label="Repetir PIN">
            <input
              name="repeat"
              type="password"
              required
              pattern="[0-9]{4}"
              minLength={4}
              maxLength={4}
              inputMode="numeric"
              autoComplete="new-password"
            />
          </Field>
          <Field label="Código de acceso a la App">
            <input
              name="access"
              type="password"
              required
              maxLength={128}
              autoComplete="off"
            />
          </Field>
          {bootstrapRequired && (
            <Field label="Autorización de alta inicial">
              <input
                name="bootstrap"
                type="password"
                required
                maxLength={256}
                autoComplete="off"
              />
            </Field>
          )}
          <Submit pending={pending}>Crear cuenta</Submit>
        </fieldset>
      </form>
      <Notice error={error} />
      {uncertain && (
        <p role="status">
          El resultado aún no está confirmado.{" "}
          <button disabled={pending} onClick={() => void send()}>
            Reintentar el mismo registro
          </button>
        </p>
      )}
      <button disabled={pending || uncertain} onClick={onCancel}>
        Volver a entrar
      </button>
    </>
  );
}
