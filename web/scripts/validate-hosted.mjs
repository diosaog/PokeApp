// Invoked only by the explicit hosted fixture runner. No intercepted API or traces.
import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
if (input.web !== 'https://pokeapp-web.pokeapp-v2.workers.dev' ||
    input.api !== 'https://pokeapp-api-production.up.railway.app') throw new Error('Wrong hosted target');
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(30000);
const pageErrors = [], failures = [], mutations = [], screens = [], reads = [];
const pending = new Map();
let step = 'login';
page.on('request', r => {
  if (r.url().startsWith(input.api+'/v1/')) pending.set(r, Date.now());
});
page.on('requestfinished', r => {
  if (pending.has(r) && r.method() === 'GET') reads.push({ path: new URL(r.url()).pathname, ms: Date.now()-pending.get(r) });
  pending.delete(r);
});
page.on('requestfailed', r => pending.delete(r));
page.on('pageerror', e => pageErrors.push(e.message));
page.on('response', r => {
  if (!r.url().startsWith(input.api+'/v1/')) return;
  if (r.status() >= 400) failures.push({ path: new URL(r.url()).pathname, status: r.status() });
  if (['POST', 'PUT'].includes(r.request().method())) mutations.push({ path: new URL(r.url()).pathname, status: r.status() });
});
const assert = (ok, message) => { if (!ok) throw new Error(message); };
async function nav(name) {
  step = name;
  await page.getByRole('navigation').getByRole('link', { name, exact: true }).click();
  await page.locator('main').waitFor();
}
async function doneDialog(action) {
  await action();
  await page.getByRole('dialog').waitFor({ state: 'hidden' });
}
try {
  await page.goto(input.web+'/pc');
  await page.getByLabel('Entrenador', { exact: true }).fill(input.trainer);
  await page.getByLabel('PIN', { exact: true }).fill(input.pin);
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).click();
  await page.getByRole('button', { name: 'Cerrar sesión' }).waitFor();
  await page.getByRole('button', { name: /Synthetic 0/ }).first().click();
  await page.getByRole('dialog').getByText('Escama Especial', { exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await nav('Batallas');
  await page.getByRole('button', { name: 'Fijar mi equipo' }).click();
  await doneDialog(() => page.getByRole('button', { name: 'Confirmar mi equipo' }).click());
  await nav('Tienda');
  await page.getByRole('button', { name: 'Comprar', exact: true }).first().click();
  const basePrice = page.getByRole('dialog').getByRole('checkbox');
  if (await basePrice.count()) await basePrice.check();
  await doneDialog(() => page.getByRole('button', { name: 'Confirmar compra' }).click());
  await nav('Copa');
  await page.locator(`a[href="/copa/${input.cup}"]`).click();
  const results = page.getByLabel(/^Resultado /);
  await results.first().waitFor();
  for (const select of await results.all()) await select.selectOption('2:1');
  await page.getByRole('button', { name: 'Guardar resultados' }).click();
  await page.getByText('Cambio confirmado.').waitFor();
  await nav('Juicios');
  await page.getByRole('button', { name: /Hosted Discord agreement/ }).click();
  await page.getByRole('button', { name: 'Registrar decisión', exact: true }).click();
  const decision = page.getByRole('dialog', { name: 'Registrar decisión de Discord', exact: true });
  await decision.getByLabel('Resumen de la decisión').fill('Synthetic agreement for hosted validation');
  await decision.getByRole('checkbox', { name: 'Reducción de puntos' }).check();
  await decision.getByLabel('Puntos exactos').fill('1.25');
  await decision.getByRole('button', { name: 'Confirmar', exact: true }).click();
  await decision.waitFor({ state: 'hidden' });
  await page.keyboard.press('Escape');
  for (const name of ['Inicio', 'Liga', 'Entrenadores', 'Mi PC', 'Tienda', 'Copa', 'Hall de la Fama', 'Juicios', 'Administración', 'Saves y Launcher']) {
    await nav(name);
    // Assert the application has finished its own reads, independent of unrelated
    // hosting/browser connections. Record pending API paths on failure.
    await expect(page.locator('main .loading')).toHaveCount(0, { timeout: 60000 });
    await expect.poll(() => pending.size, { timeout: 60000 }).toBe(0);
    assert(await page.getByRole('alert').count() === 0, 'UI alert on '+name);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth+1), 'Overflow on '+name);
    screens.push(name);
  }
  await nav('Hall de la Fama');
  await page.getByRole('link', { name: 'Ver esta Copa' }).waitFor();
  await page.screenshot({ path: join(input.output, 'hosted-desktop-hall.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: join(input.output, 'hosted-mobile-hall.png'), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth+1), 'Mobile overflow');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).waitFor();
  assert(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0), 'Stored credentials');
  assert(pageErrors.length === 0, 'Browser page errors');
  assert(failures.length === 0, 'Hosted API returned an unexpected error');
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status:'PASS', api_interception:false, pageErrors, failures, mutations, screens, reads, desktop:[1440,1000], mobile:[390,844] }, null, 2));
  console.log('PASS real browser Cloudflare -> Railway -> V2; no mocked requests');
} catch (e) {
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status:'FAIL', step, message:String(e.message).replaceAll(input.pin,'[REDACTED]'), pageErrors, failures, mutations, screens, reads, pending:[...pending.keys()].map(r => new URL(r.url()).pathname) }, null, 2));
  throw new Error(String(e.message).replaceAll(input.pin,'[REDACTED]'));
} finally {
  await context.close();
  await browser.close();
}
