const test = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const { EventEmitter } = require("node:events");
const { PassThrough } = require("node:stream");
const {
  createCoreSupervisor,
  mask,
  HUNG_AFTER,
  REASON_TEXT,
  STATUS_TEXT,
} = require("./core-supervisor.cjs");

const flush = () => new Promise((resolve) => setImmediate(resolve));

function clock() {
  let t = 0,
    seq = 0;
  const tasks = new Map();
  const timers = {
    setTimeout(fn, ms) {
      tasks.set(++seq, { at: t + ms, fn });
      return seq;
    },
    clearTimeout(id) {
      tasks.delete(id);
    },
    setInterval(fn, ms) {
      tasks.set(++seq, { at: t + ms, fn, every: ms });
      return seq;
    },
    clearInterval(id) {
      tasks.delete(id);
    },
  };
  async function advance(ms) {
    const end = t + ms;
    for (;;) {
      const due = [...tasks.entries()]
        .filter(([, task]) => task.at <= end)
        .sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, task] = due;
      t = task.at;
      if (task.every) task.at += task.every;
      else tasks.delete(id);
      task.fn();
      await flush();
    }
    t = end;
    await flush();
  }
  return { timers, now: () => t, advance };
}

function fakeCore() {
  const proc = new EventEmitter();
  proc.stdin = new PassThrough();
  proc.stdout = new PassThrough();
  proc.stderr = new PassThrough();
  proc.pid = 4242;
  proc.exitCode = null;
  proc.requests = [];
  proc.stdin.on("data", (chunk) => {
    for (const line of String(chunk).split("\n").filter(Boolean))
      proc.requests.push(JSON.parse(line));
  });
  proc.stdin.on("finish", () => {
    proc.pipeClosed = true;
  });
  proc.say = (message) => proc.stdout.write(JSON.stringify(message) + "\n");
  proc.event = (status, fields = {}) =>
    proc.say({ event: "core", status, ...fields });
  proc.answer = (result) => {
    const last = proc.requests.at(-1);
    proc.say({ id: last.id, result });
  };
  proc.exit = (code = 1) => {
    proc.exitCode = code;
    proc.emit("exit", code, null);
    proc.stdout.end();
    proc.emit("close", code, null);
  };
  proc.kill = () => {
    proc.killed = true;
    proc.exit(1);
  };
  return proc;
}

function setup() {
  const c = clock();
  const spawned = [];
  const lines = [];
  const supervisor = createCoreSupervisor({
    spawn: () => {
      const proc = fakeCore();
      spawned.push(proc);
      return proc;
    },
    executable: "PokeApp.Core.exe",
    args: [],
    options: {},
    log: { write: (line) => lines.push(line) },
    now: c.now,
    timers: c.timers,
  });
  return { supervisor, spawned, clock: c, lines };
}

test("requests wait for READY only when asked; the poll fails fast with the reason", async () => {
  const { supervisor, spawned } = setup();
  supervisor.start();
  await assert.rejects(supervisor.request("state"), {
    message: STATUS_TEXT.STARTING,
    code: "CORE_STARTING",
  });
  const waiting = supervisor.request("web_session", {}, { waitReady: 30000 });
  spawned[0].event("READY", { seconds: 0.8 });
  await flush();
  assert.equal(spawned[0].requests[0].command, "web_session");
  spawned[0].answer({ status: "OK" });
  assert.deepEqual(await waiting, { status: "OK" });
  assert.equal(supervisor.snapshot().startup_seconds, 0.8);
});

test("a core that exits is started again: no request is left waiting forever", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  const inFlight = supervisor.request("state");
  await flush();
  spawned[0].exit(1);
  await assert.rejects(inFlight, { code: "CORE_RESTARTED" });
  assert.equal(supervisor.snapshot().status, "RESTARTING");
  assert.equal(supervisor.snapshot().message, REASON_TEXT.EXITED);
  await assert.rejects(supervisor.request("state"), {
    code: "CORE_RESTARTING",
  });
  await clock.advance(1000);
  assert.equal(spawned.length, 2);
  spawned[1].event("READY");
  await flush();
  const state = supervisor.request("state");
  await flush();
  spawned[1].answer({ cloud_status: "ONLINE" });
  assert.deepEqual(await state, { cloud_status: "ONLINE" });
  assert.equal(supervisor.snapshot().exits.at(-1).why, "EXITED");
});

test("a profile still held by the previous core is waited for, then retried", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("WAITING_PREVIOUS");
  await flush();
  assert.equal(supervisor.snapshot().status, "WAITING_PREVIOUS");
  spawned[0].event("FATAL", { code: "LAUNCHER_ALREADY_RUNNING" });
  await flush();
  spawned[0].exit(3);
  await flush();
  const snap = supervisor.snapshot();
  assert.equal(snap.reason, "LAUNCHER_ALREADY_RUNNING");
  assert.equal(snap.message, REASON_TEXT.LAUNCHER_ALREADY_RUNNING);
  assert.equal(snap.next_attempt_in, 15);
  await clock.advance(14000);
  assert.equal(spawned.length, 1);
  await clock.advance(1000);
  assert.equal(spawned.length, 2);
});

test("a core Windows cannot run (antivirus, quarantine) is explained and retried", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].pid = undefined;
  spawned[0].emit(
    "error",
    Object.assign(new Error("spawn"), { code: "ENOENT" }),
  );
  await flush();
  assert.equal(supervisor.snapshot().reason, "SPAWN_FAILED");
  assert.match(supervisor.snapshot().message, /antivirus/);
  await clock.advance(30000);
  assert.equal(spawned.length, 2);
});

test("a silent core is restarted when no save operation can be running", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  for (let i = 0; i < 30; i++) {
    void supervisor.request("state").catch(() => {});
    await clock.advance(1000);
  }
  assert.equal(spawned[0].killed, true);
  assert.equal(supervisor.snapshot().exits.at(-1).why, "HUNG");
  await clock.advance(1000);
  assert.equal(spawned.length, 2);
});

test("a silent core is never killed during a physical operation, only waited for", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  void supervisor
    .request("quick_item_apply", { item: "rare_candy", quantity: 1 })
    .catch(() => {});
  for (let i = 0; i < 60; i++) {
    void supervisor.request("state").catch(() => {});
    await clock.advance(1000);
  }
  assert.notEqual(spawned[0].killed, true);
  assert.equal(supervisor.snapshot().stalled, true);
  assert.equal(supervisor.snapshot().message, STATUS_TEXT.STALLED);
  const state = supervisor.request("state");
  await flush();
  spawned[0].answer({ write: { busy: false } });
  await state;
  assert.equal(supervisor.snapshot().stalled, false);
  assert.ok(HUNG_AFTER < 60000);
});

test("a state that says a write is busy also protects the core", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  const busy = supervisor.request("state");
  await flush();
  spawned[0].answer({ write: { busy: true } });
  await busy;
  for (let i = 0; i < 40; i++) {
    void supervisor.request("state").catch(() => {});
    await clock.advance(1000);
  }
  assert.notEqual(spawned[0].killed, true);
});

test("closing: a ready core finishes by itself; a starting one is ended; nothing restarts", async () => {
  const ready = setup();
  ready.supervisor.start();
  ready.spawned[0].event("READY");
  await flush();
  const stopped = ready.supervisor.stop();
  await flush();
  assert.equal(ready.spawned[0].pipeClosed, true);
  assert.notEqual(ready.spawned[0].killed, true);
  ready.spawned[0].exit(0);
  await stopped;
  await ready.clock.advance(60000);
  assert.equal(ready.spawned.length, 1);
  assert.equal(ready.supervisor.snapshot().status, "STOPPED");

  const starting = setup();
  starting.supervisor.start();
  starting.spawned[0].event("WAITING_PREVIOUS");
  await flush();
  await starting.supervisor.stop();
  assert.equal(starting.spawned[0].killed, true);
  await starting.clock.advance(60000);
  assert.equal(starting.spawned.length, 1);
});

test("an update bounds the wait for the core's files", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  const stopped = supervisor.stop({ killAfter: 15000 });
  await clock.advance(15000);
  await stopped;
  assert.equal(spawned[0].killed, true);
});

test("«Reintentar ahora» starts a waiting core at once", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  spawned[0].exit(1);
  await flush();
  for (let i = 0; i < 4; i++) {
    await clock.advance(30000);
    spawned.at(-1).exit(1);
    await flush();
  }
  const before = spawned.length;
  supervisor.restartNow();
  assert.equal(spawned.length, before + 1);
});

test("answers from a previous core never resolve the new one's requests", async () => {
  const { supervisor, spawned, clock } = setup();
  supervisor.start();
  spawned[0].event("READY");
  await flush();
  spawned[0].exit(1);
  await clock.advance(1000);
  spawned[1].event("READY");
  await flush();
  const state = supervisor.request("state");
  await flush();
  const id = spawned[1].requests[0].id;
  spawned[0].stdout = new PassThrough();
  spawned[1].say({ id, result: { from: "new" } });
  assert.deepEqual(await state, { from: "new" });
});

test("stderr and exit reasons reach the local log", async () => {
  const { supervisor, spawned, lines } = setup();
  supervisor.start();
  spawned[0].stderr.write("Traceback: LocalConflict\n");
  await flush();
  spawned[0].event("FATAL", { code: "LOCAL_DATA_UNREADABLE" });
  await flush();
  spawned[0].exit(4);
  await flush();
  const exit = lines.find((line) => line.startsWith("core exited"));
  assert.match(exit, /code=4/);
  assert.match(exit, /reason=LOCAL_DATA_UNREADABLE/);
  assert.match(exit, /Traceback: LocalConflict/);
});

test("the user's folder and name are masked", () => {
  const home = os.homedir();
  const user = os.userInfo().username;
  const text = mask(
    `${home}\\AppData\\Local\\PokeApp ${home.replace(/\\/g, "/")}/x ${user}`,
  );
  assert.ok(!text.includes(home));
  assert.match(text, /%USERPROFILE%\\AppData/);
  if (user.length > 2)
    assert.ok(!text.toLowerCase().includes(user.toLowerCase()));
});
