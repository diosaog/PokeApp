// Real dev Electron + private Python stdio; never an installed/package claim.
import { _electron as electron } from "../web/node_modules/@playwright/test/index.mjs";
import { createRequire } from "node:module";
import { readFile, writeFile, chmod, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import assert from "node:assert/strict";
const require = createRequire(import.meta.url);
const [workspace, native] = process.argv.slice(2);
if (!workspace || !native)
  throw new Error("owned seeded fixture workspace and native required");
const seed = JSON.parse(
  await readFile(path.join(workspace, "seed.json"), "utf8"),
);
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const before = digest(await readFile(seed.target));
const results = [];
for (const available of [true, false]) {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  Object.assign(env, {
    POKEAPP_LAUNCHER_PROFILE: seed.profile,
    POKEAPP_LAUNCHER_HEADLESS_TEST: "1",
    POKEAPP_LAUNCHER_PARSER: available
      ? native
      : path.join(workspace, "missing-parser.exe"),
  });
  const app = await electron.launch({
    executablePath: require("../companion/launcher/node_modules/electron"),
    args: [path.resolve("companion/launcher/main.cjs")],
    env,
  });
  try {
    const page = await app.firstWindow();
    await page.waitForLoadState("domcontentloaded");
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.locator("#refresh-backups").click();
    await page.waitForFunction(() =>
      document.querySelector("#backup-list").textContent.includes("Verificada"),
    );
    const state = await page.evaluate(() => window.launcher.state());
    assert.equal(state.write.production_operations_enabled, false);
    assert.equal(state.write.emulator_qualified, false);
    assert.equal(state.write.can_confirm, false);
    assert.equal(state.write.backups.length, 1);
    assert.equal(state.write.backups[0].can_restore, false);
    assert.equal(
      await page.getByRole("button", { name: "Restaurar copia…" }).count(),
      0,
    );
    assert.equal(await page.evaluate(() => typeof require), "undefined");
    const copied = path.join(
      workspace,
      available ? "ui-copy.sav" : "ui-copy-no-native.sav",
    );
    await app.evaluate(({ dialog }, destination) => {
      dialog.showSaveDialog = async () => ({
        canceled: false,
        filePath: destination,
      });
    }, copied);
    await page.getByRole("button", { name: "Guardar copia…" }).click();
    await page.waitForFunction(() =>
      document
        .querySelector("#backup-notice")
        .textContent.includes("guardada y verificada"),
    );
    assert.equal(digest(await readFile(copied)), before);
    assert.equal(digest(await readFile(seed.target)), before);
    const denied = await page.evaluate(async (operation) => {
      const actions = [
        () =>
          window.launcher.saveBackup(
            "00000000-0000-0000-0000-000000000000",
            "original",
          ),
        () => window.launcher.restoreBackup(operation, false),
        () => window.launcher.restoreBackup(operation, true),
        () => window.launcher.exportSave(),
      ];
      const rejected = [];
      for (const action of actions) {
        try {
          await action();
          rejected.push(false);
        } catch {
          rejected.push(true);
        }
      }
      return rejected;
    }, seed.operation);
    assert.deepEqual(denied, [true, true, true, true]);
    const frameDenied = await app.evaluate(async ({ ipcMain }) => {
      try {
        await ipcMain._invokeHandlers.get("launcher:backups")({ sender: null });
        return false;
      } catch {
        return true;
      }
    });
    assert.equal(frameDenied, true);
    if (!available) {
      await chmod(seed.backup, 0o666);
      await writeFile(seed.backup, "deliberately corrupt disposable backup");
      await page.locator("#refresh-backups").click();
      await page.waitForFunction(() =>
        document
          .querySelector("#backup-list")
          .textContent.includes("Inválida o ilegible"),
      );
      assert.equal(
        await page.getByRole("button", { name: "Guardar copia…" }).isDisabled(),
        true,
      );
    }
    await mkdir(path.join(workspace, "screens"), { recursive: true });
    await page.screenshot({
      path: path.join(
        workspace,
        "screens",
        available ? "backups.png" : "invalid-backup.png",
      ),
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    results.push({
      native_available: available,
      exact_backup_copy: true,
      source_unchanged: true,
      ipc_denials: 5,
      production_writes: false,
      browser_errors: errors,
    });
  } finally {
    await app.close();
  }
}
assert.equal(digest(await readFile(seed.target)), before);
await writeFile(
  path.join(workspace, "ui-evidence.json"),
  JSON.stringify(
    {
      status: "PASS",
      scope: "dev Electron, isolated profile; not packaged or real emulator",
      results,
    },
    null,
    2,
  ),
);
console.log(
  "PASS: two isolated Electron launches; exact native-free backup copies; 10 IPC denials; invalid backup UI",
);
