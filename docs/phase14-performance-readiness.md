# Phase 14 preparation - performance execution map

2026-10-11. **STATUS: PHASE 14 PREP DONE. PHASE 14: NOT STARTED.**
Preparation only: source inspection and documentation; no benchmark, product
change, test suite, database operation, migration, deployment or cutover.

## 1. Verified entry and evidence limits

Entry `48294f8a9efb249413ff70b37eb8ee216115099b`, `main`, fetched origin 0/0,
clean tracked tree. Phase 13 DONE verified from [report](phase13-staging-report.md)
and [handoff](work-in-progress/phase13-live-handoff.md). Its isolated database and
servers were removed/stopped. Unrelated untracked files and protected guide are
untouched. This preparation follows the repository's committed/pushed continuity
documentation convention; its documentation commit follows the entry above.

Retained Phase 13 remote evidence, **not reobserved here**: Railway source
`cea57ca5d6e25c7b073aa2dd8857152730f1a157`, deployment
`3845ce2d-6488-43ef-893a-1459c2aed0bb`; Cloudflare source `eb4e402`, deployment
`ea9c837d-86f0-4b0a-826d-a4774371b56e`; 34 migrations through 042 once.
Reconcile these briefly at actual Phase 14 entry; do not reopen Phase 13.

[M candidates, final-alignment follow-up](phase10-5m-performance-candidates.md)
reported single hosted samples: overview 5.050 s, empty inventory 2.507 s,
Shop 1.955 s, scouting 1.680 s, General 0.898 s. Earlier M three-sample medians
were overview 3.616 s and inventory 1.826 s. These justify measurement priority,
not current latency claims, populated-inventory evidence or a diagnosed cause.

## 2. Exact hotspot map

Path abbreviations below are exact current files:

- `core` = `web/src/features/core.tsx`; `state` = `web/src/state.tsx`.
- `FR` = `app/application/frontend_reads.py::FrontendReads`.
- `RR` = `app/repositories/supabase/frontend_reads.py::SupabaseFrontendReadRepository`.
- `reads` = `app/api/routes/reads.py`; frontend read base `B=/v1/read/seasons/{sid}`.
- `invalidate` = `web/src/read-invalidation.ts::{affectedRead,invalidationFor}`,
  called by `web/src/ui.tsx::useCommand` after success or definitive 409.

Counts below are **static business transport calls**, not measured durations or
SQL statements inside RPCs. They exclude retries, auth and shell reads. Every
authenticated hosted request first runs
`app/api/security.py::require_principal`: `SupabaseAuthClient.get_user`
(`app/auth/supabase_adapter.py`, remote Auth verification), then
`SupabaseTrainerAuthRepository.find_by_auth_user_id/_find_one`
(`app/api/supabase_repository.py`, trainer SELECT). Instrument both separately;
do not remove verification or cache roles to meet a budget.

| Surface / frontend and hooks | API -> application -> transport | Count, dependency and affected experience |
| --- | --- | --- |
| `/entrenadores`: `core::TrainersPage/OverviewState`, `state::useOverview`; `/liga` day: `core::LeagueDay`; `/`: `core::HomePage` also calls `usePC` | `GET B/overview` -> `reads.overview/read` -> `FR.overview` -> `RR.rows` + `RR.observed_progress` | One browser overview GET; **12 row reads + 1 RPC** for a participant, sequential. Reads season, global names, roster, progress, full historical snapshot JSON, points, days, matches, divisions, memberships, season-wide public locks, membership/wallet. No application per-player loop, but payload grows with days/roster. Blocks `OverviewState` content on cold and stale navigation; relevant mutations refetch it. Home additionally fetches the full own PC. |
| `/entrenadores/:trainerId`: `web/src/features/trainer-profile.tsx::Profile` | `useOverview` + `useRead(B/league)` + **one** of `B/scouting?trainer_id=...` / `B/team-preview?mode=battle&trainer_id=...` | Three parallel browser GETs; **13 + 1 + 5 public / 6 own** business calls with current day. Profile gates on overview even when narrower stats/team finish first. Shared overview/league keys can reuse cache from prior pages. Cold, stale warm and refresh. |
| `/tienda`, embedded `web/src/features/inventory.tsx::Inventory`, `useRead(B/inventory)` | `reads.inventory/read` -> `FR.inventory -> pc, observed_entities`; `RR.rows`, `RR.shield_targets` -> `inventory_shield_targets` | Eager PC/eligibility/rival targets before purchases are known. Season is read twice (outer + `pc`). Each rival lock invokes one observations SELECT and another owner-filtered entities SELECT if observations exist: **N+1 confirmed**. Typical ready own save/current day/purchases: **11 + up to 2R** calls for R rival locks. Empty inventory can still pay this cost. Cold/warm-stale/refresh, even with redemption closed. |
| `/tienda`: `core::ShopPage`, `useRead(B/shop)`; Inventory mounts independently | `reads.shop/read` -> `FR.shop/season/balance` -> season, `public_shop_promotions`, `public_shop_items`, membership, `public_coin_balances` | **5 serial** business calls for active participant; Shop + Inventory browser GETs are parallel, not a frontend waterfall. Four category tabs are local filters. Names `/v1/read/trainers` are **already lazy**, one cached read only when redemption opens. Economic `invalidate` + explicit extras refresh dependent season reads. |
| `/battle`: `web/src/features/team-preview.tsx::Preview`; `/entrenadores/scouting`: `web/src/features/scouting.tsx::Scouting` | `reads.preview/public_scouting` -> `app/application/team_preview.py::team_preview`; `app/application/scouting.py::scouting` delegates with `single_public=True`; `RR.rows` | One GET per uncached selection/mode. **5 serial** calls with current day (season, names, roster, day, all public day locks); own Battle adds **1 private own-lock** read. No per-player loop. Selected-team DTO still fetches all public locks. Lock modal `LockConfirmation` adds `usePC` lazily. Team-lock invalidation covers preview/scouting/overview/setup. |
| `/admin`: `web/src/features/admin.tsx::AdminPage`, `useAdminCommand`, tab components | Setup -> `app/api/routes/season_admin.py::get_setup/_execute` -> `app/repositories/supabase/season_admin.py::execute` -> `api_admin_get_setup`; Rules -> same route/repo, `api_admin_live_rules_read` | Summary: **1 GET / 1 RPC**. Setup must finish before tab child mounts. Config adds rules GET; Participants adds names + overview; Competition adds overview + selected day and modern initial review; Risk adds championship, **not overview directly**. `DayAdmin` and parent share the same overview key. See tab details below. |

Inventory count formula: `1 outer season + Qpc + 1 shield RPC + D lock query +
sum(1 + E_i) per rival + 1 purchases + P catalog`, where D/P/E are 0 or 1.
`FR.pc` is 2 calls without current save, up to 6 when ready (season, player pointer,
save, parsed payload, observations, owned entities). Own PC returns party/boxes
in one payload. Preserve unknown, exact identity ownership and 501-row fail-closed
guards; batching must not expose rival parsed saves or silently truncate.

Additional exact routes and aggregate boundaries:

- General `GET B/league`: `reads.league_general -> FR.league_general ->
  RR.league_general -> league_general_read` (one RPC; latest definition in
  `supabase/v2/migrations/036_observed_initial_divisions.sql`).
- Progress `GET B/progress`: `reads.progress -> FR.progress ->
  RR.observed_progress -> observed_progress_read`
  (`040_observed_progress_read.sql`). No extra progress GET in trainer cards;
  they render overview's progress. `web/src/features/progress.tsx::MyProgress`
  is mounted on `/saves`.
- Day state `GET /v1/seasons/{sid}/matchdays/{day}`:
  `app/api/routes/matchdays.py::participant_state/execute` ->
  `app/repositories/supabase/matchdays.py::execute` -> `api_participant_matchday`.
  Admin day uses `state/execute` -> `api_admin_matchday` (one RPC each).
- General's `web/src/features/league-operations.tsx::DayOperations` and
  `web/src/features/wipe-revivals.tsx::OwnedWipeRevivals` mount after league data:
  day GET if eligible/open-or-scheduled, wipe GET if roster member. Wipe route
  `app/api/routes/wipe_revivals.py::state/execute` ->
  `app/repositories/supabase/wipe_revivals.py::execute` ->
  `api_participant_wipe_revivals` (one RPC). Current-day
  `league-results.tsx::ParticipantResults` reuses the same participant day key.
- Admin Competition's `web/src/features/initial-assignment.tsx::InitialAssignment`
  adds initial-assignment review; Risk's `championship.tsx::ChampionshipReview`
  adds `/v1/admin/seasons/{sid}/championship`. Championship passes through
  `app/api/routes/season_lifecycle.py::championship/execute` ->
  `app/repositories/supabase/season_lifecycle.py::execute` ->
  `api_admin_championship_read` (latest `041_final_product_alignment.sql`).
  Setup latest definition is in 036, live rules in 041; shield eligibility in 039.
  Existing applied SQL is inspection-only.

Navigation is a separate measurement dimension: `web/src/App.tsx::App` uses static
route imports; `SeasonPicker` needs `/v1/read/seasons?offset=0` before season reads
enable. `ApiClient.login` (`web/src/api/client.ts`) does PIN login then `/v1/me`.
Session is in memory; full reload requires login and is not warm navigation.
`state::useRead` keys by viewer + **full path**, with 15 s stale time and no focus
refetch. Multiple identical mounted observers share a key; do not count them as
duplicate HTTP calls. Default selection URLs and explicit equivalent selections
can differ; measure overlap before canonicalizing, preserving viewer/mode/privacy.
`useCommand` awaits active dependent refetches, so separate mutation response time
from final settled UI. Inactive cache entries may become stale without immediate
network work. API/browser HTTP reads use `no-store`; do not add shared CDN caching.

## 3. Ranked priorities and proposed order

| Rank | Candidate / expected benefit | Smallest evidence-led action | Risk / regression surface |
| --- | --- | --- | --- |
| 1 HIGH | Overview and profiles; current serial calls and broad history gate useful content | Remove redundant consumers/duplicate requests first; then narrow list/profile/day projection or aggregate existing reads if measured dominant | Medium/high: frozen standings, progress provenance, exact totals, lock privacy; Home/Liga/Admin also consume overview |
| 2 HIGH | Inventory eager preparation and rival identity N+1 | Eliminate repeated season lookup; batch authorized identity pairs in bounded calls. Separate on-demand target preparation only if consumer/equivalence evidence supports it | High: ownership/ambiguity, stale eligibility, robbery/revive/shields and uncertain replay; zero queries proportional to rival count is the acceptance target |
| 3 MEDIUM | Shop aggregation, coupled to expensive inventory mount | Measure five calls; reuse safe same-request facts or bounded aggregate after ranks 1/2. Preserve two initial browser reads and lazy names | Medium: exact wallet, offers activating over time, post-League spending; no speculative wallet cache |
| 4 MEDIUM | Scouting/preview selected projection | Measure all-lock payload; narrow selected public rows or aggregate bounded reads | Medium: self Battle versus public Spectator/Admin, pending team and first timing |
| 5 MEDIUM | Admin tab waterfalls and mutation refetch breadth | Measure active refetch set/pending duration; reuse setup facts and remove proven unnecessary extras | Medium: stale rules/roster/confirmations; central invalidation is already implemented, not an open global-invalidation bug |

Low priority: General/progress aggregates, current Shop category/name behavior,
central invalidation itself. Cross-cutting 503 instrumentation comes **before**
optimization measurements, without assuming any hotspot causes failures.
Within the ranked areas: duplicates/serial dependencies -> N+1 -> reuse/aggregate
-> payload breadth -> targeted cache/invalidation -> SQL/index work **only with
plans and measured evidence**. Avoid unbounded parallel HTTP as an N+1 workaround.

## 4. Small benchmark matrix and recording protocol

Run in Phase 14, **not this preparation**. One six-player synthetic active dataset,
known save/lock/purchase facts; one frozen-day checkpoint only when needed. Compare
the identical fixture/actor/state before and after. Existing hosted owner season
is read-only and a sparse reference, not a representative populated workload.

Modes: **C** fresh production-build browser context/deep link; record static app
load, login/me/season time and business-data-to-useful separately. Do not visit
Home first. **W** same-session warm return within 15 s; also one aged (>15 s)
return per surface. **R** repeated authenticated GET with reused HTTP client,
separate from browser cache. **M** one deliberate local synthetic mutation and its
dependent refresh; separate command acknowledgement from fresh visible values.

Start with 3 C samples and 5 W/R samples per row, one M per listed command family;
reuse a single mutation to inspect all its dependent views. Desktop primary;
mobile 390px only Liga/profile/Shop/preview. Report median, range, all failures and
sample count; do not claim meaningful p95 from 3-5 samples. Expand only the slow
or unstable cases to >=20 samples for an explicitly exploratory tail estimate.

| Surface | Useful-content condition; modes C/W/R for each | M / incremental request checks |
| --- | --- | --- |
| General `/liga` GENERAL | Real standings rows and wallet/death states, not just heading; league GET then eligible day + wipe (typically 3 browser reads) | Shared result/wipe mutation: General/profile reflect authoritative values; preserve separate auxiliary-error handling |
| Liga current + one closed J tab | Current results editor or official revision/table; General first, overview on first day tab, day state when editable | Same result update; switching already-loaded J tabs must not redownload all history needlessly |
| Entrenadores | Named roster/progress cards from overview, explicit unknown accepted | Shared progress fixture update or normal dependent mutation; no invented progress |
| Individual own + rival profile | Name/stats plus team/pending state; 3 parallel reads with privacy-specific third endpoint | Same lock/wipe events; evaluate cached list-to-profile versus direct profile |
| Mi PC `/pc` | Own save state and slots or explicit no-save state; 1 GET, up to 6 business calls | Local accepted observation only if optimizing this surface; search/details with loaded data should add zero reads |
| Team Preview `/battle` + scouting | Selected public/own team or explicit pending; 1 GET per uncached selection, lazy PC only in lock modal | One lock replacement; mode/selection cache keys must never mix public and private |
| Shop `/tienda` | Wallet and actual catalog/offer state; parallel shop + inventory | One purchase; wallet/inventory freshness. Four categories add zero reads |
| Inventory within `/tienda` | Purchases and eligible-target modal, not heading; no separate inventory route | Same purchase then one redemption; first modal adds <=1 names GET, cached reopen zero; measure empty vs populated rival-lock branch |
| Admin `/admin` | Setup readiness; then Rules, Participants, Competition and Risk child data | One rules save; measure setup/child waterfalls and active refetches. Summary 1, Config +1, Participants +2, Competition up to +3, Risk +1 business GETs |

Optional controls, not an expanded suite: Home's parallel overview + PC; self
progress endpoint; 1 versus 6 locked rivals/participants in isolated fixtures to
prove inventory call-count slope. Reuse the existing 1/100 mocked read guard for
structural limits; don't create a 100-player hosted league.

For each sample record route, actor class, state/size, build/commit, cache age,
UTC start, click/submit-to-useful time, API GET/mutation/OPTIONS counts, cancellations,
slowest request and timing, encoded transfer and decoded JSON bytes where practical,
duplicates/serial dependency chain, response status, retry attempts and eventual
outcome. Use Playwright request/response/timing/size events (CDP if necessary),
DOM-ready assertions and a no-reload marker; not whole-page `networkidle` or a
heading that renders before data. Resource Timing may hide cross-origin details;
unknown transfer bytes stay unknown. Redact headers/tokens/PINs/body/private PC
from shared traces. Keep API count distinct from assets, preflight and auth.

Backend record: total handling, auth verification, trainer lookup, business
query/RPC count and time, projection/serialization, outbound attempts. SQL plan
time is a separate layer; a PostgREST round trip is not SQL execution time.
Use a production frontend build, not Vite dev/StrictMode, for timing. Local psql
subprocess transport proves structure/equivalence, **not hosted latency**.

## 5. Proposed acceptance budgets (targets, not measured guarantees)

- Cached/current navigation: useful content within **300 ms**, no full-page
  loading replacement or avoidable business GET. Loaded category/detail switches:
  **zero new reads**. Stale revalidation may run while existing content stays visible.
- Authenticated uncached core content: target median **<=2 s**; rich PC/profile/
  inventory **<=3 s**, excluding separately reported login. Investigate repeated
  >4 s samples; no fixed hosted 100 ms guarantee and no hiding auth cost in totals.
- Mutation acknowledgement target **<=2 s**, dependent useful refresh within a
  further **2 s**. Exact correctness, uncertainty and original-key retry take precedence.
- No business round-trip slope proportional to roster/rival lock count; bounded
  payload/queries, zero unexplained duplicate completed requests, zero unrelated
  viewer/season refetch. Preserve existing targeted refresh contracts.
- Final controlled samples: zero unexplained 5xx and zero freshness/privacy
  regressions. Count recovered failures too. On touched flows seek a material
  call/byte/latency reduction; investigate >10% median regression in unchanged
  controls with a focused repeat before accepting or rejecting due to noise.

## 6. Reusable Phase 13 tooling

`tools/phase13_staging.py`: `StagingClient` rejects non-loopback/unrelated DBs;
`SyntheticAuth` exercises signed local JWT/PIN/principal boundaries;
`Staging.prepare`, `observe`, `api`, `rows`, `day`, `results` supply current real
DTOs and HTTP fixtures. `prepare` requires an empty database and builds six
participants, observations and modern J1. `before_browser` adds funded progress
and an on-time lock. Reuse helpers to add the specific rival locks/purchases and
save a baseline checkpoint; do not run the full championship/Cup journey merely
to measure reads. `after-browser`/`finish-journey` have prerequisites and mutate;
`verify` expects the **complete Phase 13** manifest, so is not a generic benchmark
cleanup command. CLI has no benchmark mode today.

The old DB is gone; a new disposable DB is necessary at Phase 14 execution, using
the existing guarded prefix `pokeapp_v2_validation_phase13_` (e.g. suffix
`phase14_perf`), fresh output directory and current bootstrap. No harness redesign
or remote fixture is required. `serve` binds API 8130; CLI accepts `--connect`,
`--psql`, `--database`, `--output`; stop via `<output>/stop-api`. `LocalClient`
in `tools/validate_supabase_v2_identity_sql.py` launches psql for every query.

`web/e2e/phase13-staging.spec.ts`: reuse `login`, `navigate`, `monitor`, real Edge
selectors, desktop/mobile sizes and no-F5 check. It is opt-in via
`POKEAPP_PHASE13_FIXTURE` and loopback `POKEAPP_E2E_BASE_URL`; close/history flags
have state prerequisites. Add a small Phase 14 read-only measuring driver around
these patterns, not a rerun of all seven mutating tests. Production preview can
use port 5173 to preserve the local API's existing CORS origin.

`web/e2e/performance.spec.ts` is a **mocked structural guard**, not a latency
benchmark. `tests/test_api_frontend_reads.py::FrontendReadTests.
test_names_and_overview_have_bounded_repository_round_trips` supplies count
guards. Private Phase 13 evidence/manifest remains under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase13/20261011/`; useful for selectors,
expected outcomes and preservation SQL, not a live fixture or source of production
timing. Do not run `tools/validate_phase10_hosted.py` wholesale: it creates hosted
fixtures and is not the read-only benchmark needed here.

## 7. Narrow hosted 503 investigation

The Phase 13 **close** 503 was a deterministic `SeasonRules` constructor mismatch,
fixed at `cea57ca`; retain `tests/test_api_matchdays.py` regressions. Prior
intermittent **read** 503s on overview/Shop/inventory/General/preview remain
unexplained. `reads.read` maps persistence/projection errors to `READ_UNAVAILABLE`;
auth can fail before that handler. Status alone cannot identify a layer.

Existing diagnostics: `RR` module `_report_failure` logs operation and bounded
exception class, not messages/SQL/rows; `_execute_read` retries **one ReadError**.
`state::queries` retries one API read on >=500; `ApiClient.request` has a separate
401/session-refresh path. Mutations have no automatic 5xx retry. No dedicated
request correlation/Server-Timing layer was found in current API source.

In Phase 14 first correlate UTC, route template, deployment/image/start time,
status/error code, sanitized platform request ID and application/outbound stage
durations. Add minimal structured correlation/timing only where current logs
cannot separate layers; no tokens, SQL, row data or raw exception bodies. Keep
attempt counts and first failure alongside eventual success; do not increase
timeouts/retries or suppress failed samples to obtain a green chart.

| Hypothesis | Discriminating evidence required |
| --- | --- |
| Railway startup/restart | Deploy/start/restart events and process uptime align with slow/failing first requests, health timeline, comparable later successes. `/health` alone proves liveness only. Do not force a production restart to test it. |
| Pool/resource exhaustion | Identify layer first: Python HTTP connection wait/PoolTimeout versus PostgREST/DB connection pressure. Record concurrency, active clients and resource metrics, bounded local 1/2/4-reader comparison. No connection-limit increase without evidence. |
| Supabase/DB latency | Auth versus PostgREST stages, slow RPC/query identity and read-only DB metrics/plans under matching inputs. Use SELECT EXPLAIN only for confirmed read-only statements; no mutation EXPLAIN ANALYZE. |
| Application timeout or CPU | Handling/projection time, threadpool/CPU/memory, effective installed SDK/server timeout configuration and exception class. Current app does not establish a measured timeout cause. |
| Platform/network transient | DNS/connect/TLS/read failure stage, platform request ID/status/body class, presence/absence of app access log, no matching DB slowdown. Do not label every 503 a database problem. |
| Retry masking | Record both backend ReadError attempts, React Query retries and 401 refresh separately; compare first-attempt failure rate and user delay, even when final response is 200. |

No new external monitoring service is required. If occasional 503 cannot be
reproduced, retain evidence and the limit; never claim a causal fix from one clean run.

## 8. Exact execution, likely changes and closure

1. On **new Phase 14 execution authorization**, verify HEAD/status, this map,
   hosting sources and migration head only; retain Phase 13 functional evidence.
2. Prepare the minimal local synthetic read fixture from existing helpers. Add
   opt-in timing capture; establish read-only hosted baseline and the C/W/R matrix.
   Separate auth, business transport and rendering; investigate any first-attempt
   503 before attributing timing differences. No owner positive mutations/load test.
3. Select the first measured bottleneck: unnecessary requests/serial dependence,
   inventory N+1, safe aggregation, payload, cache in that order. One bounded
   change at a time; focused output-equivalence/privacy/freshness/count tests,
   repeat only its invalidated measurements. No speculative rewrite.
4. Likely files: `core.tsx`, `trainer-profile.tsx`, `inventory.tsx`,
   `team-preview.tsx`, `scouting.tsx`, `admin.tsx`, `rules.tsx`; `state.tsx`,
   `read-invalidation.ts`, `ui.tsx` only if measured request/cache issues justify it.
   Backend: `reads.py`, `read_models.py`, `FR`, `RR`, team-preview/scouting services.
   Observability: API middleware/security and safe read-transport instrumentation.
   These are candidates, not permission to alter every listed file. A new forward
   SQL file/bootstrap regeneration is conditional on an actually needed DB change.
5. Focused gates: `test_api_frontend_reads`, `test_frontend_read_recovery`,
   `test_api_team_preview`, `test_api_scouting`, `test_api_league_general`,
   `test_api_final_alignment`, and Admin/mutation tests only when affected.
   React: `web/src/read-invalidation.test.ts`, `command-refresh.test.tsx` and
   affected `features/{economy,team-preview,scouting,admin,admin-recovery}.test.tsx`.
   Browser: `performance.spec.ts`, affected `final-alignment.spec.ts` profile
   assertions and affected real journeys (not their full unrelated matrices).
   Add a call-slope guard and no-unrelated-refetch assertion, not brittle wall-clock
   CI thresholds. Real PG equivalence for changed repository queries; full fresh
   migration/bootstrap parity and RLS/grants only if SQL/security contracts change.
6. On final meaningful source: **one** applicable full Python run
   (`.venv-api/Scripts/python.exe -m tools.run_unit_tests`), affected React/browser,
   TypeScript/build/compile/targeted Ruff/format/diff. Preserve Phase 13 close
   regressions. No parser/Phase 11/12 rerun without a direct changed dependency.
7. Commit/push before deploying changed components. Migration then API then web
   only when required; no deployment for tooling/docs alone. Same-method hosted
   before/after reads, controlled local mutation-refresh checks and minimal remote
   preservation comparison; expanded security/Advisor/fixture checks only if
   contracts or remote writes change. Account for unavoidable owner Auth activity
   separately; no business/Storage/private-reference changes are expected.
8. Remove only the new disposable dataset/servers, verify no shared residue,
   record raw measurements and limits, report/handoff/checkpoint and commit/push.
   No cutover or autonomous Phase 15.

## 9. Stop and rollback boundaries

Stop a proposed change if it mixes unknown with zero, changes exact economy/title,
recomputes frozen history, exposes private rival data, breaks stale/CAS/original-key
replay, weakens auth, requires owner-season mutations or shows material unexplained
failure/latency regression. A sparse hosted dataset is a measurement limit, not
permission to populate the owner's season. If required access is missing, preserve
local progress and identify that concrete blocker.

Keep previous compatible source/deployment recorded. Revert a bad code change in
a new commit and redeploy only its component; never rewrite published history.
Prefer additive compatible DB changes; applied SQL is never edited/replayed and
any rollback uses a reviewed forward migration. Never roll back owner data or the
private V1 reference to recover a benchmark. Unknown remote outcomes require
reconciliation before retry. Phase 14 has **not** begun under this document.
