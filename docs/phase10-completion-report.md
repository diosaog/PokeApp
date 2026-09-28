# Phase 10 delivery report — React / Cloudflare

Observed 2026-09-28. **IN PROGRESS: local delivery validated and published;
public deployment blocked by missing Cloudflare authentication and backend URL.**
This is not a Phase 10 closure or a live authenticated staging PASS.
Current operational record: [live handoff](work-in-progress/phase10-live-handoff.md).
[Contract](phase10-react-cloudflare.md), [durable evidence](phase10-validation-evidence.json),
[run/deploy instructions](../web/README.md).

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

## Validation evidence and limits

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

## Cloudflare / backend / database

Workers static assets config provides
[SPA navigation](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/).
Build-generated [headers](https://developers.cloudflare.com/workers/static-assets/headers/)
include a CSP constrained to the configured API origin. Missing/invalid
build URLs fail; the deployment command rejects a localhost build. No temporary
account, domain, public URL or live backend was invented.

`wrangler whoami`: **not authenticated**. No public deployment took place.
No existing Railway deployment was found. API origin remains hosting-independent;
`/health` remains liveness only. The owner was asked for the intended public API
URL and Cloudflare account/domain while local work continued; no answer is recorded.

Pinned project verified for read-only preflight:
`https://uwleqeuzsveqlugugzba.supabase.co`. Final schema selections, including numeric
casts, were accepted. Observed lists: zero seasons, zero Hall entries, ten public
trainers. **No fixture, mutation, migration or Storage operation** occurred.
No fresh Advisor/cleanup run is claimed because no DB security/schema/data change
was performed. Historical 031=`20260928110301`, 032=`20260928111840` remain the closed
8L records; do not reapply. Migrations 001–032 are unchanged; no 033.

## Publication and next action

- `512d239`: safe reads/CORS, initial contract and continuity index; pushed.
- `c940b33`: React features, generated contracts, tests and Cloudflare boundary; pushed.
- `7a827ee`: admin recovery and exact numeric transport; pushed.
- Documentation/evidence closure: the commit containing this finalized report.

Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` remains untracked,
unread and untouched (metadata still 72,079 bytes / 2026-09-22 10:13:27 UTC).
No secrets or ignored build/browser artifacts were staged.
Local validation servers were stopped; ports 8787/5173 have no listeners and no
workspace web Node/Workers/browser process remains.

Weighted estimate **~73% → ~79%** for the delivered React/API work, with no credit
for a public deployment or cutover. Phase 10 remains IN PROGRESS. Next: configure
the owner-selected backend/origins and Cloudflare account, rebuild/deploy, and verify
real authenticated flows in that environment. Follow the master staging procedure
if fixtures are required; current read-only evidence does not authorize bypassing
baseline/cleanup checks. Do not restart Phase 9/8L or begin Phase 11 automatically.
