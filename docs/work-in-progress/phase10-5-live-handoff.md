# Phase 10.5 — live execution record

Closed historical record. The subsequent owner instruction authorized Phase 11;
the [Phase 11 live handoff](phase11-live-handoff.md) now owns current execution
state. The dated closure and evidence below are retained unchanged.

Observation: 2026-10-08 Europe/Madrid. **A–M + FINAL ALIGNMENT DONE; PHASE 10.5 DONE;
PHASE 11 READY FOR REVIEW / NOT STARTED.** [Final report](../phase10-5-completion-report.md).
The final closure at the end supersedes older dated package states below.
[Contract](../phase10-5-functional-alignment.md),
[continuity](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md),
[previous closed delivery](../phase10-completion-report.md).

## Verified entry and safety

Entry main `9a8620db5324104e753bb5f63b408d7b140502e8`. Fresh `git fetch origin`
succeeded; HEAD/origin/main identical, divergence 0/0, no tracked changes. Only
the protected guide is untracked; never open/inspect/hash/stage/move/delete it.
Local migrations 001–032 present at entry. No code, database or hosting changes in A.
**A published as `226ac7b`**, main push successful before B implementation.

Historical entry preflight (2026-09-29): pinned V2 `uwleqeuzsveqlugugzba`,
24 records through 032=`20260928111840`; 031=`20260928110301`.
Historical Phase 10 backend `6d2c66a` / frontend `3c83a16` were superseded by the
verified B+C deployment below. **Historical C closure: B and C DONE, publicly deployed.**
That checkpoint had 26 migration records through 034. D below supersedes its
hosting/history snapshot. Never replay 031?035.

Preserve owner active season `c6bcac5b-0b89-403f-8242-41ac58286ade`, other manual
seasons and Anto's current staging identity/PIN/admin. No fixture cleanup is
authorized for those records. Use local disposable PG if active-season guards
prevent staging tests. Prior delivery reports retain their historical results.

No remote fixtures were created. All B/C validation runners finished; local PG
is stopped. No pending migration/deployment operation remains.
Unrelated processes/remote operations not inspected: UNKNOWN.

## Alignment matrix and progress

| Package / finding verified against entry source | Classification | State |
|---|---|---|
| A: entry, contract, resumable memory | FIX NOW | DONE, published `226ac7b`. |
| B: League lacked primary GENERAL; existing 030 points view is authoritative | FIX NOW | DONE, source `d4ee903`, publicly delivered with C. |
| C: participant result entry with separate closed-day correction | FIX NOW | DONE, source `9be3d70`, local gates and safe public checks PASS. |
| D: daily wins/deaths and relevant unresolved ties | FIX NOW | DONE, source `2c8ad42`, 035 + public delivery verified below. |
| E: 026 requires initial manual A/B before activation | FIX NOW | DONE; observed progress/deaths, boundary-only ties, local/public gates and deployment verified. Closure below. |
| F: 029 lifecycle reads final daily snapshot positions for title | FIX NOW | DONE; accumulated championship, finish certificate and frozen Hall delivered. Closure below. |
| G: wipe counter exists in stats but lacks owned command/UI | FIX NOW | DONE; participant-owned counter, full closure and safe public delivery verified below. |
| H: Preview only selects scheduled match; missing-lock presentation insufficient | FIX NOW | DONE; independent public spectator/self-only private battle, nonblocking warnings and verified public delivery below. |
| I: pending promotions, vouchers, post-League spending and observed-save rewards | FIX NOW | DONE; economic authority preserved in final alignment. |
| J: Admin humanization | FIX NOW | DONE; final alignment closes prospective rules and the three backend gaps. |
| K: public competitive Team Lock projection | FIX NOW | DONE; strict public allowlist, reused by rival profiles. |
| L: reliable badges / in-game Champion evidence | FIX NOW | DONE; unknown remains distinct from observed zero. |
| M: directed performance guard | FIX NOW | DONE; lazy name reads retained, broader candidates deferred. |
| Final alignment: rules, freshness, profiles, categories, participant authority, 3+ title ties, first-lock timing | FIX NOW | DONE, source eb4e402, 041 and both deployments verified. |
| Later owner decisions | OWNER_DECISION_REQUIRED | Finalist separately undefined; future per-round/postgame caps deferred. All approved 10.5 rules are implemented; no new decision request. |
| Physical effects, cloud save ingestion, installer/updater | FUTURE LAUNCHER/CLOUD | Out of scope. |
| Final sprites, item art, audio and broad UI redesign | POLISH | Deferred. |
| Manual Discord judicial verdicts and modern Cup formats | INTENTIONAL V2 DIFFERENCE | Preserve; no legacy jury/Swiss restoration. |

Target evidence: `app/application/frontend_reads.py`, `web/src/features/core.tsx`,
`app/api/routes/matchdays.py`, `app/domain/services/league.py`, migrations
026/027/029/030, and Phase 9 parser contracts. Targeted review only; no repeated
full-project audit. Independent read-only B review confirmed: adjusted competitive
deaths are not visible Box 8 deaths, identity revision alone does not prove a
complete box, and disabled historical participants must not disappear.

## B delivered implementation

GENERAL uses official accumulated points from 030, exact decimal strings and
server ordering; no sporting rank/champion inferred from a rendering tie-break.
Include all season participants, including inactive/historical rows. Current
wallet balance is independent of frozen points. Visible dead count needs an
explicit complete current Box 8 observation; absent/incomplete data is unknown,
not zero. Current save changes never recalculate official points.

`GET /v1/read/seasons/{id}/league` uses enabled JWT and a single service-only
`league_general_read(uuid)` RPC in new **033_league_general_read.sql**. No new table,
competition mutation or browser privilege. STABLE read keeps one database snapshot.
The aggregate returns reached/current days, all roster rows including disabled and
retired historical trainers, public names, official exact points and current coins.
Secondary numeric/name/ID ordering is presentation only; no rank/title returned.
Coins are integer strings too: two maximum valid judicial debts exceed the old
int32 balance view, so this RPC sums the scoped ledger directly. The existing
overview/shop balance view still has that inherited limitation; repair its consumers
when touching economy in I, without silently claiming this package fixed them.

Dead count uses only the selected owner's same-season, non-deleted parsed save,
matching parser/schema/identity revision and optional payload identity/hash checks.
A complete Box 8 with exactly 30 unique explicit slots proves a count (including
zero); malformed/missing data returns null + `unknown`. Only count/provenance/time
leave SQL, never the private payload/identity/Storage fields. Unsupported official
snapshot shapes fail explicitly instead of being interpreted as zero points.

React defaults to GENERAL and performs only its aggregate read for that screen;
the existing overview is loaded for a selected day. Current/completed chips replace
the dropdown; future chips are filtered in SQL and React. Top 3, A/B and matches
remain in daily views. Changing season or losing the selected reached day falls
back to GENERAL. Exact point/coin strings are rendered without JS arithmetic.
The responsive table scrolls horizontally and supports keyboard focus; amounts
remain readable instead of splitting digits across lines. Mobile screenshot inspected.

B does not change title certification, sporting ties or initial A/B (D-F).
Self-service result entry was subsequently delivered in C. No owner decision inferred.

## Evidence ledger

- A, entry source above, Windows local: Git branch/HEAD/remote/status inspection
  and fresh fetch PASS. Document links and `git diff --check` are the A gate;
  no code/database test is claimed for this documentation-only block.
- Historical Phase 10: 565 Python, 11 React and nine browser tests at the commits
  recorded in its report, not rerun or claimed as Phase 10.5 evidence.
- A/B local-only evidence below predates the B+C public checkpoint. It does not
  supersede the current deployment/history at the end of this record.

### B local gates (2026-09-29, Windows, PostgreSQL 17, Edge)

Source: `226ac7b` plus the B implementation/test/bootstrap changes published with
this handoff update. This is not a claim that remote runs used this source.

- Python full suite: **571 PASS**, exit 0, 40.708 s (565 inherited + six new API/
  transport tests). `%TEMP%/phase10-5b-unit-final.log`.
- React unit/transport: **11 PASS**, exit 0. TypeScript + production Vite build
  PASS with the existing HTTPS Railway URL; final JS gzip 113.41 kB, CSS 6.36 kB.
- Browser: **13 PASS**, exit 0, 32.9 s, nine existing flows and four new GENERAL scenarios, including
  no days, first current, closed/current, final closed, exact/tied/negative amounts,
  inactive history, 1440/768/390 widths, no future tabs and preserved podium/A/B.
  Final combined-run log: `%TEMP%/phase10-5b-browser-final.log`.
- `.venv-api/Scripts/python.exe -m tools.validate_phase10_5_league_sql --psql <local-psql>`:
  PASS, exit 0. Real fixture totals, cumulative penalties only once, negative ledger
  beyond int32, current day filtering, private-source exclusion, observed zero/five,
  unknown malformed/foreign/missing sources, invalid-history rejection, archive/
  discarded behavior and service-only catalog privileges. Separate DB sessions
  observe old name/balance before commit and both new values after commit.
  Exact count/full-content hashes of **all 46 public tables** restored after fixtures.
- Independent 001–033 build and generated-bootstrap build: schema/catalog/RLS PASS;
  normalized public schema/grants/ownership dumps **10,627 identical lines**.
  `%TEMP%/phase10-5b-{schema,bootstrap}.log` and matching `*-schema.sql` dumps.
  Only random pg_dump restrict keys removed in comparison. No old migration replay
  on staging; 001–032 file contents independently unchanged against `226ac7b`.
- `py -m ruff check` on affected API/service/adapter/new test/validator files PASS;
  compileall app/tools/tests, Prettier and `git diff --check` PASS.

Resolved validation setup failures are retained honestly: the first full Python
run found two migration-manifest/bootstrap-header expectations still pinned to 032;
updating the explicit expected set to 033 fixed both, then the full suite passed.
The new browser harness initially sampled before Home had loaded, then assumed
one dev GET despite React StrictMode cancellation/remount; it now waits for Home
data and bounds dev requests while asserting no overview request from GENERAL.
Production build initially failed its required API-URL guard, then passed with
the real existing URL. Ruff is available through `py`, not `.venv-api`.

Local database names: `pokeapp_v2_validation_phase10_5b` and `_bootstrap`, loopback
port 55439; PG data `%TEMP%/pokeapp_phase10_5_pg`, binaries
`%TEMP%/pokeapp_pg17_phase8c_20260922/portable/pgsql/bin`.
No staging fixture, owner-data mutation, Auth change or Storage access occurred.
All B test runners finished. Local PG was stopped cleanly before publication;
restart that exact local data directory only after checking the port/process state.
Durable source hashes and gate summaries: [B evidence](../phase10-5-validation-evidence.json).

## C implementation and evidence - 2026-09-30

Entry `d4ee903215853d4ef14c224da71c7f60542e756e`, main/origin 0/0 after fresh
fetch; tracked clean, protected guide only untracked. Actual remote history remained
24 records through 032; 033 pending. Infrastructure read preflight identified the
existing Railway service and Cloudflare Worker, both still serving Phase 10 source.

Any enabled, active, eligible season participant can record/edit/clear winners of
any current open League match, including third-party matches. JWT determines the
actor. No admin or opponent confirmation. New enabled-JWT routes:
`GET /v1/seasons/{sid}/matchdays/{did}` and `PUT .../{did}/results`, strict existing
DTOs, scoped whitelisted responses and service-only `api_participant_matchday`.
New **034_participant_matchday_results.sql** uses the existing result helper,
CAS revisions, actor/scope/key/body receipts and transactional before/after events.
Existing admin open/close/cancel/correction paths remain unchanged.

Locks follow principal, receipt, season, roster, day, matches, configuration.
Current enabled/active/eligible authority is checked before replay. Identical
receipt retrieval after close writes nothing; new edits after close/later day fail.
Discarded seasons are unavailable to both read and mutation. Entire invalid
batches and injected failures roll back. Ordinary clearing intentionally retains
existing null-winner semantics. No browser table/column/RPC grant was added.

League's current day contains "Registrar resultados"; Admin links there for
ordinary entry and retains its separate closed-day correction form. The form
sends only changed matches, hides revisions, preserves unknown-outcome body/key,
and requires explicit refresh after 409. Refresh/invalidation touches participant
day state, overview and admin day state only; it does not refetch unrelated PC,
shop or GENERAL (open result edits do not award official points).

Validation source: entry plus C files, LF-normalized hashes retained in
[C evidence](../phase10-5c-validation-evidence.json). Windows / PG 17 / Edge:

- Full Python **578 PASS**, exit 0, 36.708 s; `%TEMP%/phase10-5c-unit.log`.
- React **11 PASS** and browser **17 PASS**, exit 0, 39.3 s. Browser fixtures
  intercept API; non-admin third-party entry/edit/clear, narrow reads, 409,
  identical unknown retry and closed ordinary form. No public JWT claim here.
- TypeScript/Vite production build PASS against the real existing API URL;
  JS gzip 113.94 kB / CSS 6.36 kB. Ruff, compile, Prettier and diff checks PASS.
- Existing integrated local SQL regressions: matchdays 20, participant status 24,
  trials 8 groups PASS, including cleanup. `%TEMP%/phase10-5c-regressions.log`.
- Final C SQL: **six groups PASS**, exit 0; authority matrix, separate-session
  writes/replay/close races, four exact all-public-table rollback boundaries,
  admin correction and browser denial. Exact **46 public tables** restored.
  `%TEMP%/phase10-5c-sql-final2.log`. Final focused API: **7 PASS**, exit 0.
- Final 001-034 and generated-bootstrap builds, schema/RLS/catalog PASS;
  normalized public schema/grants/ownership **10,725 identical lines**. Only
  random pg_dump restrict keys excluded. `%TEMP%/phase10-5c-rebuild-final2.log`
  and `phase10-5c-{migrations,bootstrap}-schema.sql`.

Resolved harness issues: rebuilding the same local DB exposed that `reset_dev.sql`
did not remove new B/C helpers; its local reset list now includes them. Published
001-033 unchanged; reset is never run remotely. The added discarded-season fixture
initially lacked mandatory `discarded_at`; corrected fixture retains that constraint.
A direct unittest module invocation lacked the discovery import path; use
`tools/run_unit_tests.py --pattern test_api_participant_results.py` instead.
The Admin-to-League link was corrected to the existing `/liga` route and verified
by browser navigation. No product constraint was loosened to pass a test.

Local databases: `pokeapp_v2_validation_phase10_5c` and `_bootstrap`,
127.0.0.1:55439, same disposable PG data/binaries as B. Server stopped after
cleanup; verify actual process/port state before restarting it.

## B+C public delivery - 2026-09-30

Implementation `9be3d70f1aacf0a6ca37d9d3d690c24dd1268587` committed/pushed before
migration application and deployment. **B and C DONE; Phase 10.5 IN PROGRESS.**
At that B+C checkpoint, no D code or Phase 11 had started. [Public evidence](../phase10-5bc-public-evidence.json),
[Advisor inventory](../phase10-5bc-security-advisor.json).

Fresh target/history/full baseline/Advisor precede the only two remote SQL writes:

| Migration | Applied version |
|---|---|
| 033_league_general_read | `20260930113319` |
| 034_participant_matchday_results | `20260930113328` |

SQL came from committed Git source using the supported
[Supabase apply-migration API](https://supabase.com/docs/reference/api/v1-apply-a-migration).
Both applied exactly once. **Do not replay.** Original 24 history rows retain their
full record hashes; total 26. No bootstrap/reset/failure DDL/new tables/owner edits.
Three new helpers are invoker/fixed-search-path/service-only, including PUBLIC
and browser EXECUTE denial. Published migration files 001-033 are unchanged.

Railway: existing PokeApp V2 project `f5c4666a-508f-4e5a-8aae-a54581814f29`,
service `9a78e086-c927-471f-8bb9-befe62c77de7`, environment `production` (V2 staging).
Deployment `1b5aa59b-3262-44f4-b639-03e830117aca` SUCCESS, source `9be3d70`.
Runtime image digest `sha256:697b36e0b4cffe25f4dbba708f28230c172ad6f936936a71746ddfcb9e822f83`.
Committed-only 224-file API bundle, one replica, existing CORS/secrets unchanged.
https://pokeapp-api-production.up.railway.app.

Cloudflare: same account `a8e089ff4da821ed3dbd24701437514c`, Worker `pokeapp-web`,
https://pokeapp-web.pokeapp-v2.workers.dev. Source `9be3d70`; version
`9bf8ac7d-0d31-494b-83a6-9223e34e9b6e`, deployment
`275adc6f-cb8e-49d7-a83f-683ad78c75a0`, 100%.
Built against the existing HTTPS API; frontend deployed after the compatible
backend was ready.
Build/dry-run/deploy PASS; public JS/CSS hashes equal final local build, JS gzip
113.94 kB / CSS 6.36 kB. Deep SPA `/pc`, MIME, CSP, nosniff and allowed/rejected
CORS PASS. Public calls prove actual deployed routes; health alone is not readiness.

Real public read-only validator: **PASS**, run
`phase10_5_public_reads_1f893d43f4bc4b8e9b1d6e48422a28d3`, source `9be3d70`.
Existing PIN login/refresh and `/v1/me` preserve the same enabled/admin Anto.
GENERAL returns all eight participants, two reached/current day tabs, exact
point/coin strings and eight honest unknown dead counts. Participant GET matches
current official scope. Anonymous/invalid JWT 401, injected actor field 422, and
valid-shaped PUT against a just-verified absent season returns structured 404,
proving the deployed RPC path without changing a manual result.

Browser: **22 real screen/viewport visits PASS**, eleven screens at 1440 and 390,
GENERAL columns/roster/day tabs, current day, admin reads and logout. No intercepted
API, business writes, page/API errors, unexpected app origins or persisted tokens.
Known installed Kaspersky injection origin is recorded separately as in Phase 10.
The owner's current J2 is scheduled, not open: normal result form correctly absent.
Positive non-admin input/edit/clear, unknown retry and concurrency are **local**
API/SQL/browser evidence; no public positive mutation claim is made from Anto's
admin session. No fixture identities created and no owner role/PIN/season changes.
Inspected [GENERAL desktop](../evidence/phase10-5/public-general-desktop.png) and
[current-day mobile](../evidence/phase10-5/public-current-day-mobile.png).

Owner safety evidence is time-scoped: immediately after both migrations, **52/52
full tables were identical** to fresh preapply. A later independent observation
found **49/52 full tables identical**, including all 46 public + both Storage and
Auth identities. Only Auth users/sessions/refresh tokens changed; refresh rows
100 to 102. All current Auth rows mapped to the sole owner; exact historical
session causation is not inferred from aggregate hashes. No prior owner-excluded
baseline existed, so no retrospective scoped PASS is invented.

The subsequent public runner takes a fresh 52-table baseline with only the owner's
Auth activity excluded (all public owner rows remain fully included): **52/52
identical**, all 26 history rows unchanged, no fixtures/cleanup mutations.
Independent final check at 16:28:50 UTC also proves **52/52 identical**,
**26/26 migration records unchanged**, owner mapping/enabled/admin preserved and
zero added/removed Advisor ERROR/WARN. No Storage bytes were touched.
Advisor before/after migration and public run: **24 ERROR / 5 WARN / 122 INFO**;
zero added ERROR/WARN by finding/object/severity. Existing findings not repaired
or relabelled. Credential values are absent from repository evidence.

Single observed HTTPS samples: GENERAL ~1.14 s, overview ~4.96 s, participant read
~1.62 s including JWT/network; not a benchmark or SLA. GENERAL remains one aggregate
RPC. C mutations invalidate only relevant day/overview state. Broader overview/auth
query chains stay recorded for Phase 14; no global performance work performed.

Raw evidence: `%TEMP%/phase10-5bc-deployment-20260930`,
`phase10-5bc-independent-migrations`, `phase10-5bc-public-readonly`,
`phase10-5bc-independent-final`, `phase10-5bc-{railway-deployments,cloudflare-deployments}.json`,
`phase10-5bc-api-9be3d70/deployment-source.json` and local gate logs above.
Local PG stopped cleanly; all local fixtures restored. Protected guide never
read/inspected/hashed/staged/touched. No V1/reset/Phase 11 work.

## Historical next step at C closure

**Package D: daily sorting and relevant unresolved ties.** Read the contract,
`app/domain/services/league.py`, matchday planning/027 and focused competition tests.
Daily wins then fewer adjusted deaths; remove H2H-first and alphabetical sporting
resolution, preserve frozen snapshots, CAS/replay and close/correction safety.
Any SQL change needs new forward **035** after verifying actual history. Do not
replay 033/034 or alter manual owner results to make fixtures pass. Unresolved
owner rules remain unresolved; do not infer championship tie policy.

C is a complete atomic checkpoint. No D code had started at that checkpoint. Phase 10.5
remains IN PROGRESS (D-L independent work and decisions remain), whole project
estimate ~80%; Phase 11 **NOT READY / NOT STARTED**. Final documentation is in its
own commit; obtain its hash from Git. Check fresh status/refs before continuing.


## D delivery ? 2026-10-01

**D DONE; Phase 10.5 IN PROGRESS. E and Phase 11 NOT STARTED.**
[Delivery report](../phase10-5d-completion-report.md),
[local evidence](../phase10-5d-validation-evidence.json),
[public evidence](../phase10-5d-public-evidence.json),
[Advisor inventory](../phase10-5d-security-advisor.json).

Entry `92d9e5548fe028cda78a95ab41375e0dcea28184`, fresh main/origin 0/0,
tracked clean. Source **2c8ad428163ee21d8954b5fc70139805f1b87704** committed/pushed
before remote work. Documentation closure uses its own Git commit; do not invent
a self-referential hash. The protected guide remains the only untracked exception.

D uses wins descending then fewer authoritative adjusted deaths for all group sizes.
No H2H/name/slug/UUID sporting fallback. Neutral groups share sporting positions;
consequential groups block close/correction until an admin records the external
complete order/reason against a current review hash. New forms have empty initial
choices and preserve unknown-outcome body/key. Rule/groups/decisions are frozen in
existing append-only snapshot history. Old corrections retain their recorded legacy
rule and existing window guards. V1's isolated original helper has identical AST.
The final title/accumulated-points defect remains F, and championship tie policy is
still OWNER_DECISION_REQUIRED. D does not decide either.

Local gates at source above: **623 Python, 11 React, 20 browser PASS**. Browser
fixtures are synthetic, not a public positive mutation claim. Seven real local PG
D groups PASS, four exact rollback boundaries across all public tables, same/different
key resolution races, stale inputs, neutral final lifecycle and old corrections.
Existing SQL regressions: matchdays20 / participants24 / lifecycle19 / trials8 /
C results6 and B GENERAL PASS. D/C each restore all 46 public tables exactly;
independent final prefix scan has zero fixture rows. Schema/RLS/catalog rebuild of
001?035 and independent bootstrap PASS, **10,834 identical normalized schema/grant/
owner lines**. Formatting, compile/lint, TypeScript/build and Workers dry run PASS.
Raw logs and resolved harness failures/provenance limits are in the report/evidence.
Cross-database data hashes are not a valid cleanup baseline: independently generated
schema/RLS fixture UUIDs/timestamps differ. No such content-equality PASS is claimed.

**STAGING_DONE_ZERO_RESIDUE for D.** Pinned V2 `uwleqeuzsveqlugugzba`.
**035 applied once as `20261001111600`; DO NOT REAPPLY.** Existing 26 records remain
unchanged, 27 total. Fresh project/history/source/baselines/Advisor plus immediate
checks preceded the only write: committed 035 via the supported migration API.
No old migration edits/replays, remote reset/bootstrap/failure DDL or data mutation.
Six changed helpers retain fixed search paths/invoker/service-only execution.

Existing Railway project/service, environment production (label; isolated V2 staging):
D deployment **32c10fee-a30a-4c1c-8b5b-4bec9951f637**, SUCCESS, source `2c8ad42`,
226-file committed bundle, one replica. Image
`sha256:7c8a7051a791cfef1a1e598fbbb6a04a5cecc0af0becf5e2a775d49c6b86a9e9`.
Existing Cloudflare Worker: version **fc5ae861-dfa9-43bc-87b9-d4871642d682**,
deployment **3d92653c-9336-4dad-90eb-0e522482a418**, 100%, same source.
URLs remain https://pokeapp-api-production.up.railway.app and
https://pokeapp-web.pokeapp-v2.workers.dev. Backend deployed before frontend;
secrets/origins unchanged. Served asset hashes, SPA/MIME/CSP and CORS PASS.
JS gzip 115.38 kB / CSS 6.36 kB. No N+1 API loop introduced; existing overview/admin
invalidation performance stays recorded for M/14, without broad repair here.

Real public run **phase10_5_public_reads_31caaaeee91b4177838879a89a1e06fe**, exit0,
PASS: existing Anto PIN/login/JWT refresh and enabled admin; exact GENERAL/overview,
participant state, typed D absent-resource denial and injected-plan rejection;
**22 real browser screen/viewport visits**, admin visibility/reads and logout.
No intercepted API or business mutation. Positive close/tie/correction races remain
local evidence. Anto and the active manual Prueba1.0/J2 scheduled season are preserved.
No new identity, temporary credential reset, role change or competitive edit.

Runner and independent final SQL at **11:23:29 UTC**: **52/52 full table contents
identical**, 27/27 migration records unchanged, same owner mapping/enabled/admin,
Advisor **24 ERROR / 5 WARN / 122 INFO**, zero added/removed ERROR/WARN. Scope excludes
only the existing owner's Auth activity; every public/manual row and Storage metadata
is included. No Storage bytes touched. Fixtures created: zero. All local test,
browser/deployment processes finished; local PG stopped. Unrelated processes UNKNOWN.

Raw evidence `%TEMP%/phase10-5d-{deployment-20261001,public-readonly,independent-final}`,
`phase10-5d-{python-final,browser-final,sql-second,regressions,rebuild}.log`, matching
source/schema/exit artifacts and `phase10-5d-hosting-final.json`. Explicit installed
CLI 2.118.0 path was used via `POKEAPP_SUPABASE_CLI`; unpinned npx tried an uncached
new release. Verify tools in a future session; do not assume auth or deployment state.

## E entry review - 2026-10-01

**Historical entry: E implementation stopped for a progress-authority decision;
resolved by the owner update below. A-D remain complete.** The E continuation replaces
the preceding D stop instruction. This is an entry review, not an E validation PASS.

Entry `58ef75f4aedab8d4ba394d9a8d172cafc2351e16`; fresh fetch succeeded,
`main`/`origin/main` 0/0, tracked clean, protected guide the only untracked path.
The guide was not read, inspected, hashed or touched. This review changes only the
contract and this live memory; no application, test, migration or hosting changes.

Verified prerequisites against that source, with an independent read-only review:

- The A/B cut already exists: `ConfigVersionBody.division_sizes` and SQL026
  `admin_setup_validate_config` require positive A/B capacities whose sum equals
  the roster. Unequal capacities and odd participant counts are supported. No new
  numerical cut needs an owner decision.
- The approved E prompt fixes J1 at Medal 2 inclusive. Current configuration has
  no progression-cap field/guard. SQL026 `api_admin_initial_divisions` still accepts
  manual draft assignments before J1 preparation/activation, without progress or
  death-readiness checks; this is precisely the E behavior to replace for modern
  initialization, while retaining existing memberships/history.
- `season_player_stats.badges_count` defaults to 0 (002). Enrollment initializes
  that default (026). Modern API/services only read badges; there is no supported
  progress update/attestation command. SQL026/027 revoke browser stats writes.
- `app/save_parser/models.py::ObservedSave` contains game/trainer/party/boxes, but
  no badge/progress evidence. Legacy badge settings are a separate runtime.
  Cloud ingestion remains absent; it cannot be claimed as an E prerequisite that
  already works.
- Reuse SQL030's authoritative adjusted deaths. Missing current save/observation
  evidence must not be presented as observed zero; a new manual death override is
  not authorized. Existing registered facts can support a provisional preview,
  but relying on fixture/service-seeded data alone does not deliver the ordinary
  new-season flow.

The prior full 10.5 instruction allows explicitly provisional registered/manual
evidence, but reserves ordinary admin intervention for the exceptional boundary
tie. It does not choose who may attest qualifying progress. A new participant
self-attestation and an admin attestation confer different sporting authority;
neither is inferred from result-entry permission or external-tie authority.

**Exact pending question:** until save ingestion exists, who may manually attest
that each participant has completed Medal 2: that participant, an administrator,
or no new writer (consume existing records and remain unready when evidence is
absent)? Asked in this session; no answer received at this observation. Deaths
continue to use the existing source/calculation, without a parallel manual total.
The stop follows the E prompt's explicit instruction to stop for a genuine missing
owner decision, not an inferred requirement for deployment approval.

Fresh read-only public verification, 2026-10-01 11:39 UTC, exit 0:

- Linked project `uwleqeuzsveqlugugzba` verified; 27 migration records, latest
  035=`20261001111600`. No 036 exists in local source or the inspected history.
- Same Anto trainer/Auth mapping, enabled and admin, verified by scoped SELECT.
  No credential read/change/login was needed for this inspection.
- Railway deployment `32c10fee-a30a-4c1c-8b5b-4bec9951f637` remains SUCCESS,
  source message `Phase 10.5 D 2c8ad42`.
- Cloudflare deployment `3d92653c-9336-4dad-90eb-0e522482a418` still serves version
  `fc5ae861-dfa9-43bc-87b9-d4871642d682` at 100%.
- Zero remote writes or fixtures. No positive sporting mutation or new deployment.
  The D full-table equality/Advisor/browser gates above remain dated D evidence;
  they were not rerun or relabelled as E tests. No E implementation tests were run.

Raw evidence: `%TEMP%/phase10-5e-entry-rygsmvun/{history,owner,railway,cloudflare,
entry-summary}.json`. The first read script completed Supabase reads but failed
before launching Railway because Windows required the `.cmd` executable suffix.
The corrected hosting read exited 0; no deployment/migration retry occurred.
All review subprocesses finished; no E validation server or fixture was started.
Unrelated process state remains UNKNOWN. Documentation checks passed: only these
two intended Markdown files changed, UTF-8 decoding/relative links/E anchor valid,
and `git diff --check` clean. Publication uses a documentation-only commit; obtain
its hash and actual push state from Git.

## E observed-progress implementation - owner decision 2026-10-01

Entry `8e3d598205613d950e3c4851bd07fb0ffe15ba53`; fresh fetch and main/origin 0/0,
tracked clean, protected guide excluded. The owner rejects both participant and
admin manual medal attestation. Normal progress is reliable save/parser evidence;
missing observations stay unknown and block initial assignment. The neutral parser
may be extended now, without cloud ingestion or a final Launcher.

Implementation `0215f73457b7c3245b29af41e0200fd590f2db59` is committed and pushed.
Optional versioned primary-region badge evidence, service-only observed-readiness/
initial-split transition, boundary-only audited decisions and minimal React are
implemented. New seasons start gameplay before A/B; existing seasons preserve
legacy initialization. No manual progress command, Team Lock prerequisite, cloud
ingestion, final Launcher, F implementation or Phase 11. E supplies the minimal
badge foundation; later L remains subject to its remaining scope review.

Local gates PASS: 663 Python, 11 React, 24 Edge, parser 54 assertions/six integration
groups, eight E SQL groups/twelve exact rollbacks, inherited 026-030/B/C/D and four
fresh build parity (11,462 lines). See [E report](../phase10-5e-completion-report.md)
and [evidence](../phase10-5e-validation-evidence.json). The final E flow also proves
initialization through participant results and D close without changing frozen
initial evidence. Local runners finished with exact cleanup; local PG is stopped.

Fresh pinned preflight captured 52 full/scoped public/Auth/Storage tables and
27 migration records. Migration **036=`20261001165951`** applied once from that
published source; 52 original tables unchanged and new snapshot table empty.
**Do not replay 031-036.** Twenty helper catalog checks and private table ACL PASS.
Advisor 24 ERROR / 5 WARN / 125 INFO; zero new ERROR/WARN. Three new INFO concern
the backend-only snapshot table (no RLS policy and two unindexed foreign keys).

Railway deployment `f6ae9135-6425-4fa0-b76d-a26002a9993a` is SUCCESS; existing
one-replica service configuration unchanged. Cloudflare version
`0224318e-38d6-4178-ae3a-646384328eb8`, deployment
`3d829325-66fc-4da4-88f4-b7bd4967f8d7`, 100%, source `0215f73` for both.
Existing URLs remain unchanged. Served assets, deep SPA/security headers/CORS PASS.
The first public read runner finished FAIL at browser validation: 22 visits but four transient 503 reads; API gates and 53-table/history/Advisor comparisons PASS. A targeted twelve-read concurrent check reproduced six 503s. Local direct V2 reads passed in both default and HTTP/1 modes, so no root cause is inferred yet. Sanitized diagnostic follow-up `d24b551` is committed/pushed, with 19 focused API/adapter tests and 22 reads/CORS tests PASS; backend deployment pending. Raw evidence: `%TEMP%/phase10-5e-public-readonly` and `phase10-5e-concurrent-read-check.json`. Full E closure remains pending investigation and a clean public run. No fixtures,
positive owner sporting mutation, identity/PIN/admin change or Storage-byte write.
Remote deployment evidence: `%TEMP%/phase10-5e-deployment-20261001`.

The owner approved final title policy for future F: final accumulated points,
external audited Bo3 for exactly two tied at the top; fewer authoritative adjusted
deaths for exactly three, otherwise explicit owner exception if unresolved. See
the contract. This is documentation only; F is not started.

## E resumed closure - 2026-10-02 Europe/Madrid

Owner authorized completing E with a fresh complete closure gate. Entry
`d24b55152d7d8a29c3632a4f4feec710fb331040`, main/origin 0/0 after fresh fetch.
The preceding E delivery/503 notes were already local uncommitted changes in this
handoff and are preserved. Protected guide remains excluded and unread. No other
tracked changes at entry. No F or Phase 11 work.

Fresh read-only preflight verifies V2 `uwleqeuzsveqlugugzba`, **28 history rows,
036 applied exactly once as `20261001165951`**, 53 full/scoped table baselines,
same owner identity/enabled/admin, Advisor **24 ERROR / 5 WARN / 125 INFO**.
Source and raw evidence: `%TEMP%/phase10-5e-resume-20261002.py` and
`%TEMP%/phase10-5e-resume-20261002/`. No migration or business write performed.

The interrupted diagnostic deployment actually completed: Railway
`1ef649e7-1489-4f97-a4fa-ef08839f5021` SUCCESS, source `d24b551`, image
`sha256:544a744caa62cf8b2101de5678d6e2e7f93e835b7680d50a2fa05ac7282f32cc`.
Cloudflare still serves E version `0224318e-38d6-4178-ae3a-646384328eb8`,
deployment `3d829325-66fc-4da4-88f4-b7bd4967f8d7`, 100%, source `0215f73`.
Do not repeat the completed diagnostic deployment merely because the previous
handoff reported it pending. Fresh concurrent read reproduction is running;
cause remains unproven until the sanitized diagnostic is observed.

Local PG was stopped at entry. Starting the existing disposable directory without
an explicit port used 5432, so the first rebuild could not connect to 55439 and
made no database changes. That server was stopped cleanly and restarted explicitly
on loopback 55439. Fresh independent databases `pokeapp_v2_validation_phase10_5e_resume`
and `pokeapp_v2_validation_phase10_5e_resume_bootstrap` are now being built.
Fresh closure results are pending; previous E PASS remains historical evidence.

Fresh source `d24b551` closure progress: **664 Python (0 failures/0 skips), 11 React,
24 Edge, 54 parser assertions/six binary integration groups PASS**; compile,
TypeScript/Vite, format and Workers dry run PASS. Migration/bootstrap four-build
parity **11,462 lines**, regenerated bootstrap unchanged, 001-036 immutable.
Broad Ruff comparison over app/tools/tests: 1,010 inherited findings in both entry-E
and final source, **zero new**; this broader scope differs from the historical
86-finding subset and is not a claim of globally clean lint. E SQL eight groups,
twelve rollbacks and exact 47-table cleanup PASS. Remaining inherited SQL families
are still running in the disposable resume database; PG must be stopped afterward.

Public run `phase10_5_public_reads_11efa6eac0154745badf74fb3ee02abf` **PASS**:
21 API checks and 22 browser screen/viewport visits, no API interception or business
writes. Runner comparisons: all 53 scoped tables, 28 history rows and Advisor
unchanged. Two separate concurrent batches before/after browser: **24/24 HTTP 200**.
The earlier 503 incident was **not reproduced in this window; cause UNKNOWN**.
No transport fix was made and recovery is not attributed to diagnostic logging.
The compatible backend is already deployed; its 229-file committed bundle matches
Git. Existing frontend served assets match the fresh build; headers/CORS PASS.
Independent final remote data/catalog/Advisor comparison is running. Evidence:
`%TEMP%/phase10-5e-resume-public` and `%TEMP%/phase10-5e-resume-20261002`.

## E closure verification - 2026-10-03 Europe/Madrid

Entry `d24b55152d7d8a29c3632a4f4feec710fb331040`; fresh fetch confirms
main/origin 0/0. The two modified E documents and four untracked E evidence/image
files already existed at entry and are preserved. The protected guide is excluded
from all reads and writes. No application change or new migration is required by
the evidence inspected so far.

The previously pending SQL process actually finished successfully on 2026-10-02:
`sql-gates.json` records exit 0 for E and all inherited 026-030/B/C/D regressions;
the final log confirms every family completed. `local-cleanup.json` plus both
full-content baselines prove all 47 public tables restored and zero fixture residue.
Current `pg_ctl status` reports no server running; no PostgreSQL process or listener
on 55439 exists. A historical graceful shutdown is not inferred from that check.

Fresh remote read-only preflight is running under
`%TEMP%/phase10-5e-close-20261003.py`, with a new evidence directory. No remote
migration, deployment, fixture or business write is planned. Local gate evidence
will be tied to unchanged source before publishing closure. Current owner instruction
allows F only after E is fully closed and only with capacity for another complete
atomic package; it supersedes the earlier E-only stop wording. Phase 11 remains
prohibited.

Fresh concurrent public reproduction at 2026-10-03 11:06 UTC returned **3/12 HTTP
503**, so the historical clean window does not close this incident. Railway's
sanitized diagnostic records three simultaneous `frontend_read_failed
operation=rows cause=ReadError` entries. This establishes response transport loss;
the underlying network cause remains UNKNOWN. Existing deployment/source/history
and Advisor are confirmed unchanged. Do not claim public closure yet.

The narrow follow-up adds one retry only for `httpx.ReadError` in the frontend
SELECT/read-only-RPC repository. Status errors, malformed data, timeouts and other
failures retain their existing failure behavior; mutation repositories receive no
retry. Six focused real-PostgREST/MockTransport tests PASS, including persistent
failure, identical request scope, concurrent retry budgets and no mutation retry.
Full Python closure **670 PASS**, exit 0; compile and touched-file Ruff/format PASS.
Implementation **90a31fc3b4220cefbe7c160902158084aea2569e** committed and pushed,
main/origin 0/0, before upload. A new 229-file committed-only bundle was submitted
to the existing Railway service as deployment
`6aa70f72-f0cb-41a1-86d6-7b4227803392`; last inspected status DEPLOYING.
No SQL/frontend/dependency change. At that observation, remote public validation
remained pending; the completed result follows and supersedes those pending notes.

### E complete checkpoint - 2026-10-03, 13:18:42 Europe/Madrid

**E DONE / STAGING_DONE_ZERO_RESIDUE.** [Final report](../phase10-5e-completion-report.md),
[closure evidence](../phase10-5e-closure-evidence.json),
[public evidence](../phase10-5e-public-evidence.json),
[Advisor](../phase10-5e-security-advisor.json). All earlier incomplete E notes are
dated history and are superseded by this checkpoint; earlier failed runs are retained.

Entry HEAD **d24b55152d7d8a29c3632a4f4feec710fb331040**. Final application HEAD
**90a31fc3b4220cefbe7c160902158084aea2569e**, pushed before the follow-up deployment.
Documentation/evidence closure is its own subsequent commit; obtain that exact HEAD
from Git (the commit carrying this section), rather than a self-referential hash.
Explicit staging only; no protected-guide access, credential staging or history rewrite.

- **670 Python PASS**, including six new bounded-recovery transport tests; compile,
  touched-file Ruff/format/diff PASS. No mutation retries were introduced.
- Unchanged-source 2026-10-02 gates independently verified: 11 React, 24 Edge,
  parser 54 assertions/six binary groups, eight E SQL groups/twelve exact rollbacks,
  026-030/B/C/D SQL, exact 47-table restoration, four-build 11,462-line schema/grant/
  ownership parity. These are retained dated runs, not reruns for the read fix.
- Remote **28 migration records**, **036=20261001165951 exactly once**. No new SQL;
  **001-036 remain immutable; do not replay 031-036**.
- Railway **6aa70f72-f0cb-41a1-86d6-7b4227803392 SUCCESS**, source `90a31fc`, image
  `sha256:f7a8efe77db345305ddda1c6cd398f06cd58d48779edade104b750d05404ee7d`.
  Committed-only 229-file bundle; service manifest and one replica unchanged.
- Cloudflare **3d829325-66fc-4da4-88f4-b7bd4967f8d7**, version
  **0224318e-38d6-4178-ae3a-646384328eb8**, 100%, compatible source `0215f73`.
  Live asset equality, SPA/MIME/CSP/nosniff/CORS PASS; no frontend redeployment.
- Public **phase10_5_public_reads_d5d933292db242288543d89f52fb847a PASS**, exit 0:
  21 API checks, 22 real browser visits, two post-deploy concurrent batches **24/24
  HTTP 200**. Existing owner login/refresh and typed denials only; no business writes.
- Independent **53/53 scoped full-table contents identical**, 28/28 migration
  records unchanged, same owner identity/enabled/admin; 20 helper and snapshot ACL
  checks PASS; zero fixture residue. Only existing owner Auth activity is excluded;
  all public/manual data and Storage metadata are included. No Storage bytes touched.
- Advisor **24 ERROR / 5 WARN / 125 INFO**, zero added/removed ERROR/WARN.
- Historical 503 trigger is still unknown at the network level. The fresh pre-fix
  3/12 failure is linked to `ReadError`; the code now recovers one such response
  loss. Post-fix hosted samples had no errors or retry log entries, so actual retry
  execution is proven locally, not claimed from the hosted window.

Raw evidence: `%TEMP%/phase10-5e-close-20261003`, `phase10-5e-close-public`,
`phase10-5e-close-hosting-final.json`; retained complete local gates in
`phase10-5e-resume-20261002`. All task test/public/deployment runners completed.
Local PostgreSQL is stopped (`pg_ctl` exit 3); no local fixtures remain. No new
remote fixtures were created. Unrelated processes remain UNKNOWN.

Progress authority, J1 Medal 2, unknown != zero and immutable initial history are
delivered. Full Launcher/cloud ingestion remains future work; absent observations
correctly block new-season readiness. No manual progress writer was added.
Positive modern splits and races are local evidence; the owner legacy season and
all memberships/results/Team Locks remain intact. GENERAL ~0.85 s, overview ~3.36 s,
initial review ~0.91 s in one final sample; inherited overview latency stays in
Phase 14, without a broad performance refactor.

## Exact next step

Begin the separately atomic, already authorized **Package F** from fresh Git/remote
verification and a focused review of 029/030/035 finish/archive/Hall and accumulated
points contracts. Correct the champion source to final accumulated exact points;
two tied leaders require audited external BO3, three use authoritative adjusted
deaths. Preserve frozen Team Lock history and separate Cup Hall. Do not invent
residual tie/finalist policy. F has not been started in this E delivery.

Before any necessary F SQL, recheck actual history; **001-036 are immutable; 036 is
already applied**. Local gates, committed/pushed source and fresh complete remote
baseline must precede any migration/deployment. Never replay 031-036 or use owner
data for destructive validation. Preserve C/D/E; no broad audit or infrastructure
recreation. Do not start G automatically and **do not start Phase 11**.

Phase 10.5 retains independent F-M work and pending owner decisions. Whole-project
estimate remains **~80%**. Phase 11 **NOT READY / NOT STARTED**; no migration/cutover.

## F implementation entry - 2026-10-03

The new owner instruction authorizes one complete F package and then STOP. Entry
HEAD `dc326b38e8695af104745ef04b8cd1ec0e638c4f`, main/origin 0/0; tracked tree clean.
The protected untracked guide remains untouched. Fresh read-only remote evidence
in `%TEMP%/phase10-5f-entry-20261003` confirms 28 migration records through
036=`20261001165951`, owner identity/admin intact, 53 scoped tables captured,
Advisor 24 ERROR / 5 WARN / 125 INFO, Railway `6aa70f72` SUCCESS and Cloudflare
`3d829325` unchanged. No remote writes have occurred for F.

F is IN PROGRESS. New forward migration 037 implements exact accumulated points,
audited external BO3 for two tied leaders, fewer frozen adjusted deaths for three,
and unresolved residual/4+ ties. Finish certifies immutable title and historical
Team Lock; archive consumes that certificate separately. Existing historical
seasons receive no backfill. Finalist remains null/OWNER_DECISION_REQUIRED, which
does not block an otherwise proven champion. API/React focused tests pass;
real local PostgreSQL, complete closure and remote delivery remain pending.
Do not deploy this development checkpoint or start G/Phase 11.

### F local closure checkpoint - 2026-10-03

This supersedes the development-only gate above: **LOCAL GREEN / PUBLIC PENDING**.
680 Python, 14 React and 28 Edge PASS; compile, Ruff, Prettier, public build and
deployment dry-run PASS. New F PostgreSQL 17.11 runner: eight groups, fifteen
exact all-public rollback boundaries, 49-table restoration. Includes exact points,
unknown deaths, BO3 rights/replay/stale facts, correction/results/DQ/finish/archive
races, pre-F successful receipt replay, modern missing initial history and RLS/ACL.
Four fresh 001-037/bootstrap builds have 12,046 identical schema/grant/ownership
lines. 026-031 and B/C/D/E relevant regressions PASS with exact per-family cleanup.
Cup's old test marker was made schema-aware; no Cup production behavior changed.
The original regression wrapper still has a redundant local tail running; its
loaded pre-fix Cup assertion may fail and is not the final-source Cup evidence.
Fresh separate-process Cup L00-L08, ten races and nine rollback boundaries PASS.

Implementation and validators are ready for one explicit source commit/push.
Then take a fresh pinned V2 full/scoped baseline and Advisor baseline, apply only
committed 037 once, deploy Railway then Cloudflare and verify safe public reads,
typed absent-resource denials and exact owner/manual data preservation. No positive
remote title/BO3/finish/archive mutation is authorized for validation. No remote F
writes have happened yet. See [F report](../phase10-5f-completion-report.md) and
[local evidence](../phase10-5f-closure-evidence.json). Stop after F; no G or Phase 11.

### F remote delivery in progress - 2026-10-03

Source **6b466663edcf8e78922b956d7dd81b1408527fee** committed/pushed first, main/origin
0/0, tracked tree clean at migration time. A fresh baseline confirmed the pinned
V2 target, 28 prior records and 53 scoped tables. **037 applied once as
20261003121543**, HTTP 200; 29 records, all prior records identical. All 53 original
tables remain identical; the two new F tables are empty. Six helper and two private
immutable-table security checks PASS; Advisor 24 ERROR / 5 WARN / 131 INFO,
zero new ERROR/WARN. Owner stable Auth/credential facts and admin mapping match.
Evidence: `%TEMP%/phase10-5f-deployment-20261003`.

The committed-only 229-file API bundle was submitted to existing Railway as
**99af4814-dcfd-4a95-9c95-10984cc2b2de**; readiness not yet observed. Cloudflare F
deployment and public/final baseline gates remain pending. Never replay 037.
All local runners have ended and local PostgreSQL was stopped after verifying
zero other client sessions. The redundant old-process Cup marker assertion failed
as predicted, with exact cleanup; the fresh final-source Cup suite passed.

Railway **99af4814-dcfd-4a95-9c95-10984cc2b2de SUCCESS** subsequently observed,
source `6b46666`, image
`sha256:52760bc7fea074099c9be9c13050fbdeea6d0163085c79567e2477ac89c9cf08`.
Health 200 and new championship route 401 without JWT PASS before frontend deploy.
Cloudflare deployment **fba10b9a-60a9-4336-b1c2-17030d23b48a**, version
**cf4e1f2d-141b-44f0-ba67-40f17dae840b**, 100%, source `6b46666` then delivered.
Live asset equality, HTTPS/deep SPA/MIME/CSP/nosniff/CORS PASS. Safe authenticated
public validation is running; its outcome and independent final baseline remain
pending. Raw delivery metadata and public runner are under `%TEMP%/phase10-5f-*`.

### F complete checkpoint - 2026-10-03

**F DONE / STAGING_DONE_ZERO_RESIDUE.** This supersedes all earlier F pending
states. [Report](../phase10-5f-completion-report.md),
[closure evidence](../phase10-5f-closure-evidence.json),
[public evidence](../phase10-5f-public-evidence.json),
[security](../phase10-5f-security-advisor.json).

Entry **dc326b38e8695af104745ef04b8cd1ec0e638c4f**; final application source
**6b466663edcf8e78922b956d7dd81b1408527fee**, pushed before migration/deployments.
Documentation/evidence closure is the subsequent commit carrying this checkpoint;
get its exact HEAD from Git. Explicit staging only; protected guide untouched and
untracked, no published-history rewrite. Existing migrations 001-036 unchanged.

- Exact accumulated official points decide the title. Two leaders: audited external
  BO3. Three: fewer frozen authoritative adjusted deaths. Unknown/residual/4+ ties
  fail closed. Finalist null/OWNER_DECISION_REQUIRED does not block a proven title.
- Finish freezes title, points, official sources and safe historical Team Lock.
  Separate archive/Hall consumes the certificate. No live-save rewrite, invented
  Pokemon, new rewards/penalties or Cup change. Pre-F finished history is not
  reinterpreted; exact historical receipts still replay. Modern E history required,
  without consulting newer progress observations at finish.
- **680 Python / 14 React / 28 Edge PASS**. F eight PG groups and fifteen rollback
  boundaries; 026-031 and B-E regression gates PASS on final source. Exact 49-table
  restoration per family; four-build **12,046-line** schema/grant/ownership parity.
  Compile, Ruff, formatting, public build and dry-run PASS. Known stale loaded
  Cup assertion retained separately; fresh-source Cup proof is green.
- **037=20261003121543 exactly once; 29 migration records**. Do not replay 031-037
  or edit any applied migration. Two new private immutable tables remain empty.
- Railway **99af4814-dcfd-4a95-9c95-10984cc2b2de SUCCESS** and Cloudflare deployment
  **fba10b9a-60a9-4336-b1c2-17030d23b48a**, version
  **cf4e1f2d-141b-44f0-ba67-40f17dae840b**, 100%, both source `6b46666`.
- Public **phase10_5_public_reads_c802711156224562bcc86ecbd4a3b599 PASS**, exit 0:
  29 API requests, 22 real browser visits, no errors/interception/business writes.
  Owner championship is incomplete without a fabricated champion. Auth, read-only
  review and absent-resource/forged-body denials pass. Positive mutations are local
  evidence only. Live build assets and HTTPS/SPA/MIME/CSP/nosniff/CORS pass.
- Independent final **55/55 scoped table contents identical**, original 53 intact,
  **29/29 migration records unchanged** after apply. Owner identity/PIN/admin and
  all seasons/participants/results/Team Locks/manual data preserved. Only owner's
  Auth login/session activity excluded; full baselines plus separate stable
  identity/credential hashes retained. Storage metadata included, no byte writes.
- Advisor **24 ERROR / 5 WARN / 131 INFO**, zero added/removed ERROR/WARN. Six
  informational additions: private RLS tables/no policies and unused new indexes.
  Six helper/two-table ACL, RLS, fixed-path/invoker/immutability checks PASS.
- All task runners ended; local PG stopped after zero remaining client sessions.
  Public fixtures created: zero. Other unrelated processes remain UNKNOWN.

Performance sample: incomplete championship review 0.87 s, GENERAL 1.44 s,
overview 4.53 s. No per-player HTTP loop; Phase 14 retains overview latency and
representative complete-title review measurement. Full Launcher/cloud ingestion,
physical writes and broader shop repairs remain outside this package.

Unresolved owner decisions remain in the approved contract: finalist, residual/4+
championship ties, badge/completion rewards, normal lifecycle operator, future
game milestones, purchased-revive penalty, Team Lock cutoff, scouting scope and
League DQ/Cup eligibility. No unrelated package was started to resolve them.

**EXACT NEXT STEP: STOP.** Report F and await the next explicit owner instruction.
G is the next remaining package; do not begin it automatically. Phase 10.5 remains
IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**. No V1 migration,
shadow mode or cutover work is authorized by this completed F continuation.

## G authorized continuation — entry 2026-10-03, resumed 2026-10-04

The owner's subsequent Package G instruction supersedes the stop-after-F instruction
only for G. Finish G completely, then STOP; H and Phase 11 remain unauthorized.
Entry `b92b3dd26e182a288a4614e4bef61dade9fb8d43`, main/origin identical after fetch,
0/0 divergence, clean tracked tree. F's source and delivery remain unchanged.

Fresh read-only entry evidence: Supabase V2 `uwleqeuzsveqlugugzba`, 29 migration
records through 037=`20261003121543` once, 55 full/scoped tables, owner mapping and
enabled/admin identity intact. Advisor 24 ERROR / 5 WARN / 131 INFO. Railway
`99af4814-dcfd-4a95-9c95-10984cc2b2de` SUCCESS and Cloudflare deployment
`fba10b9a-60a9-4336-b1c2-17030d23b48a`, version
`cf4e1f2d-141b-44f0-ba67-40f17dae840b`, 100%, both source `6b466663`.
All 24 existing stats rows lack the new reserved metadata revision key.
Raw entry evidence: `%TEMP%/phase10-5g-entry-20261003`. Remote writes: zero.

Candidate 038 adds the owned absolute wipe counter command, using the existing
`revived_after_wipe` field and `metadata.wipe_revision` (absent means zero).
No new table/column or existing-row rewrite: historical source fingerprints are
preserved at migration. Real changes atomically increment revision, audit and
store an idempotency receipt; unchanged values preserve stats/fingerprint and only
store a receipt. The existing death arithmetic is promoted to bigint to cover the
full stored integer range. No purchased-revive rule or frozen snapshot changes.

API/UI and focused G tests are in progress. Four candidate migration/bootstrap
builds passed with 12,175 identical schema/grant/ownership lines and catalog/RLS
checks. This is candidate evidence, not G closure. Local PostgreSQL is running on
loopback port 55439; all fixtures are disposable local data. No G source commit,
remote migration or deployment has occurred. Exact next action: finish focused G
verification, full applicable final-source closure, commit/push, safe delivery and
final handoff. Do not claim G DONE before those gates.

### G local closure — 2026-10-04; delivery still pending

Implementation and complete applicable local gates are green. Own GET/PUT
`/v1/seasons/{season_id}/wipe-revivals` derives the participant from verified enabled
JWT identity. Strict absolute count, CAS, stable replay, audited real changes and
no automatic mutation retry. GENERAL contains the personal control, -0.4-point
explanation and pending-save notice. No Admin override, physical write, purchased
revive change, fabricated zero or historical recalculation.

[Closure evidence](../phase10-5g-closure-evidence.json): **694 Python PASS, 0 FAIL,
0 SKIP, exit 0; 22 React PASS; 34 Edge PASS including six G scenarios**. Edge is
retained unchanged-source evidence, verified against the saved full report and
current hashes; mobile screenshot reviewed. Compile, touched Ruff, TypeScript,
Vite production build, Prettier, Workers dry-run and diff check PASS.

Real PostgreSQL G: **nine groups, nine concurrent scenarios, three rollback
boundaries**; exact 49-public-table restoration. Full 026–030 and B/C/D/E/F
regressions PASS with exact per-family restoration. Four migration/bootstrap
builds retain identical **12,175** schema/grant/ownership lines and safe catalogs;
all SQL hashes still match. All 37 prior migrations are unchanged. No dedicated
Cup/shop rerun was needed: their implementation and purchased-revive semantics
are untouched; existing 029 compatibility cases passed.

Two unfinished G fixture issues were corrected (snapshot cleanup dependency and
missing required lifecycle timestamps). No product SQL was weakened. A resumed
attempt found PostgreSQL stopped before DB access; final whole G run is green.
Evidence distinguishes those attempts from the final gates. Local PostgreSQL was
stopped successfully after zero remaining client sessions.

Next action: commit/push this validated source, fresh remote baseline and Advisor,
apply only 038 once, then Railway and Cloudflare, safe authenticated reads and
exact data/security comparison. G is not DONE until delivery and final handoff.

### G preflight hardening and resumed local gate — 2026-10-04

Initial source checkpoint `a53a9421f53c029e510d5b0996aacd14eb5796a7` was pushed.
The fresh remote preflight stopped **before any migration POST**: hosted defaults
still granted authenticated TRUNCATE/REFERENCES/TRIGGER on `season_player_stats`,
although INSERT/UPDATE/DELETE were already denied. Unapplied 038 now explicitly
revokes those surplus capabilities and column write/reference privileges while
preserving existing RLS reads and backend service permissions. No remote data or
deployment changed. `%TEMP%/phase10-5g-deployment-20261004` retains the failed
read-only preflight. The next fresh delivery directory ends in `-final`.

All affected local gates are being repeated against this final hardening. Four
fresh builds again match; G reproduces hosted default grants before revocation.
A parallel rerun suffered native PostgreSQL exception `0xC0000005` and recovery;
Python separately printed 694 OK then exited `3221225477`. Neither is PASS.
Cause is UNKNOWN. Interrupted inherited databases were restored exactly across
all 49 tables from saved baselines; the focused fixture scope was cleaned without
touching seed rows. Recovery evidence: `%TEMP%/phase10-5g-crash-recovery.json`.

The subsequent isolated full code gate `phase10-5g-code-closure3` is PASS with exit
0, including all 694 Python tests. Sequential PostgreSQL families are running via
`%TEMP%/phase10-5g-sequential-pg.py`, evidence `*-closure3` and focused hardening
evidence. PostgreSQL remains running for these gates. Do not deploy or mark G DONE
until the sequential gates, second source commit/push and safe public closure pass.

### G final local hardening closure - 2026-10-05

All final-source local gates are now PASS. Full code closure3: 694 Python, zero
fail/errors/skips, exit 0; 22 React and 34 unchanged-source Edge PASS. Sequential
026-030 and B/C/D/E/F each restore all 49 public tables exactly. Four rebuilds
retain 12,175 identical schema/grant/ownership lines. All prior 37 migrations
remain unchanged. The final G run passes nine groups, nine concurrency scenarios,
three rollback boundaries and exact 49-table cleanup, exit 0.

An intervening G run had logged G01-G09 but lacked final cleanup/exit evidence;
it is not counted as PASS. Its known local fixture scope was removed. A later
native PG crash interrupted another run; Windows Event 1000 identifies local
libcrypto-3-x64.dll 3.5.7.0, exception 0xc0000005. The final unchanged-source G run
uses process-scoped OPENSSL_ia32cap=:0, a documented OpenSSL compatibility override.
This is a local environment mitigation, not a proven root cause or production
configuration change. Final evidence is `%TEMP%/phase10-5g-focused-portable-evidence.json`.
PostgreSQL was stopped after zero remaining clients. The closure evidence records
all interrupted attempts separately. No further local regression rerun is needed.

Fresh public preflight now passes: 29 migration records, 55 full/scoped tables,
owner identity/admin preserved, Advisor 24 ERROR / 5 WARN / 131 INFO. A transient
CLI read failed before any write; an independent identical read succeeded and
the complete baseline was recaptured in `%TEMP%/phase10-5g-deployment-20261005-final2`.
Railway and Cloudflare still serve F, as freshly observed. No G migration POST or
deployment has occurred at this checkpoint. Next: commit/push the validated
hardening, single 038 apply, Railway, Cloudflare, safe public read-only closure,
final report/handoff, then STOP before H/Phase 11.

### G remote apply checkpoint - 2026-10-05

Final hardening source `848e7b0177d26230315424d7edef9a6a3ca466af` is pushed.
**038 is now applied exactly once as `20261004222029`** (UTC migration version;
delivery date 2026-10-05 Europe/Madrid). All prior 29 records unchanged; 30 total.
Post-apply comparison: 55/55 scoped tables identical, zero wipe revision metadata
rows, two safe service-only helpers, stats RLS/read/service/owner preserved,
browser surplus capabilities revoked, zero added/removed Advisor ERROR/WARN.
Do not replay 038. Evidence: `%TEMP%/phase10-5g-deployment-20261005-final2/postapply.json`.
Railway G deployment `f21954a8-7624-4aaf-ad76-890469355878` was submitted from the
232-file committed API bundle. Backend completion, Cloudflare and public closure
are pending at this intermediate checkpoint; the final delivery section will
supersede it.

Railway subsequently reached SUCCESS with image
`sha256:b28ea95501afbe722845c996b3a325667fa570813ce97fbb1d3e992be20e1e20`;
health 200 and unauthenticated G route 401 verified before frontend deployment.
Cloudflare G deployment `7a7bdf65-0b40-4707-a199-2df331aff3e5`, version
`f356e801-af3e-452d-884b-0b133778c0dc`, 100%, now serves the same source.
Live build assets, HTTPS/deep SPA/MIME/CSP/nosniff/exact CORS PASS. The single
authenticated public read-only run and final preservation comparison remain in
progress; no further local test reruns are required.

## G delivered - 2026-10-05; STOP after G

This supersedes the pending-delivery notes above. **G DONE / STAGING_DONE_ZERO_RESIDUE.**
[Report](../phase10-5g-completion-report.md), [local closure](../phase10-5g-closure-evidence.json),
[public evidence](../phase10-5g-public-evidence.json), [security](../phase10-5g-security-advisor.json).
F remains DONE. Entry `b92b3dd26e182a288a4614e4bef61dade9fb8d43`; initial source
`a53a9421f53c029e510d5b0996aacd14eb5796a7`; final application source `848e7b0177d26230315424d7edef9a6a3ca466af`,
committed/pushed before any remote write. Documentation closure is a subsequent
commit: read exact final HEAD from Git, not a self-referential hash in this file.

- Own absolute counter GET/PUT uses enabled JWT ownership, strict integer/CAS,
  stable key/body replay and transactional audit/receipt. Existing adjusted-death
  formula (+2, -0.4 points each), no-op fingerprint and future freeze are preserved.
  Unknown save deaths stay unknown. No purchased-revive, physical-save, Admin
  editor or frozen E/day/F/Hall rewrite. Human personal control is in GENERAL.
- Full applicable final-source closure: **694 Python / 22 React / 34 Edge PASS**,
  zero Python fail/errors/skips, exit 0. Browser is retained unchanged-source PASS.
  Nine G groups / nine concurrent scenarios / three rollback boundaries, 026-030
  and B/C/D/E/F PASS, exact 49-table restoration. Four builds: **12,175 identical
  schema/grant/ownership lines**, safe catalogs/RLS, 37 prior migrations unchanged.
  Local PG stopped. Interrupted harness/native runs and local OpenSSL mitigation
  remain explicitly recorded; none is counted as successful evidence.
- **038=20261004222029 once; 30 remote migration records**, all prior 29 unchanged.
  No new table/column/default/backfill. Stats browser capabilities hardened; RLS
  reads/service rights/ownership preserved. Both touched helpers are service-only
  INVOKER with fixed search_path. Supabase preceded Railway, then Cloudflare.
- Railway **f21954a8-7624-4aaf-ad76-890469355878 SUCCESS**, source above, only 232 committed API inputs.
  Cloudflare **7a7bdf65-0b40-4707-a199-2df331aff3e5**, version **f356e801-af3e-452d-884b-0b133778c0dc**, 100%, same source.
  Backend health/new route auth, exact live build assets, SPA/HTTPS/MIME/CSP/
  nosniff/CORS verified.
- Public **phase10_5_public_reads_9a1a6007939d401299998b951ba432bb PASS**, exit 0: **37 API requests / 22 browser
  visits**, no interception/errors/business writes/fixtures. Owner PIN/JWT and
  own counter read pass. G write denials target a verified absent season only.
  Public mobile card reviewed. Positive wipe updates/concurrency/rollback remain
  LOCAL ONLY; owner counter was never changed to prove them publicly.
- Independent final **55/55 scoped tables identical**, **30/30 migration records
  unchanged** after apply, zero new tables and zero wipe revision metadata rows.
  Owner identity/PIN/admin, seasons/results/divisions/Team Locks/save facts/economy/
  Hall preserved. Full Auth captures plus stable owner credential/identity hashes;
  only owner login/session activity excluded from scoped equality. Storage
  metadata fully included; no Storage bytes touched.
- Advisor **24 ERROR / 5 WARN / 131 INFO**, zero new or removed ERROR/WARN.
  Exact raw delivery evidence: `%TEMP%/phase10-5g-deployment-20261005-final2` and
  `%TEMP%/phase10-5g-public`; no remote cleanup or pending operation remains.

One hosted sample measured own-counter read **0.78 s**, GENERAL **1.48 s** and overview **4.80 s**. Single staging observations only; Phase 14 retains overview
latency. No per-player HTTP loop or broad unrelated invalidation was introduced.
Existing owner decisions remain unchanged (economy/completion, lifecycle operator,
residual/4+ championship ties/finalist, purchased revive, Team Lock cutoff, scouting,
DQ/Cup and future milestones). None blocks G.

**EXACT NEXT STEP: STOP.** H (Team Lock warning + Team Preview/Battle parity) is the
next remaining package, requiring the next explicit owner continuation. No H work
has begun. Phase 10.5 IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**.

## H delivered — 2026-10-07; STOP after H

This supersedes G's next-step note. **H DONE / STAGING_DONE_ZERO_RESIDUE.**
[Report](../phase10-5h-completion-report.md), [local evidence](../phase10-5h-closure-evidence.json),
[public evidence](../phase10-5h-public-evidence.json).
Entry `9b7a8dce5953c852b104dc086c69ab689705ffe4`; final application source
`9ecf83d76bc570e88b494b548a3757f252220692`, committed/pushed before deployment.
The subsequent documentation closure HEAD is available from Git.

- Batallas/Team Preview: independent public spectator selectors, one battle
  selector with private details only for JWT self. Strict query/DTO boundaries,
  explicit missing-lock warnings, no live-save fallback or global League block.
  Existing Team Lock command/history, F Hall, Cup and G remain unchanged.
- Fresh **79 focused / 725 full Python, 29 React, 19 Edge PASS**, compile/lint/
  format/build/dry-run PASS. Full workspace includes 19 pre-existing untracked map
  tests, left unstaged. Local PG17.11: four security/projection groups, exact
  49-table restoration, stopped. Rebuild/parity and mutation matrices **NOT RERUN**:
  source/contracts unchanged; prior G evidence **HISTORICAL**.
- **No H migration. 30 remote records through 038 unchanged.** Railway
  `7886ed9c-eb63-4f97-8450-f8d129fa18d8` SUCCESS (234 committed API inputs), followed by
  Cloudflare `7545db42-055b-44fd-97ef-a069c8e77c4b`, version
  `51669d19-b5c6-49c0-b1b0-96a4fcbc01b3`, 100%; both use the application source above.
- Narrow public smoke: 11 API requests, six desktop/mobile browser states, no
  interception/errors/business writes. Missing own J2 lock verified publicly;
  positive private-lock/mutation proof LOCAL ONLY. Live assets/headers/CORS pass.
  **55/55 scoped tables and 30/30 migration records identical**, owner identity/
  credentials/admin preserved. Only own Auth session activity excluded from row
  equality; stable identity/credential hashes checked separately. Advisor unchanged
  24 ERROR / 5 WARN / 131 INFO, zero new/removed ERROR/WARN. No pending cleanup.
- Bounded preview sample 1.94–3.23 s; M/Phase 14 latency candidate. Team Lock cutoff
  and broader scouting remain undecided; no new rule. Protected/unrelated untracked
  files untouched. Raw evidence: `%TEMP%/phase10-5h-public` and `phase10-5h-*` logs.

**EXACT NEXT STEP: STOP. I is next, awaiting owner instruction.**
Phase 10.5 IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**.

## I entry — 2026-10-07; IMPLEMENTING

Owner explicitly authorized I (shop/economy) after H. Entry main/origin
`e3d4003337e4410dae46ebaa1de632696b1d80a9`, 0/0, clean tracked tree. Fresh remote
observation confirms H deployments above and 30 migrations through
038=`20261004222029`; evidence `%TEMP%/phase10-5i-entry`. No I remote writes.

New decisions: configurable defaults +4 per reliably observed badge, +12 once per
season/challenge for save-proven in-game Champion completion (not eight badges or
PokeApp finish). A purchased revive preserves one historical adjusted death and
must not duplicate that same still-visible death; G wipe semantics stay +2.

Directed implementation underway: exact wallet strings, pending/active promotions,
owned reward-voucher canje, completed-League spending with nullable matchday, reward
configuration/proof/deduplication and live purchased-revive overlap. Forward 039
is implemented but unapplied/uncommitted. Reader/3 emits native Champion proof;
automatic private rewards share the wallet lock and preserve unknown evidence.
Initial I PostgreSQL groups, 732 Python, 33 React and parser integration passed.
Final validation is still in progress: a Box-9 revive observation edge and
unlinked legacy revive UNKNOWN handling were added after those initial checks.
Required remaining: final SQL/rebuild parity, affected regressions, browser/static
gates, commit/push, safe remote DB/API/web delivery and closure. No cloud ingestion, physical writes,
frozen history rewrite, J or Phase 11. Protected/unrelated untracked files untouched.

### I local closure ? 2026-10-07; delivery pending

Supersedes the in-progress validation note above. Application implementation is
complete and locally green: 732 Python (713 committed-scope plus 19 pre-existing
untracked map tests), 33 React, 12 affected Edge; real parser/IPC/Launcher,
compile/lint/format/build/dry-run PASS. PostgreSQL I 10 groups / five rollback
boundaries; affected 022/024/025/026/E/G regressions PASS with exact 50-table
restoration. Four migration/bootstrap builds: 12,590 identical schema/grant/owner
lines. Sixteen invoker helpers, fixed search paths, private proof RLS/table/column
permissions checked. [Evidence](../phase10-5i-closure-evidence.json).

Fresh remote preflight: 30 records through 038; 55 scoped tables; owner credentials
and admin intact; Advisor 24 ERROR / 5 WARN / 131 INFO. Raw baseline in
`%TEMP%/phase10-5i-public`. No I remote writes yet. Next: commit/push this exact
source, apply only committed 039 once, compatible Railway then Cloudflare,
read-only owner smoke and independent final data/security comparison. I remains
IN PROGRESS until that delivery and documentation closure complete. STOP after I.

## I delivered - 2026-10-07; STOP after I

Supersedes I's pending-delivery notes. **I DONE / STAGING_DONE_ZERO_RESIDUE.**
[Report](../phase10-5i-completion-report.md),
[local evidence](../phase10-5i-closure-evidence.json),
[public evidence](../phase10-5i-public-evidence.json).
Entry `e3d4003337e4410dae46ebaa1de632696b1d80a9`; final application HEAD
`a5d1b627928d2e3fe05c90bcdb51851409e5687d`, committed/pushed before remote writes.
Documentation closure is the subsequent commit containing this entry; exact HEAD
is available from Git (no self-referential hash).

- Exact wallet strings, public pending/active promotions, owned reward-only voucher
  canje, eligible finished/archived spending without fictitious matchdays.
- Configurable defaults 4/badge and 12/season for observed in-game Champion proof;
  basic Admin controls delivered. Unknown is not zero; eight badges/PokeApp title
  cannot claim completion. Private audited claims, atomic delta/replay protection,
  current owned proof only, no manual attestation or automatic historical backfill.
  Reader/3 neutral Champion evidence; BW Hall-of-Fame proof rather than Ghetsis.
  Full Launcher/cloud ingestion remains unfinished; local sync is still local.
- Purchased revive keeps one historical death without stacking the same visible
  death. New death requires intervening observed alive state; ambiguous legacy
  overlap remains UNKNOWN. G factor two and frozen official history preserved.
- FRESH PASS: 732 Python, 33 React, 12 affected Edge, real parser integration,
  static/build/dry-run. PostgreSQL I ten groups / five rollback boundaries;
  022/024/025/026/E/G pass with exact 50-table cleanup. Four clean builds: 12,590
  identical schema/grant/owner lines. Full unrelated H/F/Cup matrices NOT RERUN.
  PostgreSQL stopped; no pending fixture cleanup.
- 039 applied ONCE as `20261007121317`; 31 total records, prior 30 identical.
  Railway `2402be29-d1ec-4e20-b4c4-3f218ee45893` SUCCESS, then Cloudflare
  `75e91cf3-123f-4fda-a836-a61e87c9b09f`, version
  `8f9deb86-8ebb-4b55-be52-4790ba8decf5`, 100%, same application source.
- Public: 18 successful API requests across pre/post-web checks, four final real
  browser states, mobile screenshots reviewed, no interception/business writes.
  Positive mutations LOCAL ONLY. All original 55 scoped tables unchanged, new
  proof table empty; final 56/56 tables and 31/31 migration records equal postapply.
  Owner credentials/PIN/admin/manual data preserved; only own Auth session activity
  excluded, full baselines and stable-credential hashes retained. Storage untouched.
  Sixteen helpers/private-table ACL verified. Advisor 24 ERROR / 5 WARN / 138 INFO;
  zero new/removed ERROR/WARN. Raw evidence `%TEMP%/phase10-5i-public` and I logs.
- Reward scope and purchased-revive decisions are resolved. Other decisions retain
  existing scope. Shop/inventory/overview latency remains M/Phase 14 work.
  Protected guide and unrelated untracked files remain untouched and unstaged.

**EXACT NEXT STEP: STOP. J is next, awaiting explicit owner instruction.**
Phase 10.5 IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**.

## J entry - 2026-10-07; IMPLEMENTING

Owner explicitly authorized J after I. Entry main/origin
`a973c914abd6ce7beb7eaf6dc303ccd4277481c6`, fetched 0/0, clean tracked tree.
I DONE VERIFIED from Git and latest handoff. Fresh pinned remote observation:
31 migrations through 039=`20261007121317`; Railway I deployment
`2402be29-d1ec-4e20-b4c4-3f218ee45893` SUCCESS, Cloudflare
`75e91cf3-123f-4fda-a836-a61e87c9b09f`, version
`8f9deb86-8ebb-4b55-be52-4790ba8decf5`, 100%, both I application source.
Raw entry evidence `%TEMP%/phase10-5j-entry`.

Directed impact map: READ Admin UI/API/models plus immediate setup, matchday,
lifecycle and Team Lock guards; WRITE Admin presentation/forms, readable status/
error/exception copy, affected client tests and documentation. No backend authority
or schema change is planned; no migration/rebuild is justified by the UI change.
Affected tests: configuration/current values/CAS/replay, eligibility-disabled
controls, explicit confirmations, human names/readiness, mobile and exceptions.
Unrelated Shop/Hall/Cup/Team Preview sporting matrices remain outside J.

New owner decisions are resolved: all eligible participants should operate normal
League lifecycle; 3+ title leaders use deaths then exceptional external resolution;
no Team Lock replacement cutoff; League DQ does not automatically disqualify Cup.
Current backend gaps are implementation gaps, NOT renewed owner-decision requests:
F only handles exactly-three death tie / two-player BO3, OPEN/CLOSE/FINISH are still
admin-only, and Team Lock overview cannot prove first-submission timing.
J will describe these accurately, preserve existing authorities and frozen history,
and document the scoped follow-up rather than add a broad authorization/title
migration. Safe existing Team Lock display is Fijado/Pendiente only.
No K or Phase 11. Owner/manual data and protected/unrelated files untouched.


## J local green - 2026-10-08; DEPLOY pending

Supersedes the implementing state above. Human Admin labels, actual current reward
values (including zero), integer validation, explicit version save, stale-source
review, lifecycle-disabled actions and named/reasoned confirmations are complete.
Pending/unknown commands retain the original body/key and a visible retry even
when a refreshed state has advanced or its read fails. App navigation controls are
held while unresolved; this is in-memory recovery, not durable cross-reload storage.
Browser history navigation is not a router-level blocker. No new server authority,
API, SQL, business mutation or frozen-history contract.

FRESH PASS: 732 Python (713 committed-scope plus 19 pre-existing untracked map tests),
25 focused Admin Python, 53 React, 33 unique affected Edge tests; TypeScript/public
build, formatting, deployment dry-run and diff checks pass. The initial Edge run
had two outdated test expectations; both affected files pass after checkbox/status
locator corrections (seven tests). No application change followed those gates.
[Local evidence](../phase10-5j-closure-evidence.json). Database rebuild/local PG and
unrelated full sporting matrices NOT RERUN because their contracts are unchanged.

Next: commit/push application and current contract, deploy only Cloudflare, run
narrow authenticated read-only Admin smoke, compare fresh owner/data/security
baselines, then write final report/handoff and push documentation closure. No K.


## J delivered - 2026-10-08; STOP after J

Supersedes J's pending-delivery notes. **J DONE / STAGING_DONE_ZERO_RESIDUE** for
its approved Admin UI scope. [Report](../phase10-5j-completion-report.md),
[local evidence](../phase10-5j-closure-evidence.json),
[public evidence](../phase10-5j-public-evidence.json).
Entry `a973c914abd6ce7beb7eaf6dc303ccd4277481c6`; application HEAD
`49d47906c3ca64880873bc15a093a8ece1e417a5`, committed/pushed before Cloudflare writes. Documentation closure is
the subsequent commit carrying this entry; obtain its exact final HEAD from Git.

- Human names/status/readiness/errors; actual current rewards including zero,
  strict integer validation, deliberate config save and stale-source review.
  Lifecycle guards and captured confirmations for consequential/exceptional actions.
  Unknown-outcome recovery retains body/key even after an advanced or failed read;
  navigation controls held while unresolved. Recovery is in-memory, not durable
  across accepted reload or browser history navigation.
- FRESH PASS: 732 Python (713 committed-scope + 19 pre-existing untracked map tests),
  focused Admin 25, React 53, 33 unique affected Edge, TypeScript/public build,
  formatting, dry-run and diff checks. Initial browser expectations corrected in
  tests only; seven affected cases pass. No repeated unrelated sporting matrices.
- No API/backend/SQL change, migration, replay, local PG or bootstrap rebuild.
  I's backend/DB contracts retain their prior evidence, not a new PG claim.
- Cloudflare `9fb756e2-aa1d-41bc-b406-292985ec0b7d`, version `2af2daab-5118-413b-abe4-f8f5985867ba`,
  100%, same application source. Railway `2402be29-d1ec-4e20-b4c4-3f218ee45893` remains SUCCESS
  at I source `a5d1b627928d2e3fe05c90bcdb51851409e5687d`. Live assets, HTTPS/deep SPA,
  MIME/CSP/nosniff, exact CORS and 401 boundaries pass.
- Final public smoke: six API checks and seven real Admin desktop/mobile states,
  no interception/page errors, no business writes/fixtures, reviewed screenshots.
  Initial private harness expected a disabled activation button where active seasons
  correctly hide it; corrected harness passes, application unchanged.
- Fresh 56/56 scoped tables and 31/31 migration records identical. Owner identity,
  PIN/credentials/admin, manual seasons/results/Team Locks/economy preserved.
  Full Auth baselines plus separately stable credential checks; only own login/session
  activity excluded. Storage untouched. Advisor 24 ERROR / 5 WARN / 138 INFO;
  zero new or removed ERROR/WARN. Raw evidence `%TEMP%/phase10-5j-public-final`.
- New owner rules are resolved. Implementation gaps: participant OPEN/CLOSE/FINISH
  authority; 3+ championship comparison and residual external decision beyond F's
  existing contract; reliable first-Team-Lock timing projection. League DQ does not
  cascade to Cup; linked draft/active Cup still blocks League exit. Do not reopen
  those product decisions. Undefined finalist/scouting/future milestones remain
  separately unresolved. See the alignment contract for the exact boundaries.
- No new N+1/per-player loop or wider invalidation. Final hosted setup 0.94 s,
  championship 1.47 s, overview 3.63 s; single samples, M/Phase 14 candidates.
  Protected guide and all unrelated pre-existing untracked files untouched/unstaged.

**EXACT NEXT STEP: commit/push this documentation closure and verify J DONE.**
The owner has queued K with autonomous end-to-end authorization once that gate
passes. Read its separate instruction only after closing J; no K work is included here.
Phase 10.5 IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**.


## K entry - 2026-10-08; IMPLEMENTING

J DONE VERIFIED at committed/pushed `37ac03294df8bac095e335abfe66098dcaa97b03`,
main/origin 0/0 and clean tracked tree. J's final remote observation immediately
precedes K: 56 preserved scoped tables, 31 migrations through 039, Advisor 24/5/138,
Railway retained I source and Cloudflare J source `49d4790`. This explicit queued
owner instruction supersedes the historical stop-after-J note for K only.

Directed impact: reuse H's current-day Team Lock reader with a single public
selection, add a narrower explicit scouting response and a read-only trainer surface.
READ H projections/DTO/API, shared read repository and direct SQL security fixtures;
WRITE scouting DTO/service/route, minimal H reuse, React trainer entry/screen/types,
focused privacy/browser/PG proofs and documentation. No SQL/migration expected.
Affected gates: public/private allowlists, spoofing, malformed snapshots, scope,
missing data, cache separation, H compatibility, real PG projection/RLS/grants.
Out of scope: parser/ingestion, sporting/lifecycle/Admin/Cup and timing redesign.

Public scouting scope is now RESOLVED: only competitive Team Lock species, nickname,
level, types, held item and moves. No live party/PC/dead-box/save/identity fallback;
self/admin remain public in this surface. Missing lock stays unknown, not six empty
Pokemon. Reuse existing roster/current-day semantics including frozen current locks;
no new eligibility/cutoff rule. No L or Phase 11.


## K local green - 2026-10-08; DEPLOY pending

GET `/v1/read/seasons/{season_id}/scouting` is a narrower adapter over H's reader,
with an internal single-public selection; no separate private projection or save
read. Explicit Pokemon allowlist: species/nickname/level/types/item/move names.
Only server JWT identity selects the viewer; all privacy override parameters are
forbidden. Null lock, absent day/roster and malformed input remain explicit/fail closed.
Entrenadores links to a named single-selector public surface; all selection caches
are separate from private battle/PC. Confirmed Team Lock changes invalidate only
this season's preview/scouting queries. Manual read refresh is available.

FRESH PASS: K 13 focused Python, full Python 745 (726 committed-scope plus 19 existing
untracked map tests), React 57, affected Edge 21, TypeScript/public build, compile,
Ruff, Prettier, Wrangler dry-run and diff checks. Real PostgreSQL 17.11: six H/K
projection/security groups, exact 50-table restoration, current 039 confirmed,
server stopped. No migration/bootstrap rebuild or unrelated full SQL matrices.
[Local evidence](../phase10-5k-closure-evidence.json). Fresh public baseline:
56 scoped tables, 31 migrations, Advisor 24 ERROR / 5 WARN / 138 INFO.
Next: commit/push, deploy only committed API bundle to Railway, verify compatible
read/auth, deploy Cloudflare, narrow read-only public scouting checks, final data/
Advisor comparison, then report/handoff closure commit/push. No L or Phase 11.


## K delivered - 2026-10-08; STOP after K

Supersedes K's pending-delivery notes. **K DONE / STAGING_DONE_ZERO_RESIDUE.**
[Report](../phase10-5k-completion-report.md), [local](../phase10-5k-closure-evidence.json),
[public](../phase10-5k-public-evidence.json). Entry J closure
`37ac03294df8bac095e335abfe66098dcaa97b03`; application HEAD `23081e146a8c00a57142242369161bc2b7e0f2c8`.
Committed/pushed before all remote deployment writes. Documentation closure is the
subsequent commit carrying this entry; obtain its exact HEAD from Git.

- Entrenadores named links/public selector, no scheduled-match dependency.
  GET scouting reuses H's current-day Team Lock reader with single-public selection.
  Exact Pokemon fields: species, nickname, level, types, item and move names.
  Self/admin stay public; no IV/EV/nature/ability/raw/identity/provenance/save/PC.
  Null lock/absent day/roster explicit; malformed sources fail closed. No old/live
  fallback, fabricated team, timing calculation or frozen-history rewrite.
- Query keys isolate sessions/seasons/selections from private Battle/PC caches;
  confirmed Team Lock updates refresh only this season's preview/scouting caches.
- FRESH PASS: K Python 13, full Python 745 (726 committed-scope + 19 untouched
  pre-existing untracked map tests), React 57, Edge 21; compile/Ruff/Prettier/public
  TypeScript/Vite build/dry-run/diff checks. PostgreSQL 17.11 six H/K privacy/security
  groups, exact 50-table restoration, current 039 verified, server stopped.
  No SQL/schema change; rebuild/bootstrap and unrelated full SQL matrices NOT RERUN.
- Railway `f11b0a8d-878e-49d6-923b-9df35dff8aef` SUCCESS, 236 committed API inputs only;
  verified new authenticated read before Cloudflare `7173a0cf-c746-46a8-b5ff-0a56e95cdc8b`,
  version `8cbde4f2-e51f-4c87-8056-61009d003538`, 100%, same application source.
  Live assets match; HTTPS/deep SPA/MIME/CSP/nosniff/CORS/auth PASS.
- Public: 12 API checks incl. authority-override/cross-scope denials; six real Edge
  desktop/mobile states, eight successful browser responses, no interception/page
  errors/business writes/private fallback, screenshots reviewed. Three sampled
  current locks absent; positive six-Pokemon proof LOCAL ONLY, no owner fixtures.
- Final 56/56 scoped tables and 31/31 migrations identical. Owner identity/PIN/admin,
  manual seasons/results/locks/economy preserved. Full Auth/Storage metadata included;
  only own session activity excluded and stable credential hashes checked. Storage
  bytes untouched. Advisor 24 ERROR / 5 WARN / 138 INFO, zero new/removed ERROR/WARN.
- Five bounded repository reads per current-day selection, no per-trainer loop or
  overview expansion. Hosted samples 3.51 s / 2.27 s / 2.23 s: M/Phase 14 round-trip
  aggregation candidate, not a load benchmark. Scouting scope now RESOLVED; J's
  lifecycle/championship/timing implementation gaps remain separate. Finalist and
  future game milestones retain their separate unresolved scope.
- Protected guide and unrelated ZIP/AI-map/validator files untouched and unstaged.

**EXACT NEXT STEP: STOP. L is next, awaiting explicit owner instruction.**
Phase 10.5 IN PROGRESS; **PHASE 11 READINESS: NOT READY / NOT STARTED**.


## L entry / implementation - 2026-10-08

Owner queued L after K; entry verified main/origin
`5f40737a02d209b6158b31f4598cf8b79c42080d`, 0/0, clean tracked tree.
K DONE VERIFIED. Fresh pinned remote inventory: 31 records through
039=`20261007121317`, so next forward migration is 040.

Small impact map: READ E/I parser/neutral progress, validation/reward helpers,
current frontend projections and their direct tests. EXPECTED WRITE current-game
read projection/API, Trainers/Saves progress presentation and focused evidence.
DB: one additive service-only read RPC reusing I source validation; no tables or
mutation contract changes. TESTS INVALIDATED: current progress projection/overview,
API scope, browser presentation, migration/bootstrap/security parity. OUT OF SCOPE:
new parser coverage, reward engine, cloud upload, physical writes, sporting history,
J's lifecycle/championship/first-lock timing implementation debts, M and Phase 11.

ALREADY SATISFIED BY CURRENT SOURCE: reader/3 neutral regional flags and nullable
Champion, BW Hall-of-Fame exception, E first-two-primary readiness, I configurable
idempotent badge/Champion rewards. L preserves all of them. Actual gap: public
progress cards used counts only (legacy defaults could masquerade as observations),
and no participant view exposed validated Champion completion. New read uses owned
current save plus latest identity revision in a single statement snapshot. Unknown
is explicit; regressions describe current save only, never rewrite rewards/history.
Full Launcher/cloud ingestion remains NOT CONFIGURED.

## L local green - 2026-10-08; deployment pending

040 adds only `observed_progress_read`, a bounded STABLE service-only SECURITY
INVOKER function with fixed search_path. It reuses `observed_save_progress` from I;
no applied migration changed. Current pointer, latest identity revision and owned
parsed save are joined in one statement snapshot. No row locks or reward settlement.
The overview uses this aggregate for every season instead of legacy default counts;
GET `/v1/read/seasons/{season_id}/progress` selects self from verified JWT and rejects
override/attestation parameters. Strict neutral validation plus public allowlists
exclude raw flags, hashes, identity and parser data. Badges in compatibility overview
counts remain primary-region; the new progress total includes both HGSS regions.
Trainers and Saves show regional earned/missing medals and nullable in-game Champion,
with observed-in-PokeApp timestamp; frozen competitive history is not recalculated.

FRESH PASS: L 11 focused Python; full 756 (737 committed-scope + 19 untouched
untracked map tests); React 63; affected Edge six, zero skipped/flaky. Native worker
and Launcher generated-fixture run: 77 PASS checks including BW Hall evidence.
PG 17.11 seven L groups, concurrent read replay, exact 50-table restoration; four
fresh migration/bootstrap builds yield 12,639 identical schema/grant/ownership lines.
Compile, targeted Ruff, TypeScript/public build, Prettier, Wrangler dry-run and diff
checks pass. [Local evidence](../phase10-5l-closure-evidence.json).
Native/parser/economy mutation contracts are unchanged. I's full reward race matrix
is RETAINED UNCHANGED-SOURCE; unrelated purchase/Cup/championship matrices NOT RERUN.
The previous temporary PG installation was incomplete; a new official EDB 17.11
portable install/new disposable cluster was used and is now stopped.

Fresh public baseline: pinned V2, 56 scoped tables, 31 migrations through 039,
stable owner credentials/admin; Advisor captured before any remote write.
Next: commit/push, apply only 040, verify history/data/security, deploy compatible
Railway then Cloudflare, safe authenticated progress reads and final comparison,
documentation closure commit/push. No owner progress/reward fixtures; no M/Phase 11.

## L delivered - 2026-10-08; STOP after L

Supersedes the pending-delivery note. **L DONE / STAGING_DONE_ZERO_RESIDUE.**
[Report](../phase10-5l-completion-report.md), [local](../phase10-5l-closure-evidence.json),
[public/security](../phase10-5l-public-evidence.json).
Entry K closure `5f40737a02d209b6158b31f4598cf8b79c42080d`;
application HEAD `94386d6c2fdceb5ac8625dbcc83648f469e027fa`, committed/pushed
before migration/deployment. Documentation closure is the subsequent commit
carrying this entry; obtain its exact HEAD from Git.

- E/I already provide the strict neutral regional badge and nullable Champion
  authority. Preserved reader/3 native Gen3/4/5 and BW Hall-of-Fame exception,
  first-two-primary E readiness and I idempotent configurable 4/12 reward semantics.
- L closes current participant display/reading: Trainers and Saves expose observed
  regional badges and in-game Champion true/false/unknown. Legacy default counters
  never prove zero. One bounded aggregate SQL read binds latest identity revision
  and current owned save; JWT self endpoint rejects overrides/attestation. No raw
  flags, hashes, private identity or parser details reach the progress UI. Unknown
  regional sets are null, observed zero is explicit, sparse badge identities persist.
  No new mutation engine, sporting decision, reward effect or historical rewrite.
- FRESH PASS: 756 Python (737 committed-scope plus 19 untouched untracked tests),
  11 focused L, 63 React, six affected Edge tests, 77 native/IPC/Launcher checks.
  PostgreSQL 17.11 seven groups, concurrent read replay and exact 50-table cleanup;
  four rebuild/bootstrap runs with 12,639 identical schema/grant/ownership lines.
  Static/public build/dry-run pass. New local cluster stopped. I mutation/race proof
  RETAINED UNCHANGED-SOURCE; unrelated sporting/shop purchase matrices NOT RERUN.
- 040 applied once as `20261008185548`; original 31 migration records unchanged.
  Railway `3a3ebb14-ba87-43e0-839a-639920d5f6bf` SUCCESS, 238 committed API inputs,
  source above; image `sha256:51726e531ade52deb7f42da196bb30fdd136cb33fa785cbf556c2015374dd6b0`.
  New authenticated read passed before Cloudflare `54102a24-2e0e-4fac-9519-3bf380888c88`,
  version `03e6250b-ee79-42bc-9aeb-e17363cf86d6`, 100%, same application source.
  Live assets, HTTPS/deep SPA/MIME/CSP/nosniff/CORS/auth PASS.
- Public: 10 API checks, four real Edge desktop/mobile states, eight successful
  browser responses, no interception/page errors; owner login/logout and mobile
  screenshots reviewed. All eight current participants are unknown; positive
  badge/Champion proof is LOCAL/NATIVE ONLY, without owner save/reward fixtures.
- Final 56/56 scoped tables identical and 32/32 post-apply history identical.
  Identity/PIN/admin/manual seasons/results/memberships/Team Locks/economy preserved.
  Full Auth baselines retained; only own session activity excluded, stable credentials
  compared separately. Storage metadata included, bytes untouched. Zero business
  writes/fixtures. Advisor 24 ERROR / 5 WARN / 138 INFO unchanged, zero new/removed
  ERROR/WARN. New function service-only grants/invoker/fixed search_path verified.
- Samples: self progress 1.424 s; overview 4.195 s, not a load benchmark. Existing
  overview round trips remain an M/Phase 14 candidate. No per-player HTTP loop or
  wider invalidation. Full cloud upload/installer and physical writes remain later.
- J's participant lifecycle, 4+/residual championship and first-lock timing debts
  remain IMPLEMENTATION GAPS, not missing owner decisions. Protected guide and
  unrelated ZIP/AI-map/validator files remain untouched and unstaged.

**EXACT NEXT STEP: STOP. NEXT M requires its own instruction.**
Phase 10.5 IN PROGRESS. **PHASE 11 READINESS: NOT READY / NOT STARTED**.

## M local validation - 2026-10-08; delivery pending

Owner's queued M instruction admitted after L DONE verification. Entry main/origin
`4a7537438ad19cdd6152d339b07caad4bd94de93`, fetched 0/0, clean tracked tree.
Directed read review only; [impact map and candidates](../phase10-5m-performance-candidates.md).
Inventory no longer loads overview for redemption names; the existing public names
list is enabled only while a redemption is open. Server target identity/eligibility,
exact economy, session isolation and mutation/invalidation behavior are unchanged.

FRESH PASS: 757 full Python (738 committed-scope plus 19 untouched untracked),
23 focused read tests, 63 React, five affected Edge cases, TypeScript/public build,
Prettier, targeted Ruff/compile, deploy dry-run and diff checks.
[Local evidence](../phase10-5m-closure-evidence.json). No backend/repository/schema
change; PostgreSQL/rebuild/native/unrelated mutation matrices NOT RERUN.

Fresh pinned Supabase baseline: 56 scoped tables, 32 migration records through
040=`20261008185548`; Advisor 24 ERROR / 5 WARN / 138 INFO. Railway remains L
`3a3ebb14-ba87-43e0-839a-639920d5f6bf`, Cloudflare still L before this delivery.
Three sequential samples of nine API reads and fresh desktop/mobile cold Shop
measurements captured. Cold Shop has three business reads / 30,060 decoded bytes;
the unnecessary overview is 17,525 bytes and 13 business repository calls.
Hosted response durations remain samples, not a benchmark. No owner fixtures.

Next: commit/push source, deploy Cloudflare only, repeat the same read measurements,
compare owner data/Advisor/history, close documentation and STOP. Final 10.5 product
alignment is next only after M; it and Phase 11 have not started.

## M delivered - 2026-10-08; STOP after M

Supersedes pending delivery above. **STATUS: M DONE / STAGING_DONE_ZERO_RESIDUE.**
**ENTRY CHECK: L DONE VERIFIED.** [Report](../phase10-5m-completion-report.md),
[local evidence](../phase10-5m-closure-evidence.json),
[public evidence](../phase10-5m-public-evidence.json),
[ranked candidates](../phase10-5m-performance-candidates.md).
Entry `4a7537438ad19cdd6152d339b07caad4bd94de93`; application source
`60367135c514ad0b8423c3051981137e2db420bf`, committed/pushed before deployment.
Documentation closure is the subsequent commit carrying this entry; read Git for
its exact HEAD rather than embedding a self-referential hash.

- Cold Shop now makes two business API reads instead of three; 30,060 → 12,535
  decoded response bytes. Removes 13 overview business repository calls. Names are
  one bounded public read on redemption intent. No client authority, per-target
  HTTP loop, mutation/invalidation change, new cache or private-data projection.
- Same method: three rounds of nine safe API reads before/after, all 54 return 200.
  Final browser desktop/mobile cold contexts: 3 → 2 business requests each, exact
  payload reduction; login-to-settled-API samples 11.202 → 6.713 s / 10.307 → 6.943 s.
  These include auth and harness wait, not render benchmarks. API unchanged.
- FRESH PASS: 757 Python / 23 focused reads / 63 React / five affected Edge;
  TypeScript/public build/Prettier/targeted Ruff/compile/dry-run/diff pass. Backend,
  repository, SQL and parser RETAINED UNCHANGED-SOURCE. PostgreSQL/rebuild/native/
  unrelated mutation matrices NOT RERUN / N/A, since their contracts did not change.
- Cloudflare `d9751374-7b4d-4468-aaf6-aaa7bdc50f04`, version
  `7e501a60-7fac-4fb0-a1f0-4a5181496a7f`, 100%, application source above.
  Live assets equal local build; HTTPS/deep SPA/MIME/CSP/nosniff/CORS/auth pass.
  Railway retained L `3a3ebb14-ba87-43e0-839a-639920d5f6bf SUCCESS`, source
  `94386d6c2fdceb5ac8625dbcc83648f469e027fa`. No API/DB deploy or migration replay.
- Independent final comparison: 56/56 scoped tables and 32/32 history records
  identical; 040=`20261008185548` once. Owner identity/PIN/admin/manual data and
  Storage metadata preserved; no Storage byte operations or remote business writes.
  Full Auth baselines retained, only expected own login/session activity excluded
  with credentials separately checked. Advisor unchanged 24 ERROR / 5 WARN / 138 INFO.
- Final real Edge smoke passed desktop/mobile with no page/API errors or mocking.
  Empty owner inventory means positive canje/name/retry proof is local only.
  Earlier harness timeouts and transient 503s remain recorded. First post-deploy
  mobile attempt had two 503s; unchanged-API recent logs also contain overview
  failures. Root cause UNKNOWN, not claimed fixed; availability is a Phase 14
  candidate. No product change was made to hide those failures.
- HIGH candidates: overview/Trainers breadth and inventory rival identity N+1.
  MEDIUM: Shop/scouting aggregation, Admin invalidation breadth, hosted 503
  observability. Exact refresh dependency locations and risks are documented.
- Final alignment still needs prospective simple Admin rules, cross-view visible
  freshness, visual trainer profiles, four Shop categories and concise UX. J's
  participant lifecycle, 4+/residual championship and first-lock timing remain
  implementation gaps, not missing owner decisions. Protected/unrelated files untouched.

**EXACT NEXT STEP: STOP. NEXT: FINAL 10.5 PRODUCT ALIGNMENT.**
Final alignment NOT STARTED. Phase 10.5 IN PROGRESS.
**PHASE 11 READINESS: NOT READY / NOT STARTED.**

## Final alignment admitted - 2026-10-08; IMPLEMENTING

Owner's explicit final-alignment instruction supersedes the stop-after-M note.
Entry `dd9b7b9bcf38491962ace956fd90e53fbfdd0670`, main/origin fetched 0/0,
clean tracked tree, M DONE VERIFIED. Fresh pinned V2 history: 32 rows through
040=`20261008185548`; next local forward migration is 041. No remote writes.
[Directed change map](phase10-5-final-change-map.md) records the seven authorized
areas and affected gates. Implement all, then one applicable final closure gate,
commit/push, migration/backend/frontend delivery, preservation evidence and report.
No final-alignment DONE or Phase 11 readiness claim yet. Phase 11 remains stopped.

## Final alignment local gate - 2026-10-08; VALIDATED / DELIVERY NEXT

All seven areas are implemented; [report](../phase10-5-completion-report.md) and
[local evidence](../phase10-5-closure-evidence.json) record the final contract.
763 Python, 74 React, 68 unique Edge cases; 16 PostgreSQL families each restore
53 public tables. Four fresh builds match (13,161 lines); 15 helper / three table
catalogs pass. New final flows have 12 rollback boundaries, extended F has 23.
All relevant static/build checks pass. Old test assumptions were corrected and
only affected browser files rerun. Native parser source/evidence retained unchanged.

041 is local only at this checkpoint. Remote preflight freshly pins V2, 32 records
through 040, 56 complete/scoped tables, intact owner credentials and Advisor
24 ERROR / 5 WARN / 138 INFO. Existing API L deployment and web M deployment were
reobserved unchanged. No remote business writes. Next: commit/push this source,
apply 041 once after fresh immediate comparison, deploy API then web, safe public
reads/screens and independent preservation/Advisor comparison, final closure commit.
Phase 10.5 not DONE yet; Phase 11 NOT STARTED.

## Final verified closure - 2026-10-08; PHASE 10.5 DONE

This entry supersedes the preceding intermediate state. **ENTRY CHECK: M DONE
VERIFIED. A–M + final product alignment DONE / STAGING_DONE_ZERO_RESIDUE.**
Entry HEAD `dd9b7b9bcf38491962ace956fd90e53fbfdd0670`; implementation/migration
source `25c59e42ba7b2ec1ecafdcd34f45b13f4afe3098`; final application/deployed source
**`eb4e402891cbaa02e0999229874ac3003e016ae0`**. The final source adds only the
reviewed division-label correction over the validated implementation. All sources
were pushed before their remote writes. Documentation closure is the subsequent
commit containing this entry; read Git HEAD for its exact hash.

[Report](../phase10-5-completion-report.md), [local evidence](../phase10-5-closure-evidence.json),
[public evidence](../phase10-5-public-evidence.json),
[Phase 14 follow-up](../phase10-5m-performance-candidates.md).

- Direct prospective reward editing with immutable server cutover; centralized
  viewer/season refresh and safe uncertain retries; visual public/self profiles;
  four Shop categories; eligible normal participant open/close/finish; 3+ championship
  deaths/residual audited decisions; immutable first-lock timing/no cutoff.
  Config/exceptions/archive remain admin. Cup and frozen historical truth retained.
- **041 applied once = `20261008204133`**, pinned V2 `uwleqeuzsveqlugugzba`;
  **33 migration records**, prior 32 unchanged. Three new private tables; no backfill.
  Do not replay 041 or any earlier migration. Final source migration is identical
  to the committed SQL applied from `25c59e4`.
- **763 Python / 74 React / 68 unique Edge PASS**; 16 real PG families restore
  all 53 public tables. New flow 12 rollback boundaries and extended F 23; four
  fresh migration/bootstrap builds match 13,161 lines. Fifteen helper / three private
  table catalogs pass locally/remotely. Relevant copy/profile reruns and production
  build pass. Native parser I/L evidence retained unchanged; no redundant native run.
- Railway **`2d71ec3b-095d-49a7-aa15-31749fe67b52` SUCCESS**, final source above,
  238 committed API inputs; image
  `sha256:fc59ebcab95dfab6cf4eee72a962dc22f06744a0c6beafb8ebbe984fd2f461e3`.
  Verified API before Cloudflare **`ea9c837d-86f0-4b0a-826d-a4774371b56e`**,
  version **`77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`**, 100%, same final source.
  Live assets match build; HTTPS/deep SPA/MIME/CSP/nosniff/CORS/auth PASS.
- Public 24 API checks and final 14 real Edge desktop/mobile states / 26 successful
  GETs PASS; no mocking/page errors/business mutations. Current rules 4/12; owner
  championship incomplete, team/progress unavailable rather than fabricated.
  Positive business mutations/populated Pokémon proof remain local only.
- First browser attempt completed all 14 states but had four recovered 503 reads;
  strict HTTP assertion failed. Preserved separately. One unchanged-source
  confirmation passed. Existing M availability candidate remains **ROOT CAUSE
  UNKNOWN / NOT FIXED**; no retries expanded and no failure hidden.
- Independent final **56/56 original raw table hashes identical**, three new empty
  tables, **59/59 post-apply scoped tables** and **33/33 history records** unchanged.
  Owner credentials/PIN/admin, manual seasons, memberships/results/locks and Storage
  metadata preserved. Full Auth snapshots retained privately; only expected owner
  login/session activity excluded, stable credentials compared separately.
  No Storage bytes or public fixtures; zero owner business writes. Advisor
  **24 ERROR / 5 WARN / 143 INFO**, zero added/removed ERROR/WARN.
- Local PostgreSQL stopped after all runners completed. No migration/deployment
  pending. Protected guide and unrelated untracked artifacts untouched; explicit
  staging only. Full cloud ingestion, physical writes, distribution and Phase 14
  remain later roadmap work. Finalist is still separately undefined.

**PHASE 11 READINESS: READY FOR REVIEW. PHASE 11 NOT STARTED.**
**EXACT NEXT STEP: STOP. NEXT: PHASE 11 READINESS REVIEW.** Await explicit owner
authorization before any V1→V2 migration, Shadow Mode or later phase.
