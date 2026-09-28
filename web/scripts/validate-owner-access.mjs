// Explicit owner staging check. Credentials arrive over stdin, never in artifacts.
import { chromium } from '@playwright/test';
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const data = JSON.parse(Buffer.concat(chunks).toString('utf8'));
if (data.web !== 'https://pokeapp-web.pokeapp-v2.workers.dev') throw new Error('Wrong owner target');
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
const context = await browser.newContext();
const page = await context.newPage();
try {
  await page.goto(data.web);
  await page.getByLabel('Entrenador', { exact: true }).fill(data.identifier);
  await page.getByLabel('PIN', { exact: true }).fill(data.pin);
  const me = page.waitForResponse(r => r.url() === data.api+'/v1/me' && r.status() === 200);
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).click();
  const identity = await (await me).json();
  if (identity.trainer_id !== data.trainer_id) throw new Error('Owner mapping mismatch');
  if (data.require_admin) {
    if (identity.is_admin !== true) throw new Error('Owner admin authority missing');
    const setup = data.season_id ? page.waitForResponse(r =>
      r.url() === data.api+'/v1/admin/seasons/'+data.season_id+'/setup' && r.status() === 200) : null;
    await page.getByRole('navigation').getByRole('link', { name: 'Administración', exact: true }).click();
    await page.getByRole('heading', { name: 'El control, en su sitio.' }).waitFor();
    await page.getByRole('button', { name: 'Crear temporada', exact: true }).waitFor();
    if (setup && (await (await setup).json()).season.id !== data.season_id) throw new Error('Admin read scope mismatch');
    if (await page.getByRole('tab').count() !== 6) throw new Error('Missing admin areas');
    console.log('PASS owner real backend admin authority, admin read and six React admin areas');
  }
  await page.getByRole('button', { name: 'Cerrar sesión' }).waitFor();
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.getByRole('button', { name: 'Entrar a PokeApp' }).waitFor();
  if (!await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0)) throw new Error('Unexpected persisted credentials');
  console.log('PASS owner real React login, verified trainer identity and logout');
} catch {
  throw new Error('Owner browser validation failed; credentials suppressed');
} finally {
  await context.close();
  await browser.close();
}
