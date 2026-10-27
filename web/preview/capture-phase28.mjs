// Phase 28 design captures from the local design preview (synthetic data).
// Usage: node preview/capture-phase28.mjs <output-dir>   (preview running)
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "@playwright/test";

const out = process.argv[2];
if (!out) throw new Error("Output directory required");
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  channel: process.platform === "win32" ? "msedge" : undefined,
});
for (const [label, width, height] of [
  ["desktop", 1440, 900],
  ["mobile", 390, 844],
]) {
  const page = await browser.newPage({ viewport: { width, height } });
  const shot = (name) =>
    page.screenshot({ path: join(out, `web-${name}-${label}.png`) });
  await page.goto("http://127.0.0.1:4173/");
  await page.getByLabel("Entrenador", { exact: true }).fill("Antonio");
  await page.getByLabel("PIN", { exact: true }).fill("1234");
  await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await page.waitForSelector(".sidebar", { state: "attached" });
  const go = async (name) => {
    const menu = page.getByRole("button", { name: "Abrir navegación" });
    if (await menu.isVisible()) await menu.click();
    await page
      .getByRole("navigation", { name: "Principal" })
      .getByRole("link", { name, exact: true })
      .click();
  };
  await go("Saves y Launcher");
  await page.waitForTimeout(600);
  await shot("saves");
  await page.getByRole("button", { name: "Copias de seguridad" }).click();
  await shot("saves-copias");
  await go("Entrenadores");
  await page.locator("a[href^='/entrenadores/1']").first().click();
  await page.waitForSelector(".profile-inventory");
  await page.locator(".unlimited-section").scrollIntoViewIfNeeded();
  await shot("inventory");
  await page.getByRole("button", { name: "Añadir a la bolsa" }).first().click();
  await page.waitForTimeout(400);
  await shot("item-popup");
  await page.keyboard.press("Escape");
  await go("Administración");
  await page.getByRole("button", { name: /Economía e incidencias/ }).click();
  await page.waitForTimeout(600);
  await shot("admin-incidents");
  await page.getByRole("button", { name: "Reembolsar" }).first().click();
  await page.waitForTimeout(400);
  await shot("admin-refund");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /Cuentas y sistema/ }).click();
  await page.waitForTimeout(400);
  await shot("admin-accounts");
  await page.close();
}
await browser.close();
