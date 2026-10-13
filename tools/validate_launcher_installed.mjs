// Installed binary only. Hidden Electron window; no interaction with the desktop.
import { _electron as electron } from "../web/node_modules/@playwright/test/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import launcher from "../companion/launcher/package.json" with { type: "json" };

const [install, evidence, fixture] = process.argv.slice(2);
if (!install || !evidence || !fixture)
  throw new Error("install evidence synthetic-save required");
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
const expectedData = path.join(env.LOCALAPPDATA, "PokeApp", "Launcher");
const results = [];
for (let run = 0; run < 2; run++) {
  const app = await electron.launch({
    executablePath: path.join(install, "PokeApp Launcher.exe"),
    env,
    timeout: 30000,
  });
  try {
    const page = await app.firstWindow();
    await page.waitForLoadState("domcontentloaded");
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const properties = await app.evaluate(({ app, BrowserWindow }) => {
      const win = BrowserWindow.getAllWindows()[0],
        prefs = win.webContents.getLastWebPreferences();
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
    assert.equal(properties.data, path.join(expectedData, "shell"));
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
    const deadline = Date.now() + 15000;
    do {
      state = await page.evaluate(() => window.launcher.state(null));
      if (state.observation) break;
      await new Promise((resolve) => setTimeout(resolve, 200));
    } while (Date.now() < deadline);
    assert.equal(state.observation?.game, "X", JSON.stringify(state));
    assert.equal(state.observation.generation, 6);
    assert.equal(state.observation.boxes.length, 31);
    assert.equal(state.observation.progress, null);
    assert.equal(state.auth_status, "LOGIN_REQUIRED");
    assert.equal(await page.evaluate(() => typeof require), "undefined");
    await page.locator("#cloud-tab").click();
    assert.equal(await page.locator("#cloud-view").isVisible(), true);
    assert.deepEqual(errors, []);
    results.push({
      run,
      ...properties,
      game: state.observation.game,
      local_status: state.local_status,
      errors,
    });
    await page.screenshot({
      path: path.join(evidence, `installed-${run}.png`),
    });
  } finally {
    await app.close();
  }
}
assert.equal(digest(await readFile(fixture)), before);
await writeFile(
  path.join(expectedData, "preserve-on-upgrade.txt"),
  "Phase16C synthetic sentinel",
);
const result = {
  status: "PASS",
  runs: results,
  save_unchanged: true,
  developer_path_removed: true,
  default_data_outside_install: expectedData,
  cloud_login_not_attempted: true,
};
await writeFile(
  path.join(evidence, "installed-smoke.json"),
  JSON.stringify(result, null, 2),
);
console.log(JSON.stringify(result));
