import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import type { Model } from "../api/types";
import { pokemonTitle } from "../pokemon/localization";
import { PokemonSprite } from "../pokemon/presentation";
import { useApp, useOverview, usePC } from "../state";
import {
  CommandState,
  Loading,
  Modal,
  Notice,
  date,
  notify,
  useCommand,
} from "../ui";
import { prepareFirstMatchday, useReadiness } from "./league-start";

const PARTY = /^Equipo · ([1-6])$/;

/** The six of the trainer's OFFICIAL League save, in slot order. */
export function leagueParty(pc?: Model<"PCRead">) {
  return (pc?.pokemon ?? [])
    .filter((s) => PARTY.test(s.location))
    .sort(
      (a, b) =>
        Number(PARTY.exec(a.location)![1]) - Number(PARTY.exec(b.location)![1]),
    );
}

/**
 * «Fijar Equipo»: the trainer's official Team Lock for the League's current
 * matchday (J1 included: an all-vs-all J1 that does not exist yet is
 * prepared first, idempotently). The confirmation shows exactly the six of
 * the official League save that will be fixed. The existing Team Lock
 * operation stays authoritative; its announcement (Discord, with the public
 * Pokepast.es link) is queued by the server from the immutable snapshot.
 */
export function FixTeamButton({
  shownPersonal = false,
}: {
  shownPersonal?: boolean;
}) {
  const { me } = useApp();
  const overview = useOverview();
  const [open, setOpen] = useState(false);
  const day = overview.data?.days?.find(
    (d) => d.id === overview.data?.season.current_matchday_id,
  );
  const lock = overview.data?.locks?.find(
    (l) => l.trainer_id === me?.trainer_id && l.matchday_id === day?.id,
  );
  return (
    <div className="fix-team">
      <button
        type="button"
        className="button primary fix-team-button"
        onClick={() => setOpen(true)}
      >
        <ShieldCheck size={16} aria-hidden="true" /> Fijar Equipo
      </button>
      {lock && day && (
        <small className="fix-team-status" role="status">
          Team Lock oficial · J{day.number} · {date(lock.locked_at)}
        </small>
      )}
      {open && (
        <FixTeamDialog
          shownPersonal={shownPersonal}
          replacing={!!lock}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}

function FixTeamDialog({
  shownPersonal,
  replacing,
  onClose,
}: {
  shownPersonal: boolean;
  replacing: boolean;
  onClose: () => void;
}) {
  const { season } = useApp();
  const pc = usePC();
  const ready = useReadiness();
  const cmd = useCommand([
    `/v1/read/seasons/${season}/overview`,
    `/v1/read/seasons/${season}/team-preview`,
  ]);
  const [preparing, setPreparing] = useState(false),
    [error, setError] = useState<unknown>(null);
  const busy = cmd.pending || cmd.uncertain || preparing;
  const close = () => {
    if (!busy) onClose();
  };
  if (pc.isPending || ready.isPending)
    return (
      <Modal title="Fijar Equipo" onClose={close}>
        <Loading />
      </Modal>
    );
  const state = ready.data;
  const party = leagueParty(pc.data);
  const save = pc.data?.status === "ready" ? pc.data.save : null;
  const target =
    state?.state === "unprepared"
      ? 1
      : state && ["scheduled", "open"].includes(state.state)
        ? state.matchday?.number
        : undefined;
  const problem = !state
    ? null
    : !state.can_operate
      ? "Solo los participantes activos de la Liga pueden fijar un equipo."
      : target == null
        ? state.state === "unavailable" &&
          state.reasons.includes("season_not_active")
          ? "La Liga no está en curso: no hay ninguna jornada que fijar."
          : "No hay ninguna jornada pendiente en la que fijar un equipo."
        : state.state === "unprepared" && !state.can_prepare
          ? "La J1 todavía no puede prepararse. Revisa los motivos en Liga › General."
          : !save
            ? "Tu partida aún no está registrada como partida oficial de la Liga. Sincronízala con PokeApp Launcher."
            : party.length !== 6
              ? `Necesitas seis Pokémon en el equipo de tu partida oficial; ahora tiene ${party.length}.`
              : null;
  return (
    <Modal title="Fijar Equipo" onClose={close}>
      <Notice error={ready.error ?? pc.error} />
      {problem ? (
        <p role="alert">{problem}</p>
      ) : (
        save &&
        target != null && (
          <>
            <p>
              Se fijarán estos seis Pokémon como tu equipo oficial de la{" "}
              <strong>Jornada {target}</strong>
              {state?.state === "unprepared" &&
                " (la J1 se prepara ahora: todos contra todos)"}
              .
            </p>
            <ol className="fix-team-preview" aria-label="Equipo que se fijará">
              {party.map((slot) => (
                <li key={slot.location}>
                  <PokemonSprite
                    species={slot.pokemon.species}
                    form={slot.pokemon.form}
                    shiny={slot.pokemon.is_shiny}
                  />
                  <span>{pokemonTitle(slot.pokemon)}</span>
                  <small>Nv. {slot.pokemon.level ?? "—"}</small>
                </li>
              ))}
            </ol>
            <p className="muted">
              Partida oficial sincronizada el {date(save.uploaded_at)}.
              {shownPersonal &&
                " El equipo de arriba es tu última sincronización personal; se fija el de tu partida oficial de la Liga."}
            </p>
            {state?.state === "open" && (
              <p role="status">
                La jornada ya está abierta: el Team Lock quedará registrado como
                fuera de plazo.
              </p>
            )}
            {replacing && (
              <p role="status">
                Ya fijaste un equipo para esta jornada: se sustituirá por este y
                su anuncio de Discord se actualizará.
              </p>
            )}
            <p className="muted">
              Al confirmar se anunciará en Discord con su enlace público de
              Pokepast.es (sin habilidad, naturaleza, IVs ni EVs).
            </p>
            <button
              className="button primary"
              disabled={busy}
              onClick={async () => {
                if (busy) return;
                setError(null);
                let day = state?.matchday?.id;
                if (state?.state === "unprepared") {
                  setPreparing(true);
                  try {
                    const prepared = await prepareFirstMatchday(season);
                    day = prepared.matchday_id;
                    if (prepared.number !== target) {
                      // Never fix a team for a matchday the trainer did not see.
                      setError(new Error("stale-target"));
                      void ready.refetch();
                      return;
                    }
                  } catch (failure) {
                    setError(failure);
                    return;
                  } finally {
                    setPreparing(false);
                  }
                }
                if (!day) return;
                if (
                  await cmd.execute(
                    `/v1/seasons/${season}/matchdays/${day}/team-lock`,
                    { save_file_id: save.id },
                    "PUT",
                  )
                ) {
                  notify(
                    `Equipo fijado para la J${target}. Se anunciará en Discord con su enlace de Pokepast.es.`,
                    "ok",
                    { key: "command-ok" },
                  );
                  onClose();
                }
              }}
            >
              {preparing ? "Preparando la J1…" : "Confirmar y fijar equipo"}
            </button>
          </>
        )
      )}
      {error instanceof Error && error.message === "stale-target" ? (
        <p role="alert">
          La jornada cambió. Revisa el equipo y vuelve a confirmar.
        </p>
      ) : (
        <Notice error={error} />
      )}
      <CommandState command={cmd} />
      {problem && (
        <p>
          <Link to="/liga" onClick={onClose}>
            Ver Liga › General →
          </Link>
        </p>
      )}
    </Modal>
  );
}
