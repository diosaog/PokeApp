# Phase 10.5 — live execution record

Observation: 2026-10-03 Europe/Madrid. **E DONE; Phase 10.5 IN PROGRESS; Phase 11 NOT STARTED.**
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
| F: 029 lifecycle reads final daily snapshot positions for title | FIX NOW | Next authorized atomic package, NOT STARTED; structural Phase 11 blocker. |
| G: wipe counter exists in stats but lacks owned command/UI | FIX NOW | Pending F. |
| H: Preview only selects scheduled match; missing-lock presentation insufficient | FIX NOW | Pending G. |
| I: pending promotions hidden by public view; voucher canje absent in React; purchases require active season | FIX NOW | Pending H. |
| J: Admin displays technical readiness keys | FIX NOW | Ordinary result UI moved in C; remaining wording pending I. |
| K: minimal public projection from permitted published facts | FIX NOW | Pending J; wider scope blocked below. |
| L: legacy exports badges; neutral Phase 9 parser lacks observed progress | FIX NOW | E provides the observed badge foundation; remaining L review pending K. |
| M: overview has about 13 sequential reads; command invalidation is broad | FIX NOW | Guard every touched package; record Phase 14 work. |
| Ten unresolved rules listed in contract | OWNER_DECISION_REQUIRED | No answers inferred; defer dependent branches only. |
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
