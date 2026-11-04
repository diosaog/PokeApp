import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, SlidersHorizontal, UserRound } from "lucide-react";
import { queries, useApp, useRead } from "../state";
import { Loading, Modal, Notice } from "../ui";
import { TrainerPhoto } from "../pokemon/presentation";
import {
  AccountIdentityForms,
  PinForm,
  type AccountProfile,
} from "./account-editor";
import { PreferencesPanel } from "./preferences";

type Tab = "perfil" | "seguridad" | "preferencias";
const tabs = [
  ["perfil", "Perfil", UserRound],
  ["seguridad", "Seguridad", ShieldCheck],
  ["preferencias", "Preferencias", SlidersHorizontal],
] as const;

/** True when a form field inside `root` differs from what it was rendered with. */
export function unsavedInput(root: ParentNode | null) {
  if (!root) return false;
  return Array.from(
    root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
      "form input, form textarea",
    ),
  ).some((field) => {
    if (field instanceof HTMLInputElement) {
      if (field.type === "file") return !!field.files?.length;
      if (field.type === "checkbox" || field.type === "radio")
        return field.checked !== field.defaultChecked;
    }
    return field.value !== field.defaultValue;
  });
}

// Reads that show the trainer's name or photo, after a confirmed change.
export function refreshAccountReads(trainerId?: string, season?: string) {
  return queries.invalidateQueries({
    predicate: (q) =>
      q.queryKey[0] === trainerId &&
      (String(q.queryKey[1]).startsWith("/v1/accounts") ||
        String(q.queryKey[1]) === "/v1/read/trainers" ||
        new RegExp(
          `/seasons/${season}/(overview|league|team-preview|scouting|setup)`,
        ).test(String(q.queryKey[1]))),
  });
}

/**
 * «Mi perfil»: the signed-in trainer's personal settings, opened from the
 * sidebar. Same forms, validation and requests as before; only the place
 * changed. All panels stay mounted, so switching tabs never drops input,
 * and only the selected tab is visible (079: the panels used to be forced
 * visible by a CSS display rule that overrode `hidden`).
 */
export function ProfileSettings({ onClose }: { onClose: () => void }) {
  const { me, season, accountsEnabled, adminOperationPending } = useApp();
  const available = accountsEnabled
    ? tabs
    : tabs.filter(([id]) => id === "preferencias");
  const [tab, setTab] = useState<Tab>(available[0][0]);
  const [discard, setDiscard] = useState(false),
    [waiting, setWaiting] = useState(false);
  const body = useRef<HTMLDivElement>(null);
  const profile = useRead<AccountProfile>(
    `/v1/accounts/${me?.trainer_id}`,
    accountsEnabled && !!me,
  );
  // Closing (button, Escape, backdrop or leaving to the trainer page) never
  // drops a pending request or typed input without the trainer saying so.
  const leave = () => {
    if (adminOperationPending) {
      setWaiting(true);
      return false;
    }
    if (unsavedInput(body.current)) {
      setDiscard(true);
      return false;
    }
    return true;
  };
  const requestClose = () => {
    if (discard) return; // the open question is answered with its buttons
    if (leave()) onClose();
  };
  const keyNav = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step =
      event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next =
      available[(index + step + available.length) % available.length];
    setTab(next[0]);
    document.getElementById(`profile-tab-${next[0]}`)?.focus();
  };
  return (
    <Modal
      title="Mi perfil"
      onClose={requestClose}
      className="profile-settings"
    >
      <div className="profile-settings-head">
        <div className="profile-settings-identity">
          <TrainerPhoto
            name={profile.data?.display_name ?? me?.display_name ?? ""}
            url={profile.data?.photo_url}
          />
          <div>
            <strong>{profile.data?.display_name ?? me?.display_name}</strong>
            <Link
              className="text-link"
              to={`/entrenadores/${me?.trainer_id}`}
              onClick={(event) => {
                if (!leave()) event.preventDefault();
                else onClose();
              }}
            >
              Ver mi ficha de entrenador →
            </Link>
          </div>
        </div>
        {available.length > 1 && (
          <div
            className="tabs"
            role="tablist"
            aria-label="Secciones de Mi perfil"
          >
            {available.map(([id, label, Icon], index) => (
              <button
                key={id}
                id={`profile-tab-${id}`}
                type="button"
                role="tab"
                aria-selected={tab === id}
                aria-controls={`profile-panel-${id}`}
                tabIndex={tab === id ? 0 : -1}
                onClick={() => setTab(id)}
                onKeyDown={(event) => keyNav(event, index)}
              >
                <Icon size={16} aria-hidden="true" /> {label}
              </button>
            ))}
          </div>
        )}
      </div>
      <div ref={body} className="profile-settings-body">
        {accountsEnabled && (
          <>
            <section
              id="profile-panel-perfil"
              role="tabpanel"
              aria-labelledby="profile-tab-perfil"
              hidden={tab !== "perfil"}
            >
              {profile.isPending ? (
                <Loading />
              ) : profile.data ? (
                <AccountIdentityForms
                  profile={profile.data}
                  refresh={() => refreshAccountReads(me?.trainer_id, season)}
                />
              ) : (
                <Notice error={profile.error} />
              )}
            </section>
            <section
              id="profile-panel-seguridad"
              role="tabpanel"
              aria-labelledby="profile-tab-seguridad"
              hidden={tab !== "seguridad"}
            >
              <div className="profile-security">
                <PinForm />
                <aside className="profile-security-notes">
                  <h3>Tu PIN</h3>
                  <ul>
                    <li>Protege tu cuenta en la web y en PokeApp Launcher.</li>
                    <li>
                      Al cambiarlo se cierran tus sesiones anteriores, también
                      la del Launcher: vuelve a entrar con el nuevo PIN.
                    </li>
                    <li>
                      Si lo olvidas, el responsable de PokeApp puede darte una
                      autorización de renovación tras verificar tu identidad.
                    </li>
                  </ul>
                </aside>
              </div>
            </section>
          </>
        )}
        <section
          id="profile-panel-preferencias"
          role="tabpanel"
          aria-labelledby={
            available.length > 1 ? "profile-tab-preferencias" : undefined
          }
          aria-label={available.length > 1 ? undefined : "Preferencias"}
          hidden={tab !== "preferencias"}
        >
          <PreferencesPanel />
        </section>
      </div>
      {waiting && adminOperationPending && (
        <p role="status" className="notice">
          Espera a que se confirme la operación en curso antes de cerrar.
        </p>
      )}
      {discard && (
        <div
          role="alertdialog"
          aria-label="Cambios sin guardar"
          className="notice profile-settings-discard"
        >
          <span>Tienes cambios sin guardar.</span>
          <div className="toolbar">
            <button
              type="button"
              className="button"
              autoFocus
              onClick={() => setDiscard(false)}
            >
              Seguir editando
            </button>
            <button type="button" className="button danger" onClick={onClose}>
              Descartar y cerrar
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
