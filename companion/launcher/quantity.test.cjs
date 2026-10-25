const test = require("node:test");
const assert = require("node:assert/strict");
const { parse, step, clean } = require("./quantity.js");

test("plus and minus move one coherent value within 1..max", () => {
  assert.equal(step("1", -1, 99), "1");
  assert.equal(step("98", 1, 99), "99");
  assert.equal(step("99", 1, 99), "99");
  assert.equal(step("", 1, 99), "1");
  assert.equal(step("abc", 1, 99), "1");
  assert.equal(step("5", 1, 0), "0");
});

test("typed values: delete, rewrite, then buttons continue from the typed number", () => {
  let text = clean("12");
  text = clean("");
  assert.deepEqual(parse(text, 999), {
    value: null,
    error: "Escribe una cantidad.",
  });
  text = clean("250");
  assert.equal(parse(text, 999).value, 250);
  text = step(text, 1, 999);
  assert.equal(text, "251");
  text = step(clean("998"), 5, 999);
  assert.equal(text, "999");
});

test("invalid quantities are never confirmable", () => {
  for (const bad of ["0", "-3", "1.5", "1e3", " ", "", "10000"])
    assert.equal(parse(bad, 999).value, null, bad);
  assert.equal(parse("1000", 999).error, "El máximo que cabe ahora es 999.");
  assert.equal(parse("1", 0).error, "No cabe ninguna unidad más.");
  assert.equal(clean("-1.5e3"), "153");
  assert.equal(clean("12345"), "1234");
});
