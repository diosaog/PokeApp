import {
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  LoaderCircle,
  X,
} from "lucide-react";
import { api, ApiError, errorText } from "./api/client";
import { queries, useViewer } from "./state";
import { invalidationFor } from "./read-invalidation";

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Notice({ error }: { error: unknown }) {
  return error ? (
    <div role="alert" className="notice">
      <AlertTriangle size={18} />
      <span>{errorText(error)}</span>
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div role="status" className="loading">
      <LoaderCircle className="spin" size={18} /> Cargando datos…
    </div>
  );
}
export function Heading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}
export function Tag({ children }: { children: ReactNode }) {
  return <span className="tag">{children}</span>;
}
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {isValidElement<{ id?: string }>(children)
        ? cloneElement(children, { id })
        : children}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    return () => {
      dialog.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      <div className="dialog-heading">
        <h2 id={id}>{title}</h2>
        <button className="icon-button" aria-label="Cerrar" onClick={onClose}>
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}

/** A retry with an unknown outcome reuses the exact request body and key. */
export function useCommand(invalidatePaths?: readonly string[]) {
  const viewer = useViewer();
  const last = useRef<{ path: string; viewer: string | undefined } | null>(
    null,
  );
  const refresh = () =>
    queries.invalidateQueries({
      predicate: invalidationFor(
        last.current?.viewer ?? viewer,
        last.current?.path ?? "",
        invalidatePaths,
      ),
    });
  const [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null),
    [success, setSuccess] = useState(false);
  const request = useRef<{
      path: string;
      body: unknown;
      key: string;
      method: string;
    } | null>(null),
    busy = useRef(false);
  const [uncertain, setUncertain] = useState(false);
  async function execute(path: string, body: unknown, method = "POST") {
    if (busy.current) return false;
    busy.current = true;
    setPending(true);
    setError(null);
    setSuccess(false);
    const previous = request.current;
    if (
      uncertain &&
      previous &&
      (previous.path !== path ||
        JSON.stringify(previous.body) !== JSON.stringify(body) ||
        previous.method !== method)
    ) {
      setError(new ApiError(409, "PENDING_RETRY_REQUIRED"));
      busy.current = false;
      setPending(false);
      return false;
    }
    request.current =
      previous && uncertain
        ? previous
        : {
            path,
            body: structuredClone(body),
            key: crypto.randomUUID(),
            method,
          };
    const command = request.current;
    last.current = { path: command.path, viewer };
    try {
      await api.command(
        command.path,
        command.body,
        command.key,
        command.method,
      );
      request.current = null;
      setUncertain(false);
      setSuccess(true);
      await refresh();
      return true;
    } catch (err) {
      setError(err);
      const unknown =
        !(err instanceof ApiError) || err.status === 0 || err.status >= 500;
      setUncertain(unknown);
      if (!unknown) request.current = null;
      if (err instanceof ApiError && err.status === 409 && !unknown)
        await refresh();
      return false;
    } finally {
      busy.current = false;
      setPending(false);
    }
  }
  return {
    pending,
    error,
    success,
    uncertain,
    refresh,
    execute,
    retry: () =>
      request.current &&
      execute(
        request.current.path,
        request.current.body,
        request.current.method,
      ),
  };
}
export function CommandState({
  command,
}: {
  command: ReturnType<typeof useCommand>;
}) {
  return (
    <>
      <Notice error={command.error} />
      {command.error instanceof ApiError &&
        command.error.status === 409 &&
        !command.uncertain && (
          <p role="status">
            Los datos cambiaron mientras editabas. Revísalos y vuelve a guardar.
          </p>
        )}
      {command.uncertain && (
        <div className="notice">
          No se ha confirmado el resultado. Conservamos la solicitud para evitar
          duplicados.{" "}
          <button
            disabled={command.pending}
            onClick={() => void command.retry()}
          >
            Reintentar la misma solicitud
          </button>
        </div>
      )}
      {command.success && (
        <p role="status" className="success">
          <Check size={16} /> Cambio confirmado.
        </p>
      )}
    </>
  );
}
export function Submit({
  pending,
  children,
}: {
  pending: boolean;
  children: ReactNode;
}) {
  return (
    <button className="button primary" type="submit" disabled={pending}>
      {pending ? (
        <LoaderCircle className="spin" size={18} />
      ) : (
        <ArrowRight size={18} />
      )}{" "}
      {children}
    </button>
  );
}
export function form(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  return new FormData(event.currentTarget);
}
export const text = (data: FormData, key: string) =>
  String(data.get(key) || "");
export const number = (data: FormData, key: string) => Number(text(data, key));
export const date = (value: string) =>
  new Intl.DateTimeFormat("es", { dateStyle: "medium" }).format(
    new Date(value),
  );
