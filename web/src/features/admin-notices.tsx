import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  ArrowRight,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  History,
  RefreshCw,
  ScrollText,
  ShieldCheck,
} from "lucide-react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import { CommandState, Empty, Loading, Notice, Tag, useCommand } from "../ui";
import {
  ItemIcon,
  PokemonSprite,
  SpriteGeneration,
  gameGeneration,
} from "../pokemon/presentation";
import { pokemonName } from "../pokemon/localization";

type Overview = Model<"SaveAuditOverview">;
type Row = Overview["notices"][number];
type Change = Row["changes"][number];
type Status = Row["status"];

const statuses: [Status, string][] = [
  ["pending", "Pendiente"],
  ["reviewed", "Revisado"],
  ["justified", "Justificado"],
  ["confirmed", "Confirmado"],
];
const statusName = Object.fromEntries(statuses) as Record<Status, string>;
const severityName: Record<Row["severity"], string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
};
const categoryName: Record<Row["category"], string> = {
  pokemon: "Pokémon",
  objetos: "Objetos",
  origen: "Origen",
};
const games: Record<string, string> = {
  X: "Pokémon X",
  Y: "Pokémon Y",
  OR: "Pokémon Rubí Omega",
  AS: "Pokémon Zafiro Alfa",
  SN: "Pokémon Sol",
  MN: "Pokémon Luna",
  US: "Pokémon Ultrasol",
  UM: "Pokémon Ultraluna",
};
const genders: Record<string, string> = {
  M: "Macho",
  F: "Hembra",
  N: "Sin sexo",
};
const moment = (value: string) =>
  new Intl.DateTimeFormat("es", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
const placeName = (place: { source: string; box: number; slot: number }) =>
  place.source === "party"
    ? `Equipo, posición ${place.slot}`
    : `Caja ${place.box}, posición ${place.slot}`;

const SCALE: Record<string, number> = { iv: 31, ev: 252 };

function shown(change: Change, value: Change["before"]) {
  if (value === null || value === undefined) return "—";
  if (change.kind === "ability" || change.kind === "nature")
    return pokemonName(change.kind, value as string);
  if (change.kind === "species") return pokemonName("species", value as string);
  if (change.kind === "moves" && Array.isArray(value))
    return value.map((move) => pokemonName("move", move)).join(", ") || "—";
  if (change.kind === "bool" || typeof value === "boolean")
    return value ? "Sí" : "No";
  if (change.field === "gender") return genders[String(value)] ?? String(value);
  return String(value);
}

/** The heart of a notice: how far a value jumped, against its scale. */
function Jump({ change }: { change: Change }) {
  const max = SCALE[change.kind];
  const before = change.before as number;
  const after = change.after as number;
  const rise = after >= before;
  const position = (value: number) =>
    `${Math.round((Math.min(value, max) / max) * 100)}%`;
  return (
    <span
      className="aviso-meter"
      data-rise={rise}
      role="img"
      aria-label={`${before} antes, ${after} ahora, sobre ${max}`}
      style={
        {
          "--before": position(before),
          "--after": position(after),
        } as CSSProperties
      }
    >
      <span className="aviso-meter-before" />
      <span className="aviso-meter-change" />
    </span>
  );
}

function Values({ change }: { change: Change }) {
  const delta =
    typeof change.before === "number" && typeof change.after === "number"
      ? change.after - change.before
      : null;
  return (
    <span className="aviso-values">
      <span className="aviso-was">{shown(change, change.before)}</span>
      <ArrowRight size={14} aria-hidden="true" />
      <strong>{shown(change, change.after)}</strong>
      {delta !== null && (
        <small>
          {delta > 0 ? "+" : ""}
          {delta}
        </small>
      )}
    </span>
  );
}

function Evidence({ change }: { change: Change }) {
  if (change.kind === "item") {
    const name = pokemonName("item", change.item ?? "");
    return (
      <li className="aviso-item" data-severity={change.severity}>
        <span className="aviso-item-art">
          <ItemIcon name={change.item ?? ""} />
        </span>
        <span className="aviso-item-name">
          <strong>{name}</strong>
          {!!change.holders?.length && (
            <small>Equipado en {change.holders.join(", ")}</small>
          )}
        </span>
        <span className="aviso-count-jump">
          <span>{String(change.before)}</span>
          <ArrowRight size={18} aria-hidden="true" />
          <strong>{String(change.after)}</strong>
        </span>
        <span className="aviso-justify">
          <span>Compras y entregas registradas</span>
          <b>{change.justified ?? 0}</b>
          <span>Sin justificar</span>
          <b className="aviso-unjustified">+{change.unjustified ?? 0}</b>
        </span>
      </li>
    );
  }
  const numeric =
    (change.kind === "iv" || change.kind === "ev") &&
    typeof change.before === "number" &&
    typeof change.after === "number";
  return (
    <li className="aviso-evidence" data-severity={change.severity}>
      <span className="aviso-field">{change.label}</span>
      {numeric ? <Jump change={change} /> : <span aria-hidden="true" />}
      <Values change={change} />
    </li>
  );
}

function Details({
  notice,
  path,
  canAct,
}: {
  notice: Row;
  path: string;
  canAct: boolean;
}) {
  const reasons = [...new Set(notice.changes.map((c) => c.reason))];
  const before = notice.compared?.previous;
  const after = notice.compared?.current;
  return (
    <div className="aviso-detail">
      <section aria-label="Qué ha cambiado">
        <ul className="aviso-evidences">
          {notice.changes.map((change) => (
            <Evidence change={change} key={change.field} />
          ))}
        </ul>
      </section>
      <div className="aviso-facts">
        <section>
          <h3>Motivo de la sospecha</h3>
          {reasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
          <p className="aviso-origin">
            <CircleHelp size={15} aria-hidden="true" />
            <span>
              Origen: <strong>{notice.origin}</strong>
            </span>
          </p>
        </section>
        <section>
          <h3>Operaciones autorizadas consideradas</h3>
          {notice.operations.length ? (
            <ul className="aviso-plain">
              {notice.operations.map((op, index) => (
                <li key={index}>
                  <ShieldCheck size={15} aria-hidden="true" />
                  <span>
                    <strong>{op.label}</strong>
                    {op.at && <> ({moment(op.at)})</>}
                    {op.detail && <small>{op.detail}</small>}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              Ninguna operación de PokeApp coincide con este cambio.
            </p>
          )}
        </section>
        {before && after && (
          <section>
            <h3>Sincronizaciones comparadas</h3>
            <ul className="aviso-plain">
              <li>
                <span>
                  Anterior: <strong>{moment(before.uploaded_at)}</strong>{" "}
                  <small>
                    Versión {before.revision}, huella{" "}
                    {before.sha256.slice(0, 12)}
                  </small>
                </span>
              </li>
              <li>
                <span>
                  Nueva: <strong>{moment(after.uploaded_at)}</strong>{" "}
                  <small>
                    Versión {after.revision}, huella {after.sha256.slice(0, 12)}
                  </small>
                </span>
              </li>
            </ul>
          </section>
        )}
        <p className="aviso-disclaimer">
          <ScrollText size={15} aria-hidden="true" /> {notice.summary}
        </p>
      </div>
      {canAct && <Decide notice={notice} path={path} />}
      {!!notice.events.length && (
        <section className="aviso-history" aria-label="Historial">
          <h3>
            <History size={15} aria-hidden="true" /> Historial
          </h3>
          <ol>
            {notice.events.map((event, index) => (
              <li key={index}>
                <strong>{moment(event.at)}</strong> {event.actor ?? "—"}:{" "}
                {statusName[event.from_status]}{" "}
                <ArrowRight size={12} aria-hidden="true" />{" "}
                {statusName[event.to_status]}
                {event.note && <q>{event.note}</q>}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

// The administrator's decision. It only changes this notice's administrative
// state: a save, the points or the trainer are never touched from here.
function Decide({ notice, path }: { notice: Row; path: string }) {
  const { holdAdminNavigation } = useApp();
  const command = useCommand([path]);
  const [target, setTarget] = useState<Status | null>(null);
  const [note, setNote] = useState("");
  useEffect(
    () =>
      command.pending || command.uncertain ? holdAdminNavigation() : undefined,
    [command.pending, command.uncertain, holdAdminNavigation],
  );
  const needsNote = target === "justified" || target === "confirmed";
  const valid =
    target !== null &&
    (needsNote
      ? note.trim().length >= 3
      : note.trim().length > 0 || target !== notice.status);
  async function send() {
    if (!target || !valid) return;
    const ok = await command.execute(`${path}/${notice.id}/status`, {
      status: target,
      note: note.trim(),
    } satisfies Model<"NoticeStatusBody">);
    if (ok) {
      setTarget(null);
      setNote("");
    }
  }
  const busy = command.pending || command.uncertain;
  const actions: [Status, string][] = [
    ["reviewed", "Marcar como revisado"],
    ["justified", "Justificar"],
    ["confirmed", "Marcar como confirmado"],
    ["pending", "Reabrir"],
  ];
  return (
    <section className="aviso-decide" aria-label="Tu decisión">
      <div className="aviso-decide-actions">
        {actions
          .filter(
            ([status]) =>
              !(status === notice.status) &&
              (status !== "pending" || notice.status !== "pending"),
          )
          .map(([status, label]) => (
            <button
              type="button"
              key={status}
              className="secondary"
              aria-pressed={target === status}
              disabled={busy}
              onClick={() => setTarget(target === status ? null : status)}
            >
              {label}
            </button>
          ))}
        <button
          type="button"
          className="secondary"
          aria-pressed={target === notice.status}
          disabled={busy}
          onClick={() =>
            setTarget(target === notice.status ? null : notice.status)
          }
        >
          Añadir observación
        </button>
      </div>
      {target && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void send();
          }}
        >
          <label className="aviso-note">
            <span>
              {needsNote
                ? "Observación (obligatoria)"
                : "Observación (opcional)"}
            </span>
            <textarea
              value={note}
              maxLength={1000}
              rows={2}
              placeholder="Por ejemplo: el entrenador confirma que consiguió las Cápsulas Habilidad jugando."
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <p className="muted">
            Solo cambia el estado de este aviso: no toca la partida, los puntos
            ni al entrenador.
          </p>
          <button
            className="button primary"
            type="submit"
            disabled={!valid || busy}
          >
            Guardar: {statusName[target]}
          </button>
        </form>
      )}
      <CommandState command={command} />
    </section>
  );
}

function NoticeCard({
  notice,
  path,
  canAct,
  open,
  onToggle,
}: {
  notice: Row;
  path: string;
  canAct: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  const p = notice.pokemon;
  const generation = gameGeneration(notice.game);
  const count = notice.changes.length;
  return (
    <li
      className="aviso"
      data-severity={notice.severity}
      data-status={notice.status}
    >
      <button
        type="button"
        className="aviso-head"
        aria-expanded={open}
        onClick={onToggle}
      >
        <span className="aviso-lamp" aria-hidden="true" />
        <span className="aviso-art" aria-hidden="true">
          {p ? (
            <SpriteGeneration.Provider value={generation}>
              <PokemonSprite
                species={p.species}
                form={p.form}
                shiny={p.shiny}
              />
            </SpriteGeneration.Provider>
          ) : (
            notice.changes[0]?.item && (
              <ItemIcon name={notice.changes[0].item} />
            )
          )}
        </span>
        <span className="aviso-summary">
          <strong>{notice.title}</strong>
          <span className="aviso-who">
            {notice.display_name}
            {p && (
              <>
                , con <b>{p.nickname || pokemonName("species", p.species)}</b>
                {p.nickname ? ` (${pokemonName("species", p.species)})` : ""}
                {p.level ? `, nivel ${p.level},` : ""} en{" "}
                {placeName(p.location)}
              </>
            )}
          </span>
          <span className="aviso-when">
            {games[notice.game] ?? notice.game}. Detectado el{" "}
            {moment(notice.detected_at)}. {count > 1 ? `${count} cambios.` : ""}
          </span>
        </span>
        <span className="aviso-tags">
          <span className="aviso-severity">
            Gravedad {severityName[notice.severity].toLowerCase()}
          </span>
          <Tag>{statusName[notice.status]}</Tag>
          <Tag>{categoryName[notice.category]}</Tag>
        </span>
        <span className="aviso-chevron" aria-hidden="true">
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </span>
      </button>
      {open && <Details notice={notice} path={path} canAct={canAct} />}
    </li>
  );
}

export function NoticesDesk() {
  const { season, me } = useApp();
  const path = `/v1/admin/seasons/${season}/notices`;
  const [off, setOff] = useState(false);
  const q = useRead<Overview>(path, !!season, off ? undefined : 30000);
  const unavailable =
    q.error instanceof ApiError &&
    (q.error.code === "NOTICES_UNAVAILABLE" || q.error.status === 404);
  useEffect(() => setOff(unavailable), [unavailable]);
  const analyze = useCommand([path]);
  const [status, setStatus] = useState<Status | "all">("pending");
  const [severity, setSeverity] = useState<Row["severity"] | "all">("all");
  const [trainer, setTrainer] = useState("all");
  const [category, setCategory] = useState<Row["category"] | "all">("all");
  const [open, setOpen] = useState<string | null>(null);
  const notices = useMemo(() => q.data?.notices ?? [], [q.data]);
  const scope = useMemo(
    () =>
      notices.filter(
        (n) =>
          (status === "all" || n.status === status) &&
          (trainer === "all" || n.trainer_id === trainer) &&
          (category === "all" || n.category === category),
      ),
    [notices, status, trainer, category],
  );
  const visible = scope.filter(
    (n) => severity === "all" || n.severity === severity,
  );
  if (unavailable)
    return (
      <section className="empty">
        <h2>Los avisos todavía no están activos</h2>
        <p>
          Necesitan la migración 084 en la base de datos y la nueva API. Cuando
          estén publicadas, los avisos aparecerán aquí sin más pasos.
        </p>
      </section>
    );
  if (q.isPending) return <Loading />;
  if (!q.data) return <Notice error={q.error} />;
  const pending = notices.filter((n) => n.status === "pending");
  const high = pending.filter((n) => n.severity === "alta").length;
  const counts = (level: Row["severity"]) =>
    scope.filter((n) => n.severity === level).length;
  return (
    <div className="avisos">
      <Notice error={q.error} />
      <section
        className="avisos-lede"
        data-severity={high ? "alta" : undefined}
      >
        <h2>
          {pending.length === 0
            ? "No hay avisos pendientes"
            : high
              ? `${high} aviso${high === 1 ? "" : "s"} de gravedad alta por revisar`
              : `${pending.length} aviso${pending.length === 1 ? "" : "s"} por revisar`}
        </h2>
        <p>
          Cada partida sincronizada se compara con la anterior y con lo que
          PokeApp autorizó. Solo informa: nunca bloquea, sanciona ni modifica
          una partida. Un aviso es una sospecha; decides tú.
        </p>
        <div className="avisos-sync">
          <span>
            {q.data.pending_saves > 0
              ? `${q.data.pending_saves} partida${q.data.pending_saves === 1 ? "" : "s"} por analizar.`
              : "Todas las partidas recibidas están analizadas."}
            {q.data.last_analyzed_at
              ? ` Último análisis: ${moment(q.data.last_analyzed_at)}.`
              : ""}
          </span>
          <button
            type="button"
            className="secondary"
            disabled={analyze.pending || q.data.pending_saves === 0}
            onClick={() => void analyze.execute(`${path}/analyze`, {})}
          >
            <RefreshCw size={15} aria-hidden="true" /> Analizar pendientes
          </button>
        </div>
        <CommandState command={analyze} />
      </section>

      <div className="avisos-filters">
        <div
          className="avisos-severities"
          role="group"
          aria-label="Filtrar por gravedad"
        >
          {(["alta", "media", "baja"] as const).map((level) => (
            <button
              type="button"
              key={level}
              data-severity={level}
              aria-pressed={severity === level}
              onClick={() => setSeverity(severity === level ? "all" : level)}
            >
              <span className="aviso-lamp" aria-hidden="true" />
              {severityName[level]}
              <b>{counts(level)}</b>
            </button>
          ))}
        </div>
        <nav className="tabs" aria-label="Filtrar por estado">
          {statuses.map(([id, label]) => (
            <button
              type="button"
              key={id}
              aria-pressed={status === id}
              className={status === id ? "active" : ""}
              onClick={() => setStatus(id)}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            aria-pressed={status === "all"}
            className={status === "all" ? "active" : ""}
            onClick={() => setStatus("all")}
          >
            Todos
          </button>
        </nav>
        <div className="avisos-selects">
          <label>
            Entrenador
            <select
              value={trainer}
              onChange={(e) => setTrainer(e.target.value)}
            >
              <option value="all">Todos</option>
              {q.data.trainers.map((t) => (
                <option key={t.trainer_id} value={t.trainer_id}>
                  {t.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Categoría
            <select
              value={category}
              onChange={(e) =>
                setCategory(e.target.value as Row["category"] | "all")
              }
            >
              <option value="all">Todas</option>
              {(Object.keys(categoryName) as Row["category"][]).map((c) => (
                <option key={c} value={c}>
                  {categoryName[c]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {visible.length ? (
        <ol className="avisos-list">
          {visible.map((notice) => (
            <NoticeCard
              key={notice.id}
              notice={notice}
              path={path}
              canAct={Boolean(me?.is_admin)}
              open={open === notice.id}
              onToggle={() => setOpen(open === notice.id ? null : notice.id)}
            />
          ))}
        </ol>
      ) : (
        <Empty>
          {notices.length
            ? "Ningún aviso coincide con estos filtros."
            : "Todavía no se ha detectado nada en esta temporada. Los cambios sospechosos aparecerán aquí cuando un entrenador sincronice su partida."}
        </Empty>
      )}
    </div>
  );
}
