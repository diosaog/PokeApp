# Phase 10.5 — live execution record

Observation: 2026-09-29 Europe/Madrid. **IN PROGRESS; Phase 11 NOT STARTED.**
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

Remote validation state: **STAGING_UNVERIFIED** for the new behavior. On 2026-09-29,
`npx --yes supabase migration list --linked` exited 0 and verified 24 records,
031=`20260928110301`, latest 032=`20260928111840`; the linked project-ref is exactly
`uwleqeuzsveqlugugzba`. No migration/schema/data write. Fresh baseline/Advisor and
actual deployment checks still required before remote delivery. Never replay 031/032.
Historical backend source `6d2c66a` / frontend `3c83a16`; verify actual resources
before deploying, using [existing runbooks](../../deploy/README.md).

Preserve owner active season `c6bcac5b-0b89-403f-8242-41ac58286ade`, other manual
seasons and Anto's current staging identity/PIN/admin. No fixture cleanup is
authorized for those records. Use local disposable PG if active-season guards
prevent staging tests. Prior delivery reports retain their historical results.

No remote fixture process started in this phase. Local B PostgreSQL/process state
is recorded in the evidence section; inspect actual processes before resuming.
Unrelated processes/remote operations not inspected: UNKNOWN.

## Alignment matrix and progress

| Package / finding verified against entry source | Classification | State |
|---|---|---|
| A: entry, contract, resumable memory | FIX NOW | DONE, published `226ac7b`. |
| B: League lacked primary GENERAL; existing 030 points view is authoritative | FIX NOW | GREEN LOCAL, source publication in the B commit containing this update; remote application/deployment pending. |
| C: ordinary results use admin routes/SQL authority | FIX NOW | Next implementation package. |
| D: two-way daily tie uses H2H before deaths; slug total order influences outcomes | FIX NOW | Pending C. |
| E: 026 requires initial manual A/B before activation | FIX NOW | Pending D; manual readiness must remain explicit. |
| F: 029 lifecycle reads final daily snapshot positions for title | FIX NOW | Pending E; structural Phase 11 blocker. |
| G: wipe counter exists in stats but lacks owned command/UI | FIX NOW | Pending F. |
| H: Preview only selects scheduled match; missing-lock presentation insufficient | FIX NOW | Pending G. |
| I: pending promotions hidden by public view; voucher canje absent in React; purchases require active season | FIX NOW | Pending H. |
| J: Admin displays technical readiness keys and ordinary results | FIX NOW | Pending I. |
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

## B delivered implementation — remote delivery pending

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

No fix to title certification, sporting ties, self-service results or initial A/B
is claimed. Those remain C–F. No owner decision was invented.

## Evidence ledger

- A, entry source above, Windows local: Git branch/HEAD/remote/status inspection
  and fresh fetch PASS. Document links and `git diff --check` are the A gate;
  no code/database test is claimed for this documentation-only block.
- Historical Phase 10: 565 Python, 11 React and nine browser tests at the commits
  recorded in its report, not rerun or claimed as Phase 10.5 evidence.
- No new migration applied remotely, staging mutation, deployment or remote fixture cleanup.

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

## Continuation and delivery order

After B is committed/pushed, next implementation is **C: participant result entry**.
Read `app/api/routes/matchdays.py`, application/repository matchday boundaries,
027/028/030 and focused matchday fixtures. Add a participant path using verified
identity and active eligibility, preserving CAS/idempotency, with separate existing
closed-day admin correction. Normal input goes to League/Battles; test outsider,
disabled/inactive, third-party participant, stale/replay/edit/closed denials.
Use a new forward migration after verifying actual local/remote history; never
edit published 033 or older SQL. Publish C before D.

033 is **not applied remotely** and the new API/UI are **not deployed**. At the next
coherent deployment checkpoint, fresh target/history, baseline and Advisor checks
must precede applying committed pending SQL, then Railway API, then Cloudflare UI.
Preserve owner active season; use local mutation gates and read-only public checks.
Do not deploy the new frontend against an API/database without its read contract.
M performance notes: GENERAL is one aggregate RPC, no per-player HTTP reads.
Existing daily overview, broad mutation invalidation and auth mapping remain Phase 14
candidates; no globally reduced request count or production timing is claimed.

Exact next step after B publication: implement C under the bounds above. Maintain
this record after each green atomic block. Project estimate remains ~80% pending
verified public delivery; Phase 11 NOT READY and not authorized to start.
