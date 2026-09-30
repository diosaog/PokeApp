# Phase 10.5 — live execution record

Observation: 2026-09-30 Europe/Madrid. **IN PROGRESS; Phase 11 NOT STARTED.**
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
verified B+C deployment below. **Current status: B and C DONE, publicly deployed.**
Current migration history has 26 records through 034. Never replay 031-034.

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
| D: two-way daily tie uses H2H before deaths; slug total order influences outcomes | FIX NOW | Next package; not started. |
| E: 026 requires initial manual A/B before activation | FIX NOW | Pending D; manual readiness must remain explicit. |
| F: 029 lifecycle reads final daily snapshot positions for title | FIX NOW | Pending E; structural Phase 11 blocker. |
| G: wipe counter exists in stats but lacks owned command/UI | FIX NOW | Pending F. |
| H: Preview only selects scheduled match; missing-lock presentation insufficient | FIX NOW | Pending G. |
| I: pending promotions hidden by public view; voucher canje absent in React; purchases require active season | FIX NOW | Pending H. |
| J: Admin displays technical readiness keys | FIX NOW | Ordinary result UI moved in C; remaining wording pending I. |
| K: minimal public projection from permitted published facts | FIX NOW | Pending J; wider scope blocked below. |
| L: legacy exports badges; neutral Phase 9 parser lacks observed progress | FIX NOW | Minimal contract pending K. |
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
No D code or Phase 11 started. [Public evidence](../phase10-5bc-public-evidence.json),
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

## Exact next step

**Package D: daily sorting and relevant unresolved ties.** Read the contract,
`app/domain/services/league.py`, matchday planning/027 and focused competition tests.
Daily wins then fewer adjusted deaths; remove H2H-first and alphabetical sporting
resolution, preserve frozen snapshots, CAS/replay and close/correction safety.
Any SQL change needs new forward **035** after verifying actual history. Do not
replay 033/034 or alter manual owner results to make fixtures pass. Unresolved
owner rules remain unresolved; do not infer championship tie policy.

C is a complete atomic checkpoint. No D code has started in this block. Phase 10.5
remains IN PROGRESS (D-L independent work and decisions remain), whole project
estimate ~80%; Phase 11 **NOT READY / NOT STARTED**. Final documentation is in its
own commit; obtain its hash from Git. Check fresh status/refs before continuing.
