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
    for (const name of ['Inicio', 'Liga', 'Batallas', 'Entrenadores', 'Mi PC', 'Tienda', 'Copa', 'Hall de la Fama', 'Juicios', 'Administración', 'Saves y Launcher']) {
      step = name+' '+viewport.width;
      const menu = page.getByRole('button', { name: 'Abrir navegación' });
      if (await menu.isVisible()) await menu.click();
      await page.getByRole('navigation').getByRole('link', { name, exact: true }).click();
      await expect(page.locator('main .loading')).toHaveCount(0, { timeout: 60000 });
      await expect.poll(() => pending.size, { timeout: 60000 }).toBe(0);
      const alerts = page.getByRole('alert');
      if (name === 'Batallas') {
        // H deliberately surfaces missing competitive locks as warnings.
        await expect(alerts.filter({ hasNot: page.locator('strong', { hasText: /^Falta el Team Lock de este entrenador\.$/ }) })).toHaveCount(0);
      } else await expect(alerts).toHaveCount(0);
      if (name === 'Liga' && input.league_checks) {
        const checks = input.league_checks;
        const tabs = page.getByRole('navigation', { name: 'Vistas de Liga' });
        await expect(tabs.getByRole('button', { name: 'GENERAL', exact: true })).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByRole('heading', { name: 'Clasificación general', exact: true })).toBeVisible();
        for (const title of ['Puntos totales', 'Monedas', 'Pokémon muertos'])
          await expect(page.getByRole('columnheader', { name: title, exact: true })).toBeVisible();
        await expect(page.locator('.league-standings tbody tr')).toHaveCount(checks.rows);
        await expect(tabs.getByRole('button')).toHaveCount(checks.days.length + 1);
        if (input.wipe_checks) {
          // Inspect the participant-owned value without filling or submitting it.
          const wipe = input.wipe_checks;
          await expect(page.getByRole('heading', { name: 'Revividos tras wipe', exact: true })).toBeVisible();
          await expect(page.getByText(`Cantidad registrada: ${wipe.revived_after_wipe}`, { exact: true })).toBeVisible();
          if (wipe.editable) {
            await expect(page.getByLabel('Cantidad de revividos tras wipe', { exact: true })).toHaveValue(String(wipe.revived_after_wipe));
            await expect(page.getByRole('button', { name: 'Actualizar revividos', exact: true })).toBeVisible();
          }
          if (wipe.visible_deaths_unknown)
            await expect(page.getByText(/^Pendiente de observar las muertes del save\./)).toBeVisible();
          await page.screenshot({ path: join(input.output, 'public-wipe-revivals-'+viewport.width+'.png'), fullPage: true });
        }
        await page.screenshot({ path: join(input.output, 'public-general-'+viewport.width+'.png'), fullPage: true });
        if (checks.current_day_number != null) {
          await tabs.getByRole('button', { name: `J${checks.current_day_number}`, exact: true }).click();
          await expect(page.locator('main .loading')).toHaveCount(0);
          await expect.poll(() => pending.size).toBe(0);
          await expect(page.getByRole('alert').filter({ hasNot: page.locator('strong', { hasText: /^Tu Team Lock está pendiente\.$/ }) })).toHaveCount(0);
          await expect(page.getByRole('heading', { name: 'Registrar resultados', exact: true })).toHaveCount(checks.can_record ? 1 : 0);
          expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
          await page.screenshot({ path: join(input.output, 'public-current-day-'+viewport.width+'.png'), fullPage: true });
        }
        await tabs.getByRole('button', { name: 'GENERAL', exact: true }).click();
      }
      if (name.startsWith('Administraci') && input.championship_checks) {
        // This tab only loads the review. Do not click any lifecycle or BO3 command.
        expect(input.championship_checks.state).toBe('incomplete');
        await page.getByRole('tab', { name: 'Zona de riesgo', exact: true }).click();
        await expect(page.getByRole('heading', { name: 'Campeonato de Liga', exact: true })).toBeVisible();
        await expect(page.getByText('Liga pendiente de completar', { exact: true })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Finalizar Liga', exact: true })).toHaveCount(0);
        await expect(page.getByRole('button', { name: 'Registrar ganador del desempate', exact: true })).toHaveCount(0);
        await expect.poll(() => pending.size).toBe(0);
        await expect(page.getByRole('alert')).toHaveCount(0);
        await page.screenshot({ path: join(input.output, 'public-championship-'+viewport.width+'.png'), fullPage: true });
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
      screens.push(step);
    }
    await page.screenshot({ path: join(input.output, 'public-readonly-'+viewport.width+'.png'), fullPage: true });
  }
  expect(errors).toEqual([]);
  expect(unexpected).toEqual([]);
  expect(reads.filter(r => r.status >= 400)).toEqual([]);
  expect(reads.some(r => r.path.startsWith('/v1/admin/') && r.status === 200)).toBe(true);
  if (input.championship_checks)
    expect(reads.some(r => r.path === `/v1/admin/seasons/${input.championship_checks.season_id}/championship` && r.method === 'GET' && r.status === 200)).toBe(true);
  if (input.wipe_checks)
    expect(reads.some(r => r.path === `/v1/seasons/${input.wipe_checks.season_id}/wipe-revivals` && r.method === 'GET' && r.status === 200)).toBe(true);
  const menu = page.getByRole('button', { name: 'Abrir navegación' });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).waitFor();
  expect(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0)).toBe(true);
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status: 'PASS', api_interception: false, business_writes: 0, screens, reads, errors, unexpected, environmentOrigins }, null, 2));
  console.log('PASS owner real public reads: eleven screens desktop/mobile, admin championship review, logout, zero business writes; local antivirus origin recorded separately');
} catch (e) {
  await writeFile(join(input.output, 'browser-result.json'), JSON.stringify({ status: 'FAIL', step, message: String(e.message).replaceAll(input.pin, '[REDACTED]'), screens, reads, errors, unexpected, environmentOrigins }, null, 2));
  throw new Error('Public read-only validation failed; credentials suppressed');
} finally {
  await context.close();
  await browser.close();
}
