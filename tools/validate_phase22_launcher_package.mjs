// Unpacked candidate, not an installed/clean-machine acceptance claim.
// No owner profile, credentials, target mutation or network command.
import { _electron as electron } from "../web/node_modules/@playwright/test/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import launcher from "../companion/launcher/package.json" with { type: "json" };

const [unpacked, evidence, fixture] = process.argv.slice(2);
if (!unpacked || !evidence || !fixture)
  throw new Error("unpacked evidence fixture-copy required");
await mkdir(evidence, { recursive: true });
const digest = (data) => createHash("sha256").update(data).digest("hex");
const before = digest(await readFile(fixture));
const env = { ...process.env };
for (const key of Object.keys(env))
  if (
    /^(PATH|PYTHON.*|DOTNET.*|NODE_.*|ELECTRON_RUN_AS_NODE|POKEAPP_LAUNCHER_.*)$/i.test(
      key,
    )
  )
    delete env[key];
Object.assign(env, {
  PATH: `${process.env.SystemRoot}\\System32;${process.env.SystemRoot}`,
  DOTNET_ROOT: path.join(evidence, "unavailable-dotnet"),
  DOTNET_MULTILEVEL_LOOKUP: "0",
  LOCALAPPDATA: path.join(evidence, "local-data"),
  POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
  POKEAPP_LAUNCHER_PYTHON: path.join(evidence, "unavailable-python.exe"),
  POKEAPP_LAUNCHER_PARSER: path.join(evidence, "unavailable-parser.exe"),
});
const results = [];
for (let run = 0; run < 2; run++) {
  const app = await electron.launch({
    executablePath: path.join(unpacked, "PokeApp Launcher.exe"),
    env,
    timeout: 30000,
  });
  try {
    const page = await app.firstWindow();
    await page.waitForLoadState("domcontentloaded");
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const properties = await app.evaluate(({ app, BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0];
      const prefs = win.webContents.getLastWebPreferences();
      return {
        packaged: app.isPackaged,
        version: app.getVersion(),
        data: app.getPath("userData"),
        visible: win.isVisible(),
        sandbox: prefs.sandbox,
        node: prefs.nodeIntegration,
        isolation: prefs.contextIsolation,
      };
    });
    assert.equal(properties.packaged, true);
    assert.equal(properties.version, launcher.version);
    assert.equal(
      properties.data,
      path.join(env.LOCALAPPDATA, "PokeApp", "Launcher", "shell"),
    );
    assert.equal(properties.visible, false);
    assert.equal(properties.sandbox, true);
    assert.equal(properties.node, false);
    assert.equal(properties.isolation, true);
    if (run === 0) {
      const initial = await page.evaluate(() => window.launcher.state(null));
      assert.equal(initial.local_status, "NO_SAVE");
      await app.evaluate(({ dialog }, input) => {
        dialog.showOpenDialog = async () => ({
          canceled: false,
          filePaths: [input],
        });
      }, fixture);
      await page.evaluate(() => window.launcher.chooseSave());
    }
    let state;
    const deadline = Date.now() + 20000;
    do {
      state = await page.evaluate(() => window.launcher.state(null));
      if (state.observation && state.local_status === "READY") break;
      await new Promise((resolve) => setTimeout(resolve, 200));
    } while (Date.now() < deadline);
    assert.equal(state.observation?.game, "X");
    assert.equal(state.observation.generation, 6);
    assert.equal(state.observation.boxes.length, 31);
    assert.equal(state.auth_status, "LOGIN_REQUIRED");
    assert.equal(state.write.status, "IDLE");
    assert.equal(state.write.production_operations_enabled, false);
    assert.equal(state.write.can_confirm, false);
    assert.equal(await page.evaluate(() => typeof require), "undefined");
    const exposed = await page.evaluate(() =>
      Object.keys(window.launcher).sort(),
    );
    assert.deepEqual(exposed, [
      "chooseSave",
      "confirmWrite",
      "login",
      "logout",
      "reconcileWrite",
      "retry",
      "state",
      "sync",
    ]);
    const denial = await page.evaluate(async () => {
      try {
        await window.launcher.confirmWrite("forged-operation", true);
        return false;
      } catch {
        return true;
      }
    });
    assert.equal(denial, true);
    assert.equal(await page.locator("#write-confirmation").isHidden(), true);
    assert.match(
      await page.locator("#write-state").innerText(),
      /No hay cambios autorizados/,
    );
    // Renderer-only states: no bridge request or physical write from this part.
    const rendering = await page.evaluate((current) => {
      const variants = [];
      for (const status of [
        "AWAITING_CONFIRMATION",
        "APPLIED_VERIFIED",
        "RECOVERY_REQUIRED",
      ]) {
        render({
          ...current,
          write: {
            status,
            operation_id: "renderer-fixture",
            game: "X",
            can_confirm: status === "AWAITING_CONFIRMATION",
            can_reconcile: true,
            description: "Prueba aislada: marca de 0 a 1.",
            message: "Estado de prueba visual",
          },
        });
        variants.push({
          status,
          confirmationHidden:
            document.getElementById("write-confirmation").hidden,
          confirmationDisabled:
            document.getElementById("confirm-write").disabled,
          selectionDisabled: document.getElementById("select-save").disabled,
        });
      }
      render(current);
      return variants;
    }, state);
    assert.equal(rendering[0].confirmationHidden, false);
    assert.equal(rendering[0].confirmationDisabled, true);
    assert.equal(rendering[1].confirmationHidden, true);
    assert.equal(rendering[2].selectionDisabled, true);
    await page.screenshot({
      path: path.join(evidence, `candidate-${run}.png`),
    });
    await page.locator("#cloud-tab").click();
    assert.equal(await page.locator("#cloud-view").isVisible(), true);
    assert.deepEqual(errors, []);
    results.push({
      run,
      ...properties,
      game: state.observation.game,
      local_status: state.local_status,
      no_login: true,
      forged_write_denied: denial,
      rendering,
      errors,
    });
  } finally {
    await app.close();
  }
}
assert.equal(digest(await readFile(fixture)), before);
const result = {
  status: "PASS",
  scope: "unpacked isolated candidate; not owner installation",
  runs: results,
  save_unchanged: true,
  developer_runtimes_unavailable: true,
  positive_write_via_renderer: false,
};
await writeFile(
  path.join(evidence, "package-smoke.json"),
  JSON.stringify(result, null, 2),
);
console.log(JSON.stringify(result));
