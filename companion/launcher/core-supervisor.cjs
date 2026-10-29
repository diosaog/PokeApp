// The Launcher core (Python) as a supervised child process.
//
// Requests are JSON lines answered by id; lines without an id are the core's
// lifecycle events (STARTING, WAITING_PREVIOUS, READY, FATAL). 0.26.6 spawned
// the core once: when it exited (a second core on the same profile, a
// startup error, an antivirus) every later request ended, forever, in «está
// tardando en responder» and the hub stayed «Sin conexión». Now an exited core
// is started again with a backoff, and one that stops answering is restarted —
// never while a physical operation on the save may still be running: that
// one is waited for, and its journal decides recovery at the next start.
const { createInterface } = require("node:readline");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

// Commands that may change the save on disk (or its recovery state).
const PHYSICAL = new Set([
  "write_confirm",
  "write_reconcile",
  "backup_restore",
  "export_prepare",
  "export_confirm",
  "export_reconcile",
  "quick_item_offer",
  "quick_item_apply",
  "transfer_prepare",
  "transfer_apply",
  "transfer_fulfil",
  "transfer_cancel",
]);
const RESTART_DELAYS = [1000, 2000, 5000, 10000, 20000, 30000];
const SPAWN_RETRY = 30000;
const ALREADY_RUNNING_RETRY = 15000;
// The core answers `state` in milliseconds; 25 s without any answer while
// requests wait is a stuck core, not a slow one.
const HUNG_AFTER = 25000;
// After a physical command, or while the core says a write is busy, a silent
// core is waited for (never killed) for this long.
const PHYSICAL_GRACE = 120000;
// Ready for this long: the next failure starts the backoff again.
const STABLE_AFTER = 60000;
// An exited core's last answers are read before its requests are failed.
const CLOSE_GRACE = 1500;

const STATUS_TEXT = {
  STARTING: "El núcleo del Launcher se está iniciando…",
  WAITING_PREVIOUS:
    "Esperando a que termine de cerrarse la sesión anterior del Launcher…",
  RESTARTING: "Reconectando con el núcleo del Launcher…",
  STOPPED: "El Launcher se está cerrando.",
  STALLED:
    "El núcleo del Launcher está terminando una operación en tu partida. Espera unos segundos y no abras el emulador.",
};
const REASON_TEXT = {
  LAUNCHER_ALREADY_RUNNING:
    "Otra ventana de PokeApp Launcher, o una sesión anterior que todavía se está cerrando, está usando tus datos locales. Lo reintentamos solo.",
  LOCAL_DATA_UNREADABLE:
    "El Launcher no puede leer sus datos locales en este equipo. Lo reintentamos solo; si sigue así, pulsa «Copiar diagnóstico» y envíalo a la administración.",
  PROFILE_ACCESS_DENIED:
    "Windows no deja usar la carpeta de datos del Launcher (permisos o antivirus). Lo reintentamos solo.",
  PROFILE_UNAVAILABLE:
    "La carpeta de datos del Launcher no es una carpeta local de este equipo.",
  STARTUP_FAILED:
    "El núcleo del Launcher no pudo iniciarse. Lo reintentamos solo.",
  SPAWN_FAILED:
    "Windows no deja ejecutar el núcleo del Launcher (PokeApp.Core.exe). Un antivirus puede haberlo bloqueado o puesto en cuarentena: restáuralo o reinstala el Launcher. Lo reintentamos solo.",
  EXITED:
    "El núcleo del Launcher se cerró inesperadamente. Lo reiniciamos solo.",
  HUNG: "El núcleo del Launcher dejó de responder y se ha reiniciado.",
};

const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// The user's folder and name never leave this PC in a log or a diagnosis.
function mask(text) {
  let out = String(text);
  const home = os.homedir();
  if (home && home.length > 3)
    for (const form of new Set([home, home.replace(/\\/g, "/")]))
      out = out.replace(new RegExp(escape(form), "gi"), "%USERPROFILE%");
  let user = "";
  try {
    user = os.userInfo().username;
  } catch {
    user = process.env.USERNAME || "";
  }
  if (user && user.length > 2)
    out = out.replace(
      new RegExp(`(?<![\\w])${escape(user)}(?![\\w])`, "gi"),
      "<usuario>",
    );
  return out;
}

// Small local log: one line per lifecycle change, rotated at 256 KB.
function createLog(file) {
  const write = (line) => {
    try {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      try {
        if (fs.statSync(file).size > 256 * 1024)
          fs.renameSync(file, file + ".1");
      } catch {
        // no file yet
      }
      fs.appendFileSync(file, `${new Date().toISOString()} ${mask(line)}\n`);
    } catch {
      // A log that cannot be written never stops the Launcher.
    }
  };
  return { write, file };
}

function tail(file, lines) {
  try {
    return mask(fs.readFileSync(file, "utf8"))
      .split(/\r?\n/)
      .filter(Boolean)
      .slice(-lines);
  } catch {
    return [];
  }
}

function createCoreSupervisor({
  spawn,
  executable,
  args,
  options,
  log = { write() {} },
  now = Date.now,
  timers = { setTimeout, clearTimeout, setInterval, clearInterval },
}) {
  let child = null,
    status = "STOPPED",
    reason = null,
    fatal = null,
    sequence = 0,
    attempts = 0,
    starts = 0,
    readyAt = 0,
    lastAnswerAt = 0,
    waitingSince = null,
    physicalUntil = 0,
    stalled = false,
    stopping = false,
    restartTimer = null,
    nextStartAt = 0,
    startupSeconds = null,
    exits = [];
  const pending = new Map();
  let readyWaiters = [];
  const listeners = new Set();
  const stderr = [];

  const notify = () => {
    const view = snapshot();
    for (const listener of listeners) listener(view);
  };
  const setStatus = (next, why) => {
    if (next === status && why === reason) return;
    status = next;
    reason = why;
    log.write(`core ${next}${why ? ` (${why})` : ""}`);
    if (next === "READY") {
      for (const waiter of readyWaiters) waiter.ready();
      readyWaiters = [];
    }
    notify();
  };
  const failure = (message, code) =>
    Object.assign(new Error(message), { code });

  function scheduleRestart(delay, why) {
    if (stopping) return;
    timers.clearTimeout(restartTimer);
    nextStartAt = now() + delay;
    setStatus(attempts >= RESTART_DELAYS.length ? "FAILED" : "RESTARTING", why);
    restartTimer = timers.setTimeout(() => {
      restartTimer = null;
      start();
    }, delay);
  }

  function start() {
    if (stopping || child) return;
    timers.clearTimeout(restartTimer);
    restartTimer = null;
    fatal = null;
    stalled = false;
    starts += 1;
    if (starts === 1) setStatus("STARTING", null);
    let proc;
    try {
      proc = spawn(executable, args, options);
    } catch (error) {
      log.write(`core spawn failed: ${error.code || error.name}`);
      attempts += 1;
      return scheduleRestart(SPAWN_RETRY, "SPAWN_FAILED");
    }
    child = proc;
    const mine = () => child === proc;
    let finished = false,
      exitInfo = null,
      closeTimer = null;
    const finish = (spawnFailed) => {
      if (finished) return;
      finished = true;
      timers.clearTimeout(closeTimer);
      if (mine()) child = null;
      const [code, signal] = exitInfo || [null, null];
      const why = spawnFailed
        ? "SPAWN_FAILED"
        : fatal || (proc.__hung ? "HUNG" : "EXITED");
      exits = [...exits, { at: now(), code, signal, why }].slice(-5);
      log.write(
        `core exited code=${code} signal=${signal || "-"} reason=${why}` +
          (stderr.length ? `\n${stderr.join("").slice(-2000)}` : ""),
      );
      stderr.length = 0;
      for (const task of pending.values()) {
        timers.clearTimeout(task.timer);
        task.reject(
          failure(
            stopping
              ? STATUS_TEXT.STOPPED
              : "El núcleo del Launcher se está reiniciando. Vuelve a intentarlo en unos segundos.",
            "CORE_RESTARTED",
          ),
        );
      }
      pending.clear();
      waitingSince = null;
      if (stopping) return setStatus("STOPPED", null);
      if (readyAt && now() - readyAt >= STABLE_AFTER) attempts = 0;
      readyAt = 0;
      attempts += 1;
      scheduleRestart(
        why === "SPAWN_FAILED"
          ? SPAWN_RETRY
          : why === "LAUNCHER_ALREADY_RUNNING"
            ? ALREADY_RUNNING_RETRY
            : RESTART_DELAYS[Math.min(attempts, RESTART_DELAYS.length) - 1],
        why,
      );
    };
    proc.on("error", (error) => {
      log.write(`core process error: ${error.code || error.name}`);
      // A process that never started has no exit to wait for.
      if (proc.pid === undefined) finish(true);
    });
    proc.on("exit", (code, signal) => {
      exitInfo = [code, signal];
      closeTimer = timers.setTimeout(() => finish(false), CLOSE_GRACE);
    });
    proc.on("close", (code, signal) => {
      exitInfo ??= [code, signal];
      finish(false);
    });
    proc.stdin.on("error", () => {
      // A broken pipe means the core is exiting: its exit event follows.
    });
    proc.stderr?.on("data", (chunk) => {
      stderr.push(String(chunk));
      while (stderr.length > 1 && stderr.join("").length > 8192) stderr.shift();
    });
    createInterface({ input: proc.stdout }).on("line", (line) => {
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        log.write("core wrote a line that is not a message");
        return;
      }
      if (!msg || typeof msg !== "object") return;
      if (msg.event === "core") {
        if (!mine()) return;
        lastAnswerAt = now();
        if (msg.status === "READY") {
          readyAt = now();
          startupSeconds = typeof msg.seconds === "number" ? msg.seconds : null;
          if (msg.config_reset)
            log.write("core set aside an unreadable config.json");
          setStatus("READY", null);
        } else if (msg.status === "WAITING_PREVIOUS")
          setStatus("WAITING_PREVIOUS", "LAUNCHER_ALREADY_RUNNING");
        else if (msg.status === "FATAL")
          fatal = typeof msg.code === "string" ? msg.code : "STARTUP_FAILED";
        return;
      }
      const task = pending.get(msg.id);
      if (mine()) {
        lastAnswerAt = now();
        waitingSince = null;
        if (stalled) {
          stalled = false;
          log.write("core answering again");
          notify();
        }
      }
      if (!task) return;
      pending.delete(msg.id);
      timers.clearTimeout(task.timer);
      if (task.command === "state" && msg.result?.write?.busy)
        physicalUntil = Math.max(physicalUntil, now() + PHYSICAL_GRACE);
      if (msg.error) task.reject(failure(msg.error, msg.error));
      else task.resolve(msg.result);
    });
  }

  function send(command, args, timeout) {
    if (!child || status !== "READY")
      return Promise.reject(failure(message(), "CORE_" + status));
    if (pending.size >= 16)
      return Promise.reject(
        failure(
          "El núcleo del Launcher está ocupado. Vuelve a intentarlo en unos segundos.",
          "CORE_BUSY",
        ),
      );
    const id = ++sequence;
    if (PHYSICAL.has(command))
      physicalUntil = Math.max(physicalUntil, now() + PHYSICAL_GRACE);
    if (waitingSince === null) waitingSince = now();
    const proc = child;
    return new Promise((resolve, reject) => {
      const timer = timers.setTimeout(() => {
        pending.delete(id);
        reject(
          failure(
            "El núcleo del Launcher está tardando en responder. Vuelve a intentarlo en unos segundos.",
            "CORE_TIMEOUT",
          ),
        );
      }, timeout);
      pending.set(id, { resolve, reject, timer, command });
      try {
        proc.stdin.write(JSON.stringify({ id, command, args }) + "\n");
      } catch {
        // The exit of that core rejects it with the real reason.
      }
    });
  }

  // `waitReady`: internal callers (session sharing, updates) wait for a
  // starting core instead of failing; the 1 s poll fails fast and shows why.
  function request(command, args = {}, { timeout = 5000, waitReady = 0 } = {}) {
    if (status === "READY" || !waitReady || stopping || status === "STOPPED")
      return send(command, args, timeout);
    return new Promise((resolve, reject) => {
      const waiter = {
        ready: () => {
          timers.clearTimeout(waiter.timer);
          send(command, args, timeout).then(resolve, reject);
        },
      };
      waiter.timer = timers.setTimeout(() => {
        readyWaiters = readyWaiters.filter((w) => w !== waiter);
        send(command, args, timeout).then(resolve, reject);
      }, waitReady);
      readyWaiters.push(waiter);
    });
  }

  // Watchdog: a core that stopped answering is restarted when nothing on the
  // save can be running; otherwise it is only reported and waited for.
  const watchdog = timers.setInterval(() => {
    if (status !== "READY" || waitingSince === null || !child) return;
    if (now() - waitingSince < HUNG_AFTER) return;
    if (now() < physicalUntil) {
      if (!stalled) {
        stalled = true;
        log.write("core silent during a possible physical operation: waiting");
        notify();
      }
      return;
    }
    log.write("core stopped answering: restarting it");
    child.__hung = true;
    try {
      child.kill();
    } catch {
      // already gone
    }
  }, 2000);
  watchdog.unref?.();

  function message() {
    if (status === "READY") return stalled ? STATUS_TEXT.STALLED : "";
    if (STATUS_TEXT[status] && status !== "RESTARTING")
      return STATUS_TEXT[status];
    return REASON_TEXT[reason] || STATUS_TEXT.RESTARTING;
  }

  function snapshot() {
    return {
      status,
      reason,
      message: message(),
      stalled,
      starts,
      attempts,
      startup_seconds: startupSeconds,
      ready_since: readyAt || null,
      last_answer_at: lastAnswerAt || null,
      next_attempt_in:
        restartTimer && nextStartAt
          ? Math.max(0, Math.round((nextStartAt - now()) / 1000))
          : null,
      exits: exits.map((e) => ({ ...e })),
    };
  }

  // «Reintentar ahora»: a core waiting for its next attempt starts at once.
  function restartNow() {
    if (!stopping && !child) start();
    return snapshot();
  }

  // Closing or updating. Before READY there is no runtime and no write: the
  // process is ended at once. A ready core gets its pipe closed and finishes
  // its last physical step by itself; `killAfter` bounds that only when the
  // installer needs its files.
  function stop({ killAfter = null } = {}) {
    stopping = true;
    timers.clearTimeout(restartTimer);
    restartTimer = null;
    timers.clearInterval(watchdog);
    for (const waiter of readyWaiters) timers.clearTimeout(waiter.timer);
    readyWaiters = [];
    const proc = child;
    if (!proc || proc.exitCode !== null) {
      setStatus("STOPPED", null);
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      proc.once("exit", () => resolve());
      if (status !== "READY") {
        try {
          proc.kill();
        } catch {
          resolve();
        }
        return;
      }
      try {
        proc.stdin.end();
      } catch {
        // the exit event still resolves
      }
      if (killAfter !== null)
        timers.setTimeout(() => {
          if (proc.exitCode === null) proc.kill();
        }, killAfter);
    });
  }

  return {
    start,
    stop,
    request,
    restartNow,
    snapshot,
    onChange: (listener) => listeners.add(listener),
    get pid() {
      return child?.pid ?? null;
    },
  };
}

module.exports = {
  createCoreSupervisor,
  createLog,
  tail,
  mask,
  PHYSICAL,
  HUNG_AFTER,
  PHYSICAL_GRACE,
  RESTART_DELAYS,
  REASON_TEXT,
  STATUS_TEXT,
};
