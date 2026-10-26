// The Launcher's native screens and the web share one palette (27B).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const primitives = (file) =>
  Object.fromEntries(
    [
      ...fs
        .readFileSync(file, "utf8")
        .matchAll(/(--c-[a-z0-9-]+):\s*(#[0-9a-f]+);/g),
    ].map((m) => [m[1], m[2]]),
  );

test("every Launcher palette primitive equals the web design token", () => {
  const web = primitives(
    path.join(__dirname, "../../web/src/design/tokens.css"),
  );
  const launcher = primitives(path.join(__dirname, "style.css"));
  assert.ok(Object.keys(launcher).length >= 15);
  for (const [name, value] of Object.entries(launcher))
    assert.equal(value, web[name], name);
});
