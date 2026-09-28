# Phase 8L delivery report — Cup engine / certification (open)

Started: 2026-09-24. Evidence reconciled: 2026-09-26.
Technical audit and local finalization correction: 2026-09-28; remote delivery remains open.
Starting HEAD `87a98f5`, branch `main`, origin 0/0 at phase start.
Baseline: 466 unit tests, migrations 001–030, complete-project estimate ~68%.
030 already deployed as `20260924102756` and `20260924103256`; never replayed.

This existing file is the technical implementation/evidence report, retained at
its original path for continuity. Its filename is not a DONE claim. The
[live handoff](work-in-progress/phase8l-live-handoff.md) alone maintains current
operational state, Git changes and the next action. Follow the canonical
[MultiIA protocol](AI/PokeApp_Multi_AI_Continuity_Protocol.md).

## Delivery status

The 2026-09-28 finalization task corrects A8L-01 and related historical eligibility
gaps. The focused 45-test suite, general 511-test suite and current local SQL
validation pass. The fresh release rebuild and resumed regressions are complete,
including final schema/security/cleanup checks. **Local gates are complete;
delivery is READY FOR STAGING, not DONE.** Management access is the remaining
blocker to remote preflight and validation. No historical migration is changed.

A fresh read-only request to the pinned V2 PostgREST endpoint returns HTTP 200,
but its exposed schema contains neither the 031 tables nor its Cup RPCs. This is
not migration-history, schema/grants or Advisor verification. Management access
is unavailable; the Supabase integration has been suggested but is not confirmed
connected. No remote writes, migrations or fixtures were started by this task.

Authoritative contract: [Cup engine](phase8l-cup-engine.md). The reduced scope is
Swiss + Top 4, elimination and doubles RR + Top 2/Bo3 final, with focused tests.
No tournament framework, solver, Elo, extensive fuzzing, visual work or Phase 9.

## Implementation

Eleven typed FastAPI routes: nine admin mutations and two safe reads. Verified
enabled JWT/admin authority, Cup CAS, canonical receipts, explicit start/results/
round close/correction/DQ/discard/finalize. Pure deterministic server engine plans
from a database snapshot; one service-only commit RPC rechecks its fingerprint
under compatible season/player locks. No client plan or automatic mutation retry.

031 adds typed side members, rounds, numeric Bo3 scores, ranking inputs, append-only
command history and immutable certification. Singles and doubles champion/finalist
are side identities; both doubles members are retained. The existing Hall supports
multiple Cups per category/season while retaining League/legacy uniqueness. The
public Hall includes Cup/certificate provenance and frozen members. Pokemon team
is empty because no authoritative Cup Pokemon team source exists.

Post-League Cup operation preserves League snapshots, rewards, movements, Hall,
archive JSON/checksum and the frozen pending-Cup marker. Ambiguous imports remain
uncertified. Draft/active cancellation is logical; DQ never changes League status.
Browser table/column DML and inherited TRUNCATE are revoked, including view paths.

## Validation ledger

These are dated local observations, not new executions during the documentation
task and not a current staging certification.

| Check | Evidence inspected on 2026-09-26 | Result / limit |
|---|---|---|
| Unit suite, baseline plus focused engine/API coverage | `%TEMP%/pokeapp-general-review-unit.log`, 2026-09-26; `tools/run_unit_tests.py` | **501 tests, OK**, exit 0 recorded in preceding context review; no skipped tests reported |
| Compile | Preceding context review: `py -m compileall -q app tests tools` | PASS; not rerun for these document edits |
| Local PostgreSQL release | `%TEMP%/phase8l-release.log`, 2026-09-24 | Ends `Cup release RESULT ok; final local gate complete`; historical evidence, not a newly executed gate |
| Migrations 001–031 / bootstrap | Release log and preserved schema dumps | Rebuild and **10,515 normalized lines** of schema/grants/ownership parity recorded; current copies of both dump files have identical SHA256 |
| Inherited browser grants | Release log | Revocation checks PASS locally |
| 026–030 regressions | Release log | Setup 17, matchdays 20, participant status 24, lifecycle 19, trials 8 groups PASS |
| Cup flows and concurrency | Release log | L01–L06 and ten race families PASS in that run |
| Cup rollback | Release log | Nine all-public-state rollback boundaries and fixture cleanup PASS in that run |
| Real staging JWT/API/PostgREST, cleanup and Advisor delta | No 8L completion evidence available | Pending verification/delivery; no deployed public API claim |

Source provenance: implementation commit `d38b871`; inspected repository HEAD
`bc419ba`. Cup implementation/test/validator/migration paths have no intervening
diff between these commits. However, the SQL release log predates that commit and
does not record its source commit or complete working-tree fingerprint. Preserve
its PASS evidence without claiming a freshly reproduced gate against current HEAD.
The next executor must reconcile any relevant source/harness changes before
reusing a result; rerun only checks justified by an evidence gap or change.

The context audit found trailing whitespace in the handoff, so its earlier
`git diff --check` PASS was stale. The document-only reconciliation removes that
defect; its final document checks belong in the live handoff, not in the SQL ledger.

Ten race families: starts; results/results; results/close; closes; correction/close;
correction/finalize; DQ/results; discard/finalize; finalizes; Cup finalize/League
finish plus consistent certificate read. Separate DB sessions/HTTP clients.

Local rollback after initial pairings, standings, successor round, DQ status,
DQ advancement, certificate, Hall, event and receipt compares every public table's
full ordered rows. No failure DDL is sent to staging.

## Technical audit 2026-09-28

Audited HEAD: `73f8453668a7eae6d4f7cfc400f80b15f8b147b2`, matching remote
`main` when checked on 2026-09-28. Implementation, tests, tools and SQL are unchanged
from `d38b871`. The audit began on 2026-09-26 and resumed on 2026-09-28 after an
interruption. No implementation or migration source was changed; no staging
operation was performed. **At audit completion one important integrity defect
remained open; its subsequent correction is recorded in the finalization section.**

### Audit evidence

| Check | Result and scope |
|---|---|
| Focused unit/API suite, 2026-09-26 | `tools/run_unit_tests.py --pattern 'test*cup*.py'`: 35 PASS; `%TEMP%/phase8l-technical-audit-unit.log` |
| Representative in-memory scenarios, 2026-09-26 | 15 completions PASS: Swiss 5/6, elimination 5, doubles 3/4, each with DQ before round 1, after round 1, and after round 1 plus correction |
| Current SQL fixture suite, 2026-09-28 | `tools.validate_supabase_v2_cups_sql` against loopback-only `pokeapp_v2_validation_phase8l_audit_20260926`: L00–L06, ten race families and nine rollback boundaries PASS, exit 0; `%TEMP%/phase8l-technical-audit-sql.log` |
| Additional Cup/sanction concurrency | Finalize versus coin reduction + Store Ban: both committed once; Cup standings unchanged, one certificate, exact -10 ledger and active ban; `%TEMP%/phase8l-audit-sanctions-race.json` |
| Certification corruption probe | Confirmed defect A8L-01 through the production adapter and real local SQL; `%TEMP%/phase8l-audit-certification-repro.json` |
| Local cleanup / schema | All 46 public tables have the same row counts and full-row content hashes as before audit fixtures. Normalized public schema/grants/ownership also match the preserved release dump; `%TEMP%/phase8l-audit-cleanup.json` |
| Deployment probes | TestClient with an empty container: `/health` returns 200/OK; cross-origin OPTIONS returns 405 without an allow-origin header. These are deployment limitations, not evidence of a deployed API; `%TEMP%/phase8l-audit-deployment-probes.json` |

The SQL database was cloned from the existing local validation database after
checking its schema against the preserved release dump. This was a focused run
against the current harness, not a fresh full migration/bootstrap rebuild or a
real Supabase JWT/PostgREST run. The local PostgreSQL server was stopped afterward.
No final 8L delivery or fresh full 501-test run is claimed.

The additional combined sanction probe initially failed cleanup with FK error
23503 because it used the Cup-only cleanup chain for judicial rows. The audit
recovered using the existing judicial dependency order, scoped to that probe's
exact season/trainer identities, then independently verified the full baseline.
This was a probe-cleanup error, not a failed concurrent business operation; no
fixture residue or product change remains. The SQL log is PowerShell UTF-16.

### A8L-01 — important: certification accepts impossible eligibility

Reproduction in the isolated local database:

1. Create and play an ordinary four-player elimination Cup through its closed final.
2. Before certification, inject inconsistent data locally by setting only the final
   round's `eligible_side_ids` to `[]`. Keep the completed Bo3 and its two entrants.
3. Call the normal `finalize` operation through `SupabaseCupRepository`.
4. Observed: state becomes `finished`, a certificate and Hall entry are created,
   and the certificate snapshot retains the empty final eligibility array.

Expected: reject the inconsistent graph and create neither artifact.

Cause: [engine validation](../app/domain/services/cup_engine.py) reconstructs
pairings/positions but does not require the participants of a `completed` match
to belong to that round's frozen eligible set. It can accept a completed match
where reconstruction would produce an automatic result. The
[031 finalize check](../supabase/v2/migrations/031_cup_engine_certification.sql)
checks the closed final and winner/finalist relationship, without closing this gap.
The existing corruption tests cover advancement and standings, not this invariant.

Impact: a corrupt/imported/backend-written graph can acquire an official Cup
certificate and Hall entry. The reproduction requires privileged/local data
corruption; no path from ordinary allowed HTTP commands or browser grants was
found. This is an integrity validation defect, not a demonstrated privilege bypass.

Before final delivery, add the narrow eligibility validation and focused negative
tests through the engine and SQL/adapter path. Preserve legitimate DQ after draw:
an already played match must be checked against eligibility at that round's draw,
not against the player's final/current status. Review the SQL final check for the
same invariant. No fix was applied during this audit.

### Integration and future boundaries

- League/archive/Hall: the local flows preserve frozen League data after finish
  and archive, retain the archive's pending-Cup marker, and create separate Hall
  entries for multiple Cups and both doubles members. Rollback covers Hall and
  certificate atomicity. A8L-01 is the remaining certification-integrity defect.
- Participants/identity: same-Cup/season/player FKs and explicit entry/start checks
  are present. The conservative 028 doubles dependency is deliberately retained;
  it can block League withdrawal for players outside a live doubles Cup. That is
  approved behavior, not newly classified as a Cup defect.
- Sanctions: the additional concurrent coin/Store Ban test passes. Cup ranking
  intentionally does not consume League point penalties or shop bans.
- Team Lock/Pokemon identity: inspected boundaries do not invent Cup Pokemon
  teams or perform save writes. Cup Hall team snapshots remain empty. No new
  Cup-versus-Team-Lock/identity-worker race was executed in this audit.
- Future React/Launcher consumers must use the 8L side/member identities. The
  older `app/domain/cup.py` uses `single_elimination`, whereas the new API uses
  `elimination`; the older Hall DTO requires a single trainer champion, whereas
  doubles Hall uses a side and nullable `champion_trainer_id`. Do not reuse those
  legacy DTOs without an explicit adapter. No current 8L route uses them.
- Deployment: configure CORS if frontend/API use different origins, and verify
  migration/backend readiness independently of the current liveness-only health
  endpoint. API deployment and real staging verification remain pending.
- Optional later optimization: the Cup list SQL builds full Cup documents before
  stripping rounds/sides/standings. A lightweight summary query or pagination can
  be added when actual usage warrants it; it is not a blocker for this small Cup.

## Finalization correction and evidence — 2026-09-28

Entry HEAD was `73f8453668a7eae6d4f7cfc400f80b15f8b147b2`, independently matching
remote main. The audit edits to this report and the live handoff were preserved.
The tested correction and evidence were committed and pushed as
`39343ea2add1591826d0809cd7c3c42ec814043c`; fresh remote main matched and divergence
was `0 0`. The final documentation follow-up changes no tested implementation.
The following results were executed against that source plus the correction in
this delivery, on Windows with `.venv-api/Scripts/python.exe` and local PostgreSQL
17.11 at `127.0.0.1:55439`. `%TEMP%/phase8l-finalization-source.json` records SHA256
for the engine, tests, validators and unchanged 031 source. Commands below are
repository-relative; all local databases use the `pokeapp_v2_validation` prefix.

### Integrity correction

- **A8L-01 fixed:** a completed match must reconstruct as `scheduled` at that
  round's frozen draw. An automatic bye/forfeit/void cannot be certified as a
  played match. Both finalists, and every earlier completed match, are checked.
- Related automatic-result gaps fixed: a bye/forfeit winner must be eligible at
  its draw; a forfeiting/void side cannot still be eligible at the next persisted
  draw. A DQ several rounds later can no longer justify an earlier invented
  automatic result. Current active sides must remain a subset of the final draw.
- Completed matches use their historical draw eligibility, never current player
  status. A later DQ preserves played results, including the final loser. Closed
  automatic results are also preserved when their winner is disqualified later.
- Corrections can recreate an unplayed successor after DQ. Its eligible set is a
  bound on historical eligibility, not a command to recompute earlier results
  using current status. Pairings, scores, advancement, identities, final and
  standings continue to be reconstructed and checked under the existing rules.
- API rejection is HTTP 409 `INVALID_RESULTS` (or the existing roster/graph
  rejection for its respective invariant). The adapter does not call the commit
  RPC after rejection. The supplied authoritative context is not mutated.

No other delivery-blocking defect was found in the bounded review of finalize,
Hall derivation, cancellation, corrections, multiple Cups, doubles and post-League
operation. No new feature, DTO rule, endpoint or tournament format was introduced.

### SQL / migration decision

**031 and all historical migrations remain byte-for-byte unchanged; no new
migration is needed for this correction.** The approved 027/031 boundary places
full graph reconstruction in the trusted backend planner. HTTP bodies cannot
supply plans; browser roles cannot call the context/commit helpers or write Cup
sources. `api_admin_cup` calls `cup_begin`, takes the shared locks, rechecks the
complete context fingerprint and revision, then checks final provenance and
atomically writes certificate, Hall, history, event and receipt. A graph changed
between validation and commit is rejected as stale; production does not retry.

The old SQL final check alone is not a complete graph validator. It is sufficient
in combination with the corrected mandatory application validator for the
approved API. Arbitrary plans submitted directly with privileged service-role
credentials are outside that boundary; service-role holders already have direct
table write authority. This is not a claim that SQL independently reconstructs
the whole competition. The real adapter/SQL rejection, browser ACL checks,
concurrency and rollback checks exercise the actual combined boundary.

### Current validation ledger

All observations in this table are from **2026-09-28**. `psql` below means
`%TEMP%/pokeapp_pg17_phase8c_20260922/portable/pgsql/bin/psql.exe`.

| Command / check | Result | Evidence under `%TEMP%` |
|---|---|---|
| New focused regressions against the old engine, `tools/run_unit_tests.py --pattern 'test*cup*.py'` | Expected failure (exit 1); demonstrated missing eligibility and automatic-result checks before implementation | `phase8l-finalization-red.log` |
| Isolated original-engine SQL reproduction through `SupabaseCupRepository` | A8L-01 accepted: FINISHED, one certificate, one Hall. Exact cleanup across all 46 public tables PASS, exit 0 | `phase8l-finalization-sql-red.json` |
| `tools/run_unit_tests.py --pattern 'test*cup*.py'` after correction | **45 tests PASS**, exit 0 | `phase8l-finalization-unit.log` |
| `tools/run_unit_tests.py` | **511 tests PASS**, no skipped tests, exit 0 | `phase8l-finalization-full-unit.log` |
| `-m compileall -q app tests tools` | PASS, exit 0, repeated before publication | `phase8l-finalization-static-checks.json` |
| `-m tools.validate_supabase_v2_cups_sql --psql <psql> --database pokeapp_v2_validation_phase8l_finalization_probe` | **L00–L08, ten race families, nine exact rollback boundaries PASS**, exit 0. All 46 public tables exactly equal to baseline after cleanup | `phase8l-finalization-sql.log` |
| `-m tools.validate_supabase_v2_cup_release --psql <psql> --database pokeapp_v2_validation_phase8l_finalization --allow-destructive-reset` | Both migration/bootstrap rebuilds twice, catalog/RLS and 10,515-line schema/grants/ownership parity PASS. Setup 17 and matchdays 20 groups PASS. Interrupted during participant regression; no final exit/result from this attempt | `phase8l-finalization-release.log` |
| Interruption recovery using `ParticipantStatusFixtures.cleanup` scoped to the exact run | Two seasons / seven trainers removed; all other full rows in all 46 public tables unchanged, schema parity and catalog rechecked, exit 0 | `phase8l-finalization-interruption-cleanup.json` |
| `%TEMP%/phase8l-finalization-resume.py` invoking the unchanged release fixture classes and final catalog/parity checks | **PASS, exit 0**: participant 24, lifecycle 19, trials 8 groups; Cup L00–L08, ten races, nine rollback boundaries; final catalog/schema parity and all 46 public tables exactly unchanged | `phase8l-finalization-release-resumed.log`, `phase8l-finalization-release-resumed.exit` |
| `git diff --check`; unchanged `supabase/v2` against entry HEAD | PASS, exit 0, repeated before publication | `phase8l-finalization-static-checks.json` |
| Relative document links/anchors across six continuity documents | 59 checked, none missing; protected guide contents not read | Tool execution, exit 0 |
| Pinned-project GET `/rest/v1/` with existing backend credentials | HTTP 200; Cup 031 tables/RPCs absent from exposed schema. No writes. Migration history, actual schema/grants and Advisor remain UNKNOWN | `phase8l-finalization-remote-read.json` |

L07 injects empty eligibility and each one-sided final eligibility into a synthetic
Cup, rejects all three, checks no certificate/Hall and exact unchanged Cup source,
revision/history/event/receipt state, then restores the valid graph and certifies.
L08 covers elimination, Swiss and doubles with valid completed results, later DQ,
correction of the closed round and eventual certification. Existing cancellation,
multiple-Hall, post-FINISHED/post-ARCHIVED, concurrency and rollback tests remain.
All corruption and failure injection performed so far is confined to disposable
local databases. Shared L07 uses only fixture-scoped row updates, not failure DDL.

The first full release execution and local PostgreSQL process were interrupted
before completion (last full groups: setup 17, matchdays 20; then participant I01).
On resumption no worker remained. PostgreSQL recovered its local WAL; startup took
longer than the initial 15-second launcher wait, then reached ready state. The
interrupted run `phase8i_validation_e3e8f4f7d42442cdaf53edf8facf1c50` was identified
from its stored fixtures, cleaned using the existing dependency order, and all
nonfixture rows compared exactly before/after. Rebuild/parity was not replayed:
the resume runner verifies the source hashes and resumes at participant status,
then lifecycle, trials, Cups and final catalog/schema/data checks. This interruption
is an execution limitation, not a product defect. The resumed process completed
with exit 0 and its final result marker. All required local gates are now covered
by the two logs; the interrupted first process itself has no successful exit claim.
The local PostgreSQL server was then stopped after verifying no other client
sessions. The three disposable task databases remain, with no fixture residue.

Real staging JWT/FastAPI/PostgREST, public/Auth/Storage baseline and independent
cleanup, migration/source/grants verification and fresh Advisor delta are still
required. The integration search found Supabase available but not installed;
connection was suggested. Local credentials provide PostgREST/Auth access, not a
management token or SQL connection. No remote PASS is inferred from local results.

## Final staging delivery attempt — 2026-09-28

**BLOCKED at management capability preflight; remote 031 classification D
(UNKNOWN / CANNOT VERIFY). No remote write or staging validation attempt started.**

Entry branch `main`, HEAD and independently queried remote main both
`6689402ac7e82f1522f98a7e2712f5053622f713`; fetched tracking ref has `0 0`
divergence. Tracked tree was clean. Source/test/validator/SQL paths equal tested
`39343ea`; 001–030 equal `87a98f5`, and 031 equals `d38b871`. Committed 031 and
the working file both hash to SHA256
`868efbca7a2ecb76138a2e12b37cd35b08cad7a849effa4fdf1dae7cfdcde362`
(Git blob `08235141f249ee02d763a051cd619b0735da19b8`). Those Git/source checks
passed with exit 0; no complete local suite was repeated.

Actual session tool discovery exposes no Supabase management/MCP operations.
Fresh integration discovery reports Supabase available but `installed=false`;
installation/connection was requested through the normal authorized workflow,
with no confirmed completed connection. The checked environment has no Supabase
management token/database URL, executable CLI or CLI token file. Existing local
configuration contains only the pinned URL, anon/service-role keys and fixture
email domain; no credential values were printed or versioned.

At **2026-09-28 10:41:21 UTC**, a read-only GET of the pinned V2 PostgREST schema
returned HTTP 200. `/cup_rounds`, `/cup_certificates`, `/rpc/api_cup_context` and
`/rpc/api_admin_cup` are not exposed. This does **not** establish that 031 is absent.
Evidence: `%TEMP%/phase8l-final-staging-preflight.json`, command exit 0.

Missing authoritative capabilities are project inventory/identity, migration
history, SQL schema/function/ACL/RLS inspection, supported migration application
and Security Advisor. Consequently:

- 031 applied before this attempt: UNKNOWN; applied during it: NO; remote version:
  UNKNOWN. No migration was applied or replayed, and no 032 was created.
- Fresh public/Auth/Storage baseline and remote schema/grants: not obtained.
- JWT/FastAPI/PostgREST staging validation and A8L-01 remote API boundary: not run.
  The existing runner and pinned configuration guard were inspected only.
- Fixture prefix/run ID: none. No Auth users, synthetic rows or Storage writes
  were created. No cleanup operation was needed for this attempt; preexisting
  remote residue and real-data integrity remain unverified.
- Advisor BEFORE/AFTER and delta: not obtained; historical totals are not reused
as fresh evidence. There was no failed migration/fixture execution to recover.
- Protected guide metadata remains 72,079 bytes, UTC mtime 2026-09-22 10:13:27;
  untracked and not read, modified, staged, moved or deleted.

At 12:44 CEST, the final connection-state check still reports `installed=false`.
The three updated continuity documents pass `git diff --check`; 59 relative
links/anchors across the six continuity documents resolve. Implementation/tests/
tools/migrations remain unchanged against task-entry `6689402` (exit 0). This
documentation checkpoint records the blocked attempt, not a staging completion.

Phase 8L remains locally READY FOR STAGING, not DONE. Approved Phase 8 backend
scope is not yet closed; weighted progress remains approximately 68%. Phase 9
has not started. Next action is to install/connect Supabase for the pinned V2
project and verify its tools are callable, then perform the authorized remote
preflight/baseline, migration decision, real validator, independent cleanup and
Advisor comparison. CORS, liveness-only health and legacy DTO notes remain future
deployment considerations, not new work in this task.

## Staging and independent cleanup

Implementation and 031 are already published; the previous instruction to wait
for their push is obsolete. Use the live handoff's next action, not an unconditional
instruction to apply 031. Before any authorized write, independently confirm the
pinned project and migration history, reconcile the committed source and validation
evidence, and obtain a fresh public/Auth/Storage baseline and Advisor inventory.

If 031 is absent, apply only its committed SQL through an available supported
migration mechanism. If already present, verify the recorded migration/schema and
continue validation without replaying it. Record remote version and validation
status immediately after application, then real API/JWT/PostgREST results,
independent cleanup and Advisor differences. Historical 8K.1 Advisor totals are
24 ERROR / 4 WARN / 5 INFO; they are not a fresh 8L preflight inventory.

No reset/bootstrap, historical migration replay, V1, runtime change or cutover.

## Reproducible checks

Reference commands for a later authorized validation task; this section does not
instruct a documentation-only task to run them. The release reset is local only.
The staging command is allowed only after the staging preflight described above.

```powershell
.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cup_release --psql <local-psql.exe> --allow-destructive-reset
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cups_sql --psql <local-psql.exe>
.venv-api\Scripts\python.exe tools/validate_supabase_v2_cups.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
git diff --check
```

Local evidence is under `%TEMP%/phase8l-{release,cups-dev,unit-final}.log`, the recent
unit log named above, and `%TEMP%/phase8l-{migrations,bootstrap}-schema.sql`.
Only random pg_dump restrict keys are removed when comparing dumps; ownership
and grants remain included. These raw files are machine-local and may be absent
in another checkout. The ledger above preserves their inspected result summary;
it does not manufacture missing commit/run provenance.

## Small Phase 8 closure inventory

Scoped inspection of registered routes and approved Phase 8 contracts:

| Domain | Authoritative boundary |
|---|---|
| Auth / identity / Team Lock | PIN bridge + verified JWT; 019 lock; 023 identity contracts |
| Purchases / promotions / redemption | 020–025 eligibility, ledger, effects and robbery |
| League setup / operation / participation | 026–028 admin CAS and frozen-round contracts |
| League finish / archive / Hall | 029 immutable source and historical package |
| Trials / sanctions | 030 recorded Discord verdict, typed effects and compensation |
| Cup / certification / Hall | 031 explicit engine and per-Cup authority; delivery gates above |

No additional critical mutation gap was identified within this approved backend
scope. This is a small closure inventory, not a new broad audit or a claim that the
whole product is deployed. React consumption/polish, deployment/cutover, Companion,
save writes and deferred D8 remain outside this phase. Phase 9 is not started.

The 2026-09-26 context/documentation work did not read, modify, stage, rename or
delete the protected `docs/pokeapp-guia-completa-pestanas-y-producto.md`. Its local
untracked state is recorded in the handoff. Migrations 001–030 and Streamlit/V1
were unchanged by 8L implementation. Global progress is maintained in the
[project checkpoint](project-checkpoint.md), with no increment credited by this
documentation task. Any increment after 8L closes requires actual delivery evidence.
