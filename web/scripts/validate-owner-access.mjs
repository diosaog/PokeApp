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
