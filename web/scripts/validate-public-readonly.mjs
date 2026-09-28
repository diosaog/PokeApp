// Existing owner session, public deployments, GET-only after login. No fixtures.
import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
if (input.web !== 'https://pokeapp-web.pokeapp-v2.workers.dev' ||
    input.api !== 'https://pokeapp-api-production.up.railway.app') throw new Error('Wrong public target');
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(60000);
const pending = new Set(), reads = [], errors = [], unexpected = [], screens = [];
const environmentOrigins = {};
let step = 'login';
page.on('pageerror', e => errors.push(e.message));
page.on('request', r => {
  const u = new URL(r.url());
  // The installed antivirus injects this origin into Edge, including long polling.
  // It is absent from the served app/assets. Record it without its session paths;
  // do not disable protection, intercept requests or allow arbitrary third parties.
  if (u.origin === 'https://me.kis.v2.scr.kaspersky-labs.com')
    environmentOrigins[u.origin] = (environmentOrigins[u.origin] || 0) + 1;
  else if (![input.web, input.api].includes(u.origin)) unexpected.push({ origin: u.origin, path: u.pathname });
  if (u.origin !== input.api) return;
  pending.add(r);
  if (r.method() !== 'GET' && u.pathname !== '/v1/auth/pin-login' && u.pathname !== '/v1/auth/refresh')
    unexpected.push({ method: r.method(), path: u.pathname });
});
page.on('requestfinished', r => pending.delete(r));
page.on('requestfailed', r => pending.delete(r));
page.on('response', r => {
  if (!r.url().startsWith(input.api+'/v1/')) return;
  reads.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() });
});
try {
  await page.goto(input.web);
  await page.getByLabel('Entrenador', { exact: true }).fill(input.identifier);
  await page.getByLabel('PIN', { exact: true }).fill(input.pin);
  const me = page.waitForResponse(r => r.url() === input.api+'/v1/me' && r.status() === 200);
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).click();
  const identity = await (await me).json();
  expect(identity.trainer_id).toBe(input.trainer_id);
  expect(identity.is_admin).toBe(true);
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    for (const name of ['Inicio', 'Liga', 'Battle', 'Entrenadores', 'Mi PC', 'Tienda', 'Copa', 'Hall de la Fama', 'Juicios', 'Administración', 'Saves y Launcher']) {
      step = name+' '+viewport.width;
      const menu = page.getByRole('button', { name: 'Abrir navegación' });
      if (await menu.isVisible()) await menu.click();
      await page.getByRole('navigation').getByRole('link', { name, exact: true }).click();
      await expect(page.locator('main .loading')).toHaveCount(0, { timeout: 60000 });
      await expect.poll(() => pending.size, { timeout: 60000 }).toBe(0);
      await expect(page.getByRole('alert')).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
      screens.push(step);
    }
    await page.screenshot({ path: join(input.output, 'public-readonly-'+viewport.width+'.png'), fullPage: true });
  }
  expect(errors).toEqual([]);
  expect(unexpected).toEqual([]);
  expect(reads.filter(r => r.status >= 400)).toEqual([]);
  expect(reads.some(r => r.path.startsWith('/v1/admin/') && r.status === 200)).toBe(true);
  const menu = page.getByRole('button', { name: 'Abrir navegación' });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).waitFor();
  expect(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0)).toBe(true);
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status: 'PASS', api_interception: false, business_writes: 0, screens, reads, errors, unexpected, environmentOrigins }, null, 2));
  console.log('PASS owner real public reads: eleven screens desktop/mobile, admin, logout, zero business writes; local antivirus origin recorded separately');
} catch (e) {
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status: 'FAIL', step, message: String(e.message).replaceAll(input.pin, '[REDACTED]'), screens, reads, errors, unexpected, environmentOrigins }, null, 2));
  throw new Error('Public read-only validation failed; credentials suppressed');
} finally {
  await context.close();
  await browser.close();
}
