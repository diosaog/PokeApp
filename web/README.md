# PokeApp web

React consumes FastAPI. It never connects directly to Supabase. Streamlit/V1 stays
available; this frontend does not perform a cutover or any physical save write.

Use Node 24 LTS (minimum 22.12), npm and the committed lockfile:

```powershell
cd web
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The only browser variable is `VITE_API_BASE_URL`. Use the API's public HTTPS URL
for a hosted environment. HTTP is accepted only for localhost validation. Vite
reads `.env.local`, `.env.staging.local` / `.env.production.local` and process env.
Never put Supabase service keys, PIN peppers or database credentials in a `VITE_`
variable. Access and refresh tokens remain in memory; refreshing the browser
requires login again. Logout clears private query state.

For local FastAPI, configure its existing V2 backend variables privately and add
`POKEAPP_API_CORS_ORIGINS=http://127.0.0.1:5173,http://127.0.0.1:8787`.
For hosting, list exact frontend HTTPS origins separated by commas. No wildcard,
paths or trailing slash. Run FastAPI using the established API environment:

```powershell
# Repository root, with the backend environment already configured
.venv-api\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

The frontend does not create Auth users. Use an already provisioned trainer/PIN.
`/health` is liveness only. Validate real login, `/v1/me`, reads and preflight before
treating any hosting environment as ready. Railway-specific code is unnecessary;
there was no existing Railway deployment configuration at Phase 10 entry.

## Checks

```powershell
npm run test
npm run test:e2e
npm run format:check
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
npm run build
npm run deploy:check
npx wrangler dev --ip 127.0.0.1 --port 8787 --local
```

Browser tests use an isolated Edge context on Windows and Chromium elsewhere
(`npx playwright install chromium`). Override with `POKEAPP_TEST_BROWSER` if needed.
Synthetic API interception exists only under `e2e/`, not in the application.
Screenshots and traces go to ignored `test-results/`. To repeat the same browser
suite against the actual Workers local runtime, start the last command above and
set `POKEAPP_E2E_BASE_URL=http://127.0.0.1:8787` before `npm run test:e2e`.

Regenerate checked-in API types after backend contract changes, from repo root:
`.venv-api\Scripts\python.exe -m tools.export_web_schema`.
The generated types are formatted by that command. Frontend DTO aliases import
these types, and server projections whitelist every field.

## Distribution

Build refuses a missing/invalid API URL. `npm run deploy` also refuses a localhost
build; use a real HTTPS backend and rebuild first. `wrangler.jsonc` uses Workers
static assets and SPA fallback. The build generates a CSP limited to the configured
API origin plus security headers, and `build-config.json` with public configuration.
No backend secret is an asset. Source maps are not published.
Hosted backend configuration and committed-source upload instructions are in the
[deployment runbook](../deploy/README.md). Live status and evidence are in the
[closed Phase 10 handoff](../docs/work-in-progress/phase10-live-handoff.md).
Active alignment work and pending deployment order are recorded in the
[Phase 10.5 handoff](../docs/work-in-progress/phase10-5-live-handoff.md).
The new GENERAL screen requires migration 033 and the matching FastAPI source
before frontend deployment; its local validation is not a public deployment.

The verified frontend is `https://pokeapp-web.pokeapp-v2.workers.dev`; its backend
is `https://pokeapp-api-production.up.railway.app`. Reuse the pinned account and
existing Worker. Deploy from a committed/pushed checkout:

```powershell
$env:VITE_API_BASE_URL='https://pokeapp-api-production.up.railway.app'
npm run build
npm run deploy:check
npm run deploy
```

After deploy, verify direct navigation to `/pc` and `/copa/<actual-id>`, asset MIME
types/security headers, login/refresh/logout, actual CORS and private data access.
Never call a dry run or intercepted browser fixture a real staging/deployment PASS.
Official references: [SPA routing](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/)
and [headers](https://developers.cloudflare.com/workers/static-assets/headers/).

Anto has explicitly authorized temporary staging access for manual inspection.
Its credential is not documented here. Keep it usable until the owner's review;
**TEMP_STAGING_AUTH_MUST_BE_REMOVED_OR_RESET_BEFORE_RELEASE**. It is not a
universal/default credential and must not be copied into future onboarding.
The same owner identity now has the explicitly authorized temporary staging admin
role through `trainers.is_admin`; backend authorization and the six React admin
areas have been verified. Review/revoke that temporary role when resolving the
release blocker. Re-login refreshes the role in an already open browser session.

The opt-in real hosted validator is `tools.validate_phase10_hosted`, with
`--allow-staging-writes`, a new evidence directory and the explicit owner Auth
exception. It reads the deployed PIN pepper privately from its process environment,
never from a command argument. Preserve the owner exception; all fixture Auth and
public rows must return to their fresh baseline. This test runs the actual public
web/API without request interception. Never run it over another active fixture run.
It also refuses when an owner-created active season exists; preserve that guard
and all manual data. To finish read/render checks in that situation, use
`scripts/validate-public-readonly.mjs` from `web`, passing the actual web/API URLs,
owner identifier, PIN, trainer ID and a fresh output directory through private
stdin JSON. It performs no business writes and visits eleven screens on desktop
and mobile. Surround it with fresh full-state/history/Advisor comparisons using
the helper functions in `tools.validate_phase10_hosted`. Never put credentials in
command arguments, logs or checked-in files. The known local antivirus injection
origin is recorded separately; API traffic is never intercepted or simulated.

## Known product boundaries

- PC accepts the neutral slotted schema; unsupported legacy payloads are explicit.
- Canje uses recorded, unambiguous entity observations. Rival selection exposes
  only existing public Team Locks; private rival boxes are not disclosed. Server
  checks final eligibility/current identity and may reject stale targets.
- Revival/theft physical effects remain pending. Launcher 9 has no remote heartbeat,
  cloud ingestion or public installer, so the Saves page does not simulate them.
- Official League results come from V2 closed snapshots, not a browser ranking.
- Whole-competition reads fail explicitly above 500 records; list pages paginate.
- Initial administration, results/corrections, lifecycle and judicial decisions
  use existing commands. No SQL/migrations or replacement business engine.
