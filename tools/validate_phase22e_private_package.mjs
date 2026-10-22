// Installed private app only; separate default profile, no remote login or write authority.
import { _electron as electron } from "../web/node_modules/@playwright/test/index.mjs";
import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import launcher from "../companion/launcher/package.json" with { type: "json" };
const [install, workspace, mode] = process.argv.slice(2);
assert.ok(
  install && workspace && ["read", "recovery", "restart"].includes(mode),
);
const hash = (b) => createHash("sha256").update(b).digest("hex");
const fixture = path.join(workspace, "main");
const seed =
  mode === "read"
    ? null
    : JSON.parse(await readFile(path.join(workspace, "seed.json"), "utf8"));
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
  LOCALAPPDATA: path.join(workspace, "local-data"),
  DOTNET_ROOT: path.join(workspace, "unavailable-dotnet"),
  DOTNET_MULTILEVEL_LOOKUP: "0",
  POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
  POKEAPP_LAUNCHER_PYTHON: "unavailable-python.exe",
  POKEAPP_LAUNCHER_PARSER: "unavailable-parser.exe",
});
const profile = path.join(env.LOCALAPPDATA, "PokeApp", "Launcher-Private");
await mkdir(workspace, { recursive: true });
const app = await electron.launch({
  executablePath: path.join(install, "PokeApp Launcher Private.exe"),
  env,
  timeout: 30000,
});
let result;
try {
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const props = await app.evaluate(({ app, BrowserWindow }) => {
    const win = BrowserWindow.getAllWindows()[0],
      prefs = win.webContents.getLastWebPreferences();
    return {
      packaged: app.isPackaged,
      version: app.getVersion(),
      userData: app.getPath("userData"),
      visible: win.isVisible(),
      sandbox: prefs.sandbox,
      isolation: prefs.contextIsolation,
      node: prefs.nodeIntegration,
    };
  });
  assert.equal(props.packaged, true);
  assert.equal(props.version, launcher.version);
  assert.equal(props.userData, path.join(profile, "shell"));
  assert.equal(props.visible, false);
  assert.equal(props.sandbox, true);
  assert.equal(props.isolation, true);
  assert.equal(props.node, false);
  let state = await page.evaluate(() => window.launcher.state());
  if (mode === "read") {
    assert.equal(state.local_status, "NO_SAVE");
    await app.evaluate(({ dialog }, input) => {
      dialog.showOpenDialog = async () => ({
        canceled: false,
        filePaths: [input],
      });
    }, fixture);
    await page.evaluate(() => window.launcher.chooseSave());
    const deadline = Date.now() + 20000;
    do {
      state = await page.evaluate(() => window.launcher.state(null));
      if (state.local_status === "READY" && state.observation?.game === "X")
        break;
      await new Promise((resolve) => setTimeout(resolve, 200));
    } while (Date.now() < deadline);
    assert.equal(state.local_status, "READY", JSON.stringify(state));
    assert.equal(state.observation?.game, "X", JSON.stringify(state));
    assert.equal(state.observation.boxes.length, 31);
    assert.equal(state.cloud_sync, false);
    assert.equal(state.auth_status, "LOGIN_REQUIRED");
    await page.locator("#cloud-tab").click();
    assert.equal(await page.locator("#cloud-view").isVisible(), true);
    await writeFile(
      path.join(profile, "preserve-on-upgrade.txt"),
      "Phase22E isolated sentinel",
    );
    result = {
      mode,
      native_read: true,
      original_sha256: hash(await readFile(fixture)),
    };
  } else {
    assert.equal(state.write.status, "RECOVERY_REQUIRED");
    assert.equal(state.write.restart_blocked_by_recovery, true);
    assert.equal(state.write.emulator_restart_allowed, false);
    await page.locator("#refresh-backups").click();
    await page.waitForFunction(() =>
      document.querySelector("#backup-list").textContent.includes("Verificada"),
    );
    state = await page.evaluate(() => window.launcher.state());
    assert.equal(state.write.backups.length, 1);
    assert.equal(state.write.backups[0].can_restore, false);
    const destination = path.join(workspace, `backup-${mode}.sav`);
    await app.evaluate(({ dialog }, file) => {
      dialog.showSaveDialog = async (_win, options) => {
        if (options.buttonLabel !== "Guardar copia")
          throw Error("wrong native dialog options");
        return { canceled: false, filePath: file };
      };
    }, destination);
    await page.getByRole("button", { name: "Guardar copia…" }).click();
    await page.waitForFunction(() =>
      document
        .querySelector("#backup-notice")
        .textContent.includes("guardada y verificada"),
    );
    assert.equal(hash(await readFile(destination)), seed.original_sha256);
    const denied = await page.evaluate(async (operation) => {
      const calls = [
        () => window.launcher.restoreBackup(operation, false),
        () => window.launcher.restoreBackup(operation, true),
        () => window.launcher.confirmWrite(operation, true),
        () => window.launcher.exportSave(),
      ];
      const rejected = [];
      for (const call of calls) {
        try {
          await call();
          rejected.push(false);
        } catch {
          rejected.push(true);
        }
      }
      return rejected;
    }, seed.operation);
    assert.deepEqual(denied, [true, true, true, true]);
    assert.equal(hash(await readFile(seed.backup)), seed.original_sha256);
    await assert.rejects(access(fixture));
    result = {
      mode,
      exact_backup_copy: true,
      restore_and_write_denials: 4,
      recovery_preserved: true,
      dialog_response_controlled: true,
    };
  }
  assert.equal(state.write.production_operations_enabled, false);
  assert.equal(state.write.can_confirm, false);
  assert.equal(state.emulator.qualified, false);
  assert.equal(state.emulator.automatic_lifecycle_enabled, false);
  assert.equal(state.emulator.candidate_version, "2126.2");
  assert.equal(await page.evaluate(() => typeof require), "undefined");
  assert.deepEqual(errors, []);
  await page.screenshot({ path: path.join(workspace, `packaged-${mode}.png`) });
  result = {
    status: "PASS",
    ...result,
    ...props,
    errors,
    production_writes: false,
    emulator_certified: false,
    developer_runtimes_removed: true,
  };
} finally {
  await app.close();
}
await writeFile(
  path.join(workspace, `packaged-${mode}.json`),
  JSON.stringify(result, null, 2),
);
console.log(JSON.stringify(result));
