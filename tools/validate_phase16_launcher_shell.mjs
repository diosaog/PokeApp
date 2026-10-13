// Actual Electron main/preload/stdio boundary, with BrowserWindow never shown.
import { _electron as electron } from "../web/node_modules/@playwright/test/index.mjs";
import { createRequire } from "node:module";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
const root = process.cwd(),
  evidence = process.argv[2];
if (!evidence) throw new Error("Private evidence directory required");
const require = createRequire(import.meta.url);
const environment = { ...process.env };
delete environment.ELECTRON_RUN_AS_NODE;
const app = await electron.launch({
  executablePath: require("../companion/launcher/node_modules/electron"),
  args: [path.join(root, "companion/launcher/main.cjs")],
  env: {
    ...environment,
    POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
    POKEAPP_LAUNCHER_PROFILE: path.join(evidence, "shell-profile"),
    DOTNET_ROOT: "C:\\Program Files\\dotnet",
  },
});
try {
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const properties = await app.evaluate(({ BrowserWindow }) => {
    const window = BrowserWindow.getAllWindows()[0],
      prefs = window.webContents.getLastWebPreferences();
    return {
      visible: window.isVisible(),
      sandbox: prefs.sandbox,
      node: prefs.nodeIntegration,
      isolation: prefs.contextIsolation,
    };
  });
  assert.deepEqual(properties, {
    visible: false,
    sandbox: true,
    node: false,
    isolation: true,
  });
  const state = await page.evaluate(() => window.launcher.state(null));
  assert.equal(state.local_status, "NO_SAVE");
  const exposed = await page.evaluate(() => ({
    actions: Object.keys(window.launcher).sort(),
    node: typeof require,
    process: typeof process,
  }));
  assert.deepEqual(exposed.actions, [
    "chooseSave",
    "login",
    "logout",
    "retry",
    "state",
    "sync",
  ]);
  assert.equal(exposed.node, "undefined");
  assert.equal(exposed.process, "undefined");
  await page.locator("#cloud-tab").click();
  assert.equal(await page.locator("#cloud-view").isVisible(), true);
  assert.deepEqual(errors, []);
  const result = {
    status: "PASS",
    electron: "44.7.0",
    ...properties,
    exposed,
    errors,
  };
  await writeFile(
    path.join(evidence, "shell.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
} finally {
  await app.close();
}
