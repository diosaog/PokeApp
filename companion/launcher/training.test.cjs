const test = require("node:test");
const assert = require("node:assert/strict");
const t = require("./training.js");
const {
  describe,
  fingerprint,
  createConfirmations,
} = require("./confirmations.cjs");
const purchase = "a0000000-0000-4000-8000-000000000001";
const pokemon = "b0000000-0000-4000-8000-000000000001";
const input = (change) => ({
  purchase_id: purchase,
  pokemon_entity_id: pokemon,
  source_sha256: "a".repeat(64),
  change,
});
const state = (effect = "nature") => ({
  principal: { trainer_id: "c0000000-0000-4000-8000-000000000001" },
  selected_save: "C:/isolated/main",
  receipt_id: "r1",
  write: { status: "IDLE", busy: false },
  training: {
    application_enabled: true,
    items: [
      {
        purchase_id: purchase,
        item_code: "menta_naturaleza",
        name: "Menta de Naturaleza",
        effect,
      },
    ],
    targets: [
      {
        pokemon_entity_id: pokemon,
        source_sha256: "a".repeat(64),
        pokemon: {
          species: "Pikachu",
          species_id: 25,
          nickname: "Chispa",
          level: 12,
          nature_id: 0,
          ivs: { hp: 31, atk: 14, defense: 4, spa: 13, spd: 12, spe: 29 },
        },
      },
    ],
    operations: [],
  },
});
test("25 Spanish natures include all neutral choices and the expected stat changes", () => {
  assert.equal(t.natures.length, 25);
  assert.deepEqual(
    t.natures.filter((n) => n.modifier === "Neutra").map((n) => n.name),
    ["Fuerte", "Dócil", "Seria", "Tímida", "Rara"],
  );
  assert.deepEqual(
    t.natures.map((n) => n.name),
    [
      "Fuerte",
      "Huraña",
      "Audaz",
      "Firme",
      "Pícara",
      "Osada",
      "Dócil",
      "Plácida",
      "Agitada",
      "Floja",
      "Miedosa",
      "Activa",
      "Seria",
      "Alegre",
      "Ingenua",
      "Modesta",
      "Afable",
      "Mansa",
      "Tímida",
      "Alocada",
      "Serena",
      "Amable",
      "Grosera",
      "Cauta",
      "Rara",
    ],
  );
  assert.deepEqual(
    t.natures.filter((n) => n.modifier !== "Neutra").map((n) => n.modifier),
    [
      "+Ataque, −Defensa",
      "+Ataque, −Velocidad",
      "+Ataque, −Ataque Especial",
      "+Ataque, −Defensa Especial",
      "+Defensa, −Ataque",
      "+Defensa, −Velocidad",
      "+Defensa, −Ataque Especial",
      "+Defensa, −Defensa Especial",
      "+Velocidad, −Ataque",
      "+Velocidad, −Defensa",
      "+Velocidad, −Ataque Especial",
      "+Velocidad, −Defensa Especial",
      "+Ataque Especial, −Ataque",
      "+Ataque Especial, −Defensa",
      "+Ataque Especial, −Velocidad",
      "+Ataque Especial, −Defensa Especial",
      "+Defensa Especial, −Ataque",
      "+Defensa Especial, −Defensa",
      "+Defensa Especial, −Velocidad",
      "+Defensa Especial, −Ataque Especial",
    ],
  );
});
test("training payload is an exact purchase/entity/save/change tuple, with no extra fields", () => {
  assert.deepEqual(
    t.parse(t.key(input({ kind: "nature", nature_id: 3 }))),
    input({ kind: "nature", nature_id: 3 }),
  );
  for (const value of [
    null,
    { ...input({ kind: "ivs" }), path: "C:/other" },
    input({ kind: "nature", nature_id: 25 }),
    input({ kind: "nature", nature_id: "3" }),
    input({ kind: "iv", stat: "speed" }),
    input({ kind: "ivs", nature_id: 1 }),
    { ...input({ kind: "ivs" }), source_sha256: "b".repeat(63) },
  ])
    assert.throws(() => t.input(value));
});
test("final main summary shows actual nature and rejects stale or redundant edits", () => {
  const s = state(),
    value = input({ kind: "nature", nature_id: 3 });
  const offer = describe("training", t.key(value), s);
  assert.match(offer.message, /Chispa.*Nv\. 12/);
  assert.match(offer.message, /Fuerte → Firme \(\+Ataque, −Ataque Especial\)/);
  assert.match(offer.detail, /naturaleza real/);
  assert.equal(offer.go, "Confirmar");
  assert.throws(
    () => t.selection(s, input({ kind: "nature", nature_id: 0 })),
    /ya tiene/,
  );
  assert.throws(
    () => t.selection(s, { ...value, source_sha256: "f".repeat(64) }),
    /ya no están disponibles/,
  );
  s.training.operations = [{ purchase_id: purchase, status: "RESERVED" }];
  assert.throws(() => t.selection(s, value), /ya no están disponibles/);
});
test("single IV shows the current stat, warns about Hidden Power, and refuses 31 or wrong purchase", () => {
  const s = state("iv"),
    value = input({ kind: "iv", stat: "atk" });
  const offer = describe("training", t.key(value), s);
  assert.match(offer.message, /Ataque: 14 → 31/);
  assert.match(offer.detail, /tipo de Poder Oculto/);
  assert.throws(
    () => t.selection(s, input({ kind: "iv", stat: "hp" })),
    /máximo/,
  );
  assert.throws(
    () => t.selection(s, input({ kind: "ivs" })),
    /ya no están disponibles/,
  );
});
test("Gold Cap previews all six IVs and refuses an already perfect Pokémon", () => {
  const s = state("ivs"),
    value = input({ kind: "ivs" });
  const offer = describe("training", t.key(value), s);
  for (const label of [
    "PS: 31 → 31",
    "Ataque: 14 → 31",
    "Defensa: 4 → 31",
    "Ataque Especial: 13 → 31",
    "Defensa Especial: 12 → 31",
    "Velocidad: 29 → 31",
  ])
    assert(offer.message.includes(label));
  s.training.targets[0].pokemon.ivs = Object.fromEntries(
    t.stats.map(([id]) => [id, 31]),
  );
  assert.throws(() => t.selection(s, value), /seis IV ya/);
});
test("confirmation ticket cannot switch Pokémon, change, save, current values or be replayed", () => {
  const s = state(),
    value = input({ kind: "nature", nature_id: 3 }),
    target = t.key(value),
    c = createConfirmations();
  const issue = () =>
    c.issue("training", target, fingerprint("training", target, s));
  let ticket = issue();
  assert.throws(() =>
    c.redeem(
      ticket,
      "training",
      t.key(input({ kind: "nature", nature_id: 4 })),
      fingerprint("training", target, s),
    ),
  );
  ticket = issue();
  s.training.targets[0].pokemon.level++;
  assert.throws(() =>
    c.redeem(ticket, "training", target, fingerprint("training", target, s)),
  );
  ticket = issue();
  s.principal.trainer_id = "d0000000-0000-4000-8000-000000000001";
  assert.throws(() =>
    c.redeem(ticket, "training", target, fingerprint("training", target, s)),
  );
  ticket = issue();
  c.redeem(ticket, "training", target, fingerprint("training", target, s));
  assert.throws(() =>
    c.redeem(ticket, "training", target, fingerprint("training", target, s)),
  );
});
test("recovery and active writes block training; fixed sprite paths cannot carry arbitrary URLs", () => {
  const s = state(),
    value = input({ kind: "nature", nature_id: 3 });
  s.write.status = "RECOVERY_REQUIRED";
  assert.throws(() => t.selection(s, value), /operación pendiente/);
  assert.equal(
    t.sprite({ species_id: 25, form: 0 }),
    "https://pokeapp-web.pokeapp-v2.workers.dev/visuals/v1/pokemon/25.png",
  );
  assert.equal(
    t.sprite({ species_id: 479, form: 1 }),
    "https://pokeapp-web.pokeapp-v2.workers.dev/visuals/v1/pokemon/479-form-1.png",
  );
  assert.equal(t.sprite({ species_id: 25, form: 99 }), null);
  assert.equal(t.sprite({ species_id: "https://evil.test" }), null);
  assert.equal(t.speciesName({ species: "Pokémon #25" }), "Pikachu");
  assert.equal(t.speciesName({ species: "Species #700" }), "Sylveon");
});
