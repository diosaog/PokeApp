import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";

const fillFirstIv = async (page: Page, stat: string, value: string) => {
  const input = page.getByTestId(`iv-${stat}`).first();
  await input.fill(value);
};

const fillLastIv = async (page: Page, stat: string, value: string) => {
  const input = page.getByTestId(`iv-${stat}`).last();
  await input.fill(value);
};

test("flujo principal de crianza sin persistencia automatica", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Optimizador de crianzas/i })).toBeVisible();

  await page.getByLabel("Dinero actual").fill("60000");
  await page.getByRole("button", { name: /Criadero/i }).click();

  await page.getByLabel("Mote").fill("Eevee madre");
  await page.getByTestId("pokemon-sex").selectOption("female");
  await fillFirstIv(page, "hp", "31");
  await fillFirstIv(page, "attack", "31");
  await fillFirstIv(page, "defense", "30");
  await fillFirstIv(page, "speed", "31");
  await page.getByRole("button", { name: /Guardar y anadir otro/i }).click();

  await page.getByLabel("Mote").fill("Furret padre");
  await page.getByTestId("species-select").selectOption("furret");
  await page.getByTestId("pokemon-sex").selectOption("male");
  await fillFirstIv(page, "specialDefense", "31");
  await page.getByRole("button", { name: /Guardar y anadir otro/i }).click();

  await page.getByLabel("Mote").fill("Rattata padre");
  await page.getByTestId("species-select").selectOption("rattata");
  await page.getByTestId("pokemon-sex").selectOption("male");
  await fillFirstIv(page, "specialAttack", "31");
  await page.getByRole("button", { name: /Guardar y anadir otro/i }).click();

  await expect(page.getByText(/3 Pokemon en memoria/i)).toBeVisible();

  await page.getByRole("button", { name: /Objetivo/i }).click();
  await page.getByRole("button", { name: /Optimizar/i }).click();
  await page.getByRole("button", { name: /^Ejecutar$/i }).click();
  await expect(page.getByText(/Mejor siguiente crianza/i)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Coste esperado/i)).toBeVisible();

  await page.getByLabel("Mote").fill("Cria real");
  await page.getByTestId("egg-sex").selectOption("female");
  await fillLastIv(page, "hp", "31");
  await fillLastIv(page, "defense", "31");
  await fillLastIv(page, "specialAttack", "31");
  await fillLastIv(page, "specialDefense", "31");
  await fillLastIv(page, "speed", "31");
  await page.getByRole("button", { name: /Registrar y recalcular luego/i }).click();

  await page.getByRole("button", { name: /Historial/i }).click();
  await expect(page.getByText(/Huevo registrado/i)).toBeVisible();
  await page.getByRole("button", { name: /^Deshacer$/i }).nth(1).click();
  await expect(page.getByText(/3 reproductores/i).first()).toBeVisible();
  await page.getByRole("button", { name: /Historial/i }).click();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /Exportar proyecto JSON/i }).click();
  const download = await downloadPromise;
  const path = await download.path();
  expect(path).toBeTruthy();
  const exported = await fs.readFile(path ?? "", "utf8");

  await page.reload();
  await expect(page.getByText(/0 reproductores/i).first()).toBeVisible();

  await page.getByRole("button", { name: /Historial/i }).click();
  await page.getByPlaceholder("Pega aqui un JSON exportado").fill(exported);
  await page.getByRole("button", { name: /Importar proyecto/i }).click();
  await expect(page.getByText(/3 reproductores/i).first()).toBeVisible();
});
