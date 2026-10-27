const test = require("node:test");
const assert = require("node:assert/strict");
const { createConfirmations, STALE } = require("./confirmations.cjs");

test("a ticket confirms exactly one action, once", () => {
  const c = createConfirmations();
  const id = c.issue("restore", "op-1", ["save", "op-1", "Y"]);
  c.redeem(id, "restore", "op-1", ["save", "op-1", "Y"]);
  assert.throws(() => c.redeem(id, "restore", "op-1", ["save", "op-1", "Y"]), {
    message: STALE,
  });
});

test("another kind, target or state is refused and spends the ticket", () => {
  const c = createConfirmations();
  for (const [kind, target, print] of [
    ["write", "op-1", ["save", "op-1", "Y"]],
    ["restore", "op-2", ["save", "op-1", "Y"]],
    ["restore", "op-1", ["other-save", "op-1", "Y"]],
  ]) {
    const id = c.issue("restore", "op-1", ["save", "op-1", "Y"]);
    assert.throws(() => c.redeem(id, kind, target, print), { message: STALE });
    assert.throws(
      () => c.redeem(id, "restore", "op-1", ["save", "op-1", "Y"]),
      {
        message: STALE,
      },
    );
  }
});

test("tickets expire and a new dialog supersedes the old one", () => {
  let clock = 1000;
  const c = createConfirmations({ ttlMs: 50, now: () => clock });
  const old = c.issue("transfer:apply", "a", [1]);
  const fresh = c.issue("transfer:apply", "a", [1]);
  assert.throws(() => c.redeem(old, "transfer:apply", "a", [1]));
  clock += 60;
  assert.throws(() => c.redeem(fresh, "transfer:apply", "a", [1]));
  assert.equal(c.size, 0);
});

test("forged or missing tickets are refused", () => {
  const c = createConfirmations();
  c.issue("install", "1.0.0", ["1.0.0"]);
  for (const id of [undefined, null, "", "x", 42, {}])
    assert.throws(() => c.redeem(id, "install", "1.0.0", ["1.0.0"]));
  assert.throws(() => c.issue("install", 1, []));
});

const {
  describe: summary,
  fingerprint,
  robberyOpen,
} = require("./confirmations.cjs");
const backup = {
  operation_id: "op-1",
  role: "original",
  can_restore: true,
  verified: true,
  game: "Y",
  created_at: "2026-10-26T10:00:00+00:00",
};
const base = {
  selected_save: "C:/fx/main",
  write: { backups: [backup], busy: false },
  cloud: { data: { transfers: [] } },
};

test("a restore ticket is bound to that backup of that save", () => {
  const c = createConfirmations();
  const id = c.issue("restore", "op-1", fingerprint("restore", "op-1", base));
  const otherSave = { ...base, selected_save: "C:/fx/other" };
  assert.throws(() =>
    c.redeem(id, "restore", "op-1", fingerprint("restore", "op-1", otherSave)),
  );
  const again = c.issue(
    "restore",
    "op-1",
    fingerprint("restore", "op-1", base),
  );
  c.redeem(again, "restore", "op-1", fingerprint("restore", "op-1", base));
  assert.match(summary("restore", "op-1", base).facts[0][1], /^Y$/);
  assert.throws(() => summary("restore", "op-2", base), /no disponible/);
  assert.throws(
    () =>
      summary("restore", "op-1", {
        ...base,
        write: { ...base.write, busy: true },
      }),
    /no disponible/,
  );
});

test("a robbery ticket dies when the robbery moves on", () => {
  const t = {
    authorization_id: "a".repeat(36),
    side: "source",
    status: "PENDING_SOURCE",
    apply_started: false,
    location: { box: 1, slot: 2 },
  };
  const at = (status) => ({
    ...base,
    cloud: { data: { transfers: [{ ...t, status }] } },
  });
  const c = createConfirmations();
  const id = c.issue(
    "transfer:apply",
    t.authorization_id,
    fingerprint("transfer:apply", t.authorization_id, at("PENDING_SOURCE")),
  );
  assert.throws(() =>
    c.redeem(
      id,
      "transfer:apply",
      t.authorization_id,
      fingerprint("transfer:apply", t.authorization_id, at("VERIFYING_SOURCE")),
    ),
  );
  assert.match(
    summary("transfer:apply", t.authorization_id, at("PENDING_SOURCE")).detail,
    /Caja 1, posición 2/,
  );
  // The victim cannot cancel; nobody cancels after applying.
  assert.throws(() =>
    summary("transfer:cancel", t.authorization_id, at("PENDING_SOURCE")),
  );
  assert.throws(() => summary("transfer:steal", t.authorization_id, at("X")));
});

test("a write ticket needs the pending operation it describes", () => {
  const state = {
    ...base,
    write: { can_confirm: true, operation_id: "w1", description: "Añadir 3" },
  };
  assert.match(summary("write", "w1", state).message, /Añadir 3/);
  assert.throws(() => summary("write", "w2", state), /ya no está pendiente/);
  assert.notDeepEqual(
    fingerprint("write", "w1", state),
    fingerprint("write", "w1", {
      ...state,
      write: { ...state.write, description: "Añadir 999" },
    }),
  );
});

test("open robberies block restores until their delivery is verified", () => {
  assert.equal(robberyOpen([]), false);
  assert.equal(
    robberyOpen([{ obligation: "RECIPIENT_PHYSICAL_PENDING" }]),
    true,
  );
  assert.equal(robberyOpen([{ obligation: "RECIPIENT_VERIFIED" }]), false);
  assert.equal(
    robberyOpen([{ apply_started: true, status: "VERIFYING_BOTH" }]),
    true,
  );
  assert.equal(
    robberyOpen([{ apply_started: true, status: "COMMITTED" }]),
    false,
  );
  assert.equal(robberyOpen([{ mandatory: true }]), true);
});
