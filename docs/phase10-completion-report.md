# Phase 10 delivery report - React / public Cloudflare + Railway

Validated 2026-09-28 UTC; documentation closed 2026-09-29 Europe/Madrid.
**DONE: public React/FastAPI, real authenticated gates, owner admin, independent
cleanup and Git publication.** The earlier missing-account/API
blocker is resolved. Current operational record:
[live handoff](work-in-progress/phase10-live-handoff.md).
[Contract](phase10-react-cloudflare.md), [local evidence](phase10-validation-evidence.json),
[public evidence](phase10-public-evidence.json),
[web runbook](../web/README.md), [backend runbook](../deploy/README.md).

## Entry and inherited result

Entry `ee7ff53e443e89819051432021a3a544056a250b`, main/origin 0/0, tracked clean;
only the protected guide untracked. Phase 9 DONE verified against 25 source hashes,
its report, evidence and Git. No repair needed. Its 543 Python tests, 24 .NET
assertions and six binary/Launcher integration groups are historical evidence at
`f2158ed`; no separate .NET rerun was needed. No pending parser process found.
The new full Python regression includes the existing Phase 9 unit tests.

Reuse: FastAPI auth, mutations, public projections and frozen competition facts.
Reference: Streamlit and ignored Electron experiment. New: React, typed reads,
CORS and Workers assets. No existing React/Cloudflare/Railway configuration was
found to replace. V1 remains the running legacy/fallback; no cutover.

## Delivered implementation

React 19.3, Vite 8.3, TypeScript 5.9.3, Router 7, TanStack Query 5, Lucide and exact
lockfile under `web/`. OpenAPI types are generated from this checkout's FastAPI.
Feature components share forms, accessible native dialogs, feedback and request
handling. Dark styling uses section accents, mobile navigation, keyboard focus,
reduced motion and responsive grids/tables. Assets are local; final sprites/audio
and release polish are not claimed.

Auth uses the existing PIN bridge, verified JWT and `/v1/me`. Tokens stay in memory;
refresh requests coalesce and logout clears private queries. API mutations preserve
idempotency and CAS. Unknown-outcome retries keep the original body/key, including
route changes within the same session; concurrent identical submissions coalesce.
No automatic retry of a 409 mutation. A browser reload loses in-memory pending
intents: inspect history before starting another operation after an uncertain result.

| Screen | Connected behavior |
|---|---|
| Home | Current day/opponent, Team Lock, own wallet, current division, save availability |
| League | Official per-day positions/podium/divisions, matches, accumulated sanctioned points |
| Battle / Team Preview | Frozen public teams/moves and own server-validated Team Lock |
| Trainers | Season participation and recorded badge counts |
| Private PC | Current parsed save, party/boxes, search and in-app Pokemon detail dialog |
| Shop | Catalog/promotions, confirmed purchases, owned purchases/gifts, supported redemption |
| Hall | League/Cup entries, nullable trainer IDs, both doubles members, exact Cup link |
| Cup | Create/setup/start, modern formats, rounds/results/Bo3, correction, DQ, cancel, certify |
| Trials | Proposal/edit/cancel, explicit Discord verdict, typed sanctions, history/correction |
| Admin | Summary; configuration/create/replace-unused; participants; divisions/day commands; history links; lifecycle risk area |
| Saves | Actual backend save state and honest local Launcher availability |

The Launcher screen does not invent a heartbeat, remote sync, installer or physical
write. Revival/theft can be recorded by the existing server; physical effects stay
pending. No new save ingestion, CaptureOrder or identity assignment was added.

Seven new enabled-JWT read endpoints live under `/v1/read`: seasons, trainers,
season overview, own PC, shop, own inventory/targets and Hall. Service/repository
composition whitelists nested DTOs. Private save reads derive owner from verified
identity and constrain season, save, deletion state and parser version. No storage
keys, raw identity evidence, arbitrary metadata or private rival details leave them.
List pages paginate; complete competition reads fail rather than truncate above
500 rows. Unsupported legacy PC payloads and snapshot schemas are explicit failures.

Inventory identities come from recorded, unambiguous observations. Rival selection
shows only already-public frozen Team Locks, never rival private boxes; the server
rechecks current identity, ownership, sanctions and eligibility when redeeming.
This is a limited visible target set, not a claim that private rival PC browsing
has been implemented or approved. Gift-only items remain absent from sale offers.

League integration was corrected during validation: historical snapshot `score`
is not accumulated net points. The UI displays per-day awarded points and reads
`public_sanctioned_points` from 030 for official cumulative values. Numeric columns
are requested as text and returned as Decimal strings, preserving large exact
sanctions; React performs no ranking/sanction recomputation. PostgREST
[column casts](https://docs.postgrest.org/en/v12/references/api/tables_views.html#casting-columns)
were checked against the actual V2 schema.

CORS uses `POKEAPP_API_CORS_ORIGINS`: exact HTTPS origins, HTTP only locally,
explicit Authorization/Content-Type/Idempotency-Key headers, no wildcard credentials.
All `/v1/` responses include `Cache-Control: no-store`. Backend privileges remain
server-enforced; hiding an admin link is not authorization.

## Historical local validation and limits

| Gate | Result / provenance |
|---|---|
| Complete Python suite | **565 PASS**, exit 0, source `c940b33` |
| Final focused reads/CORS/transport | **22 PASS**, exit 0, `7a827ee`; includes exact-decimal follow-up |
| React transport/component | **11 PASS**, exit 0, `c940b33`; tested subjects unchanged in follow-up |
| Browser suite | **8 PASS**, exit 0, `7a827ee`, isolated Edge 154.0.4258.37 |
| TypeScript + production Vite build | PASS, `7a827ee`; JS gzip 112.88 kB, CSS gzip 6.30 kB |
| Workers dry run and actual local asset runtime | PASS; deep SPA `/pc` HTTP 200 plus configured security headers |
| New Python lint / compile | PASS; compile covers app/tools/tests |
| Prettier / diff checks | PASS |
| Production npm audit | Zero reported vulnerabilities at observation |
| Pinned V2 read-only contract check | **24 selections PASS**, typed seasons/Hall/trainers reads PASS |

Full Python log: `%TEMP%/phase10-python-unit-final.log`; read-only result:
`%TEMP%/phase10-read-contract.json`. Browser outputs: ignored
`web/test-results/` and `web/playwright-report/`. Durable evidence retains commands,
source commits, normalized source hashes and the essential summaries.

Browser tests run the real React application, including the production build served
by local Workers assets. API responses are intercepted synthetic fixtures. They
prove client rendering/request behavior, **not a real JWT-to-PostgREST tournament**.
Flows cover login/logout, League, Team Lock, private dialog, purchase/conflict,
admin CAS/config replacement/cancel editing, Cup Bo3, doubles Hall, redemption and
manual judicial decimal sanctions. There is no skip or hidden failing test.

Responsive coverage visits eleven screens at 1440×1000, 1280×800, 768×1024 and
390×844, checking page errors and horizontal overflow. Representative captures were
visually inspected. Fixes included label/select association, route focus scrolling,
hidden mobile navigation focusability, modal Escape handling and stretched empty
Battle cards. Four synthetic captures are retained:
[desktop](evidence/phase10/desktop-home.png), [laptop](evidence/phase10/laptop-battle.png),
[tablet](evidence/phase10/tablet-league.png), [mobile](evidence/phase10/mobile-hall.png).

Other resolved setup failures: TypeScript 7 conflicted with the OpenAPI generator's
peer range, so 5.9.3 was pinned; Node tooling types were added for Vite config.
The Browser skill found no available integrated browser; Chromium CDN downloads
timed out. The Playwright suite used installed Edge in fresh isolated contexts.

## Public infrastructure and deployed source

Railway project **PokeApp V2** `f5c4666a-508f-4e5a-8aae-a54581814f29`, service
**pokeapp-api** `9a78e086-c927-471f-8bb9-befe62c77de7`, environment
`production` `d05ccec3-7a85-4eeb-9b01-c0f8d2111896`. That is Railway's default label;
the database remains isolated V2 staging. Existing URL:
https://pokeapp-api-production.up.railway.app.
Deployment `03e8c858-e036-44b9-8b46-ee659db175f1`, source `6d2c66a`, SUCCESS/RUNNING.
Docker starts `python -m app.api.serve`, non-root user 10001, one Uvicorn process/
replica on port 8000. Required config fails closed. Secrets remain server-side.
The committed-source bundle excludes docs, protected/untracked files, saves,
credentials, local builds and tests. No migration runs at build/start.

Cloudflare account `a8e089ff4da821ed3dbd24701437514c`, Worker **pokeapp-web**:
https://pokeapp-web.pokeapp-v2.workers.dev.
Final version `06479b87-7adb-4965-a5d8-b1d07ef783c1`, deployment
`6f6cb9d6-cb0c-4fa1-82f6-92f69222c8b1`, 100%, source `3c83a16`.
Initial public version `c3ce7902-8c42-4301-b27e-829d7f507e53` was superseded only to
fix long unbroken names; the backend did not change or redeploy.
Final build: JS gzip 112.90 kB, CSS gzip 6.31 kB. Served asset SHA256 equals the
local final build; production API URL, deep SPA route, MIME/CSP/security headers
and exact allowed/rejected CORS PASS. No wildcard credentials. `/health` proves
liveness; real JWT/API/PostgREST flows below establish usability.

Anon/service keys and PIN pepper are absent from served JS/CSS. No configured
loopback API endpoint exists. Two inert `http://localhost` URL-parsing bases from
React Router remain in vendor code; they are not API targets. Browser verification
checks actual request origins. Railway's PIN limiter stays single-process/in-memory;
shared throttling is required before adding replicas. Runtime direct dependencies
are pinned; the deployed image digest is retained, not a claim of a fully locked
transitive Python dependency graph.

## Persistent owner access - staging only

**OWNER_TEMP_STAGING_AUTH / OWNER_TEMP_STAGING_ADMIN**. Unique enabled Anto:
trainer `507d9c56-04d8-4801-a9da-f1e53674efb5`, Auth
`ac98932c-f713-43d1-8b20-600f0be3dadc`. The supported PIN provisioner mapped the
existing trainer; no duplicate trainer/Auth identity. The same requested temporary
PIN remains usable and is absent from repository docs/evidence.

On explicit owner authorization, a privileged, scope-checked update set the existing
`trainers.is_admin` field true. This is the authority read by JWT principal lookup,
`require_admin_principal`, SQL `admin_setup_principal` and existing RLS helpers.
No name-based rule, client authority, production default or role migration was added.
Public login/JWT/refresh, `/v1/me is_admin=true`, admin read, create/rename of a
disposable empty draft and six actual React admin areas PASS. Initial non-admin
request returned `ADMIN_REQUIRED`. Other trainer fields/identities unchanged except
Anto's `is_admin` and audit timestamp; the draft fixture was removed and all 52
baseline tables compared. Existing open React sessions need logout/login to refresh
cached role presentation; backend checks the mapped row on every request.

**TEMP_STAGING_AUTH_MUST_BE_REMOVED_OR_RESET_BEFORE_RELEASE**: reset/remove this
temporary credential, review/revoke the temporary staging role and establish
individual secure onboarding/definitive roles before release. Keep access usable
for current owner review; it is explicitly not fixture residue or a Phase 10 blocker.

## Public validation, failures and scope of evidence

The original 565-test Python suite also passed at `0095dac` (exit 0, 30.247 s).
Its subjects are unchanged since; no repeated backend gate was needed for CSS or
harness-only fixes. Final browser suite at `3c83a16`: **9 PASS**, exit 0, 25.6 s;
11 regular screens/four breakpoints plus long-name desktop/mobile regression.
The regression failed before the one-line wrapping fix and passed after it.
TypeScript/production build, formatting and Workers dry run/deploy PASS.

Real public fixture runs use Cloudflare React -> Railway FastAPI -> pinned V2;
no intercepted API and no TestClient. The successful individual gates in runs 4/5
cover four PIN/JWT/refresh identities, wrong PIN/disabled/mismatched identity denial,
real admin setup/activation, idempotent replay/stale-body 409, four Team Locks,
results/close/frozen history, typed overview/shop/inventory/private PC isolation,
doubles Bo3/certification/Hall and judicial proposal. Real browser responses also
confirm Team Lock, purchase, Cup results and judicial resolve HTTP 200; dialogs
complete and show success. The separate owner-admin run is PASS.

Do not relabel failed complete runners as PASS. All attempts are retained:

| Attempt | Stop reason | Resolution / state |
|---|---|---|
| 1 | Day close lacked fixture identity revisions | Fixture uses existing identity reconciliation |
| 2 | Rename attempted after activation | Check moved to draft window |
| 3 | Identical rename replay returned correct 200 | Stale conflict now uses a different body |
| 4 | Global network-idle timeout | Wait for application reads/loading; local antivirus long polling identified |
| 5 | Long unbroken fixture name overflow on Inicio | One-line CSS wrap, red/green regression, frontend-only redeploy |
| 6 | Owner had created an active season | Guard refused before creating fixtures; owner seasons preserved |

All six attempts restored their fresh 52-table baseline and preserved migration
history, with zero ERROR/WARN delta against their immediate Advisor baseline.
The final attempt is an expected safety stop, not a product defect. The all-in-one
runner's trailing direct purchase/judicial readback was not reached; public successful
mutation receipts and earlier integrated backend tests are the mutation evidence.
Completion is assessed from complementary gates, not a fictitious single green run.

The final read-only browser check uses the existing owner's season and preserves
all manual data. It covers all eleven screens at desktop/mobile with real API
responses, admin visibility/reads and logout. The first read-only attempt passed
all 22 screen checks but failed a blanket external-origin assertion: installed
Kaspersky injects its own script/long polling. Raw served assets and app source
contain no such script. The validator records that exact environment origin
separately without disabling protection, intercepting API or accepting other origins.
Final read-only result at `023442f`: **PASS**, 22 screen/viewport visits,
zero API/page errors, no business writes, logout with no persisted credentials.
Independent final SQL: **52/52 tables equal**, zero public fixture-prefix residue,
24 unchanged migration records, Anto admin mapping still valid. Final screenshots
were inspected: [desktop](evidence/phase10/public-desktop-saves.png) and
[mobile](evidence/phase10/public-mobile-saves.png).

## Database, cleanup and security

Pinned V2 `uwleqeuzsveqlugugzba`. All 24 migration records preserved;
031=`20260928110301`, 032=`20260928111840`. **Do not replay either.**
Migrations 001-032 unchanged; no 033, remote bootstrap/reset, V1 mutation or cutover.

Baselines compare counts plus ordered full-row content hashes for all 52 tables:
46 public, Auth users/identities/sessions/refresh_tokens, Storage objects/buckets.
All public rows include Anto's role and all owner-created seasons. Only the explicit
owner Auth row/identity/session/refresh activity is excluded from later comparisons;
fixture identities are still compared/deleted and deletion checked independently.
No Storage bytes are touched. Preserve the owner's manual seasons, including the
active one: do not rerun the activating fixture suite while it exists.

Combined Advisor final baseline: **24 ERROR / 5 WARN / 122 INFO**. Zero new findings
against immediate baselines. The original pre-owner inventory had four warnings;
the added observed `auth_leaked_password_protection` is the previously documented
intermittent Auth configuration warning, now present with owner access. No Auth
setting changed; do not claim it fixed or pretend initial/final totals are identical.
The [durable final inventory](phase10-public-security-advisor.json) retains finding/
object/severity. The other four warnings and 24 security-definer-view errors are inherited. No new
schema, grants, RPC privilege or RLS change occurred during public delivery.

## Publication, limits and next step

Implementation/publication commits: `512d239`, `c940b33`, `7a827ee` (React/API),
`6d2c66a` (hosting), `18b93f4`, `0095dac`, `f74d445`, `6c60d99`, `7d68de2`
(hosted harness/owner evidence), `3c83a16` (long-name fix), `8eb89fa`, `023442f`
(read-only final validation and antivirus classification). All pushed before their
respective deployments/runs. Final documentation/evidence uses its own commit.

Raw local evidence: `%TEMP%/phase10-hosted-run1` through `run6`,
`%TEMP%/phase10-owner-access`, `%TEMP%/phase10-owner-admin`,
`%TEMP%/phase10-public-readonly` and `phase10-public-readonly-final`,
`%TEMP%/phase10-hosting-final.json`, `%TEMP%/phase10-public-unit-final.log`.
No token, credential or PIN is retained in durable repository evidence.

Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` is unread/untouched/
untracked; metadata remains 72,079 bytes / 2026-09-22 10:13:27 UTC. It is never staged.
Remaining product limits: memory-only sessions/pending intents, no cloud ingestion,
physical save writes, installer/auto-update, final polish/audio or V1 migration.
Phase 11 is the next planned work and is **not started**.

Final state: all validation processes finished; no pending fixture mutation or
local validation server. Main is committed/pushed with no tracked changes; the
protected guide remains the only untracked exception. Obtain the documentation
closure hash from Git rather than maintaining a self-referential commit ID.
Weighted complete-project estimate: **~79% -> ~80%** for verified public delivery
and integration. No credit for V1 cutover, future Launcher/physical operations or
release readiness. **Phase 10 DONE; Phase 11 not started.**

During final Git verification, the local loose `origin/main` tracking ref contained
41 NUL bytes and normal fetch failed. GitHub's branch and local HEAD were separately
verified at `cf99390`. The damaged tracking file was preserved in `%TEMP%`, then
normal fetch rebuilt it; divergence returned 0/0. No branch/history rewrite, force
push, source reset or protected-file access. Cause of local ref corruption unknown.
