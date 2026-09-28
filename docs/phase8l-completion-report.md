# Phase 8L delivery report — Cup engine / certification (DONE)

Started: 2026-09-24. Evidence reconciled: 2026-09-26.
Technical audit and local finalization correction: 2026-09-28; real staging closure: 2026-09-28.
Starting HEAD `87a98f5`, branch `main`, origin 0/0 at phase start.
Baseline: 466 unit tests, migrations 001–030, complete-project estimate ~68%.
030 already deployed as `20260924102756` and `20260924103256`; never replayed.

This is the durable technical and delivery record for completed Phase 8L.
The [live handoff](work-in-progress/phase8l-live-handoff.md) is closed/superseded.
Historical audit and blocked-attempt evidence below is dated and retained; the
remote closure section supersedes its earlier pending/UNKNOWN states. Follow the
[MultiIA protocol](AI/PokeApp_Multi_AI_Continuity_Protocol.md).

## Delivery status

**Phase 8L DONE; approved Phase 8 backend scope CLOSED.** A8L-01 is fixed and
published; local and real V2 staging gates pass, with independent exact cleanup
and zero new Advisor ERROR/WARN. 031 was applied once as `20260928110301`; the required
narrow Advisor correction 032 once as `20260928111840`. **Do not reapply either.**
001-031 remain unchanged.

Authoritative contract: [Cup engine](phase8l-cup-engine.md). Approved scope remains
Swiss + Top 4, elimination and doubles RR + Top 2/Bo3 final. No Phase 9 work,
public API deployment, V1 runtime change or cutover. Weighted full-product estimate
is ~70%, recorded in the [checkpoint](project-checkpoint.md).

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

## Historical validation ledger

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

### Local finalization validation ledger

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

At this earlier checkpoint, real staging, the baseline, independent cleanup,
migration/source/grants and Advisor delta were still pending. The remote closure
section below supersedes this historical access limitation. The integration search found Supabase available but not installed;
connection was suggested. Local credentials provide PostgREST/Auth access, not a
management token or SQL connection. No remote PASS is inferred from local results.

## Historical blocked staging delivery attempt (superseded) — 2026-09-28

**At this earlier attempt: BLOCKED at management capability preflight; remote 031 classification D
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

## Remote closure - 2026-09-28

### Verified preflight and historical mechanism

Entry: `main`, `bdaa7f7f5a429ebe20f5a17fefa7a66193ccb973`, matching fresh remote
main. User login/link succeeded. Authenticated CLI **2.118.0**, linked SQL and
Management API identify **Pokeapp 2.0**, `uwleqeuzsveqlugugzba`, eu-central-1,
ACTIVE_HEALTHY. The CLI credential stayed in memory; no secrets were printed or
versioned. Local CLI cache `supabase/.temp/` is explicitly ignored.

Authoritative SQL verified **031 NOT APPLIED**: no history entry, four new tables,
seven helper/RPC functions or checked new columns. This supersedes earlier UNKNOWN
REST-only observations. Committed and working 031 bytes matched SHA256
`868efbca7a2ecb76138a2e12b37cd35b08cad7a849effa4fdf1dae7cfdcde362`.
All **22 original migration rows** were hashed in full and remain unchanged:

| Version | Name |
|---|---|
| `20260816211949` | `010_security_helpers` |
| `20260816212058` | `011_rls_policies` |
| `20260816212336` | `012_security_views` |
| `20260816213020` | `014_security_invoker_hardening` |
| `20260901190001` | `013_storage_policies` |
| `20260901234808` | `015_public_trainers_visibility` |
| `20260901235030` | `016_public_team_locks_visibility` |
| `20260901235223` | `017_public_coin_balances_visibility` |
| `20260901235520` | `018_public_views_visibility` |
| `20260922162954` | `019_team_lock_api` |
| `20260922165901` | `020_current_matchday_store_ban_contract` |
| `20260922171752` | `021_normal_purchase_api` |
| `20260922174842` | `022_promotional_purchase_api` |
| `20260923165532` | `023_pokemon_identity` |
| `20260923172957` | `024_redemption_effect_boundary` |
| `20260923180416` | `025_robbery_voucher_and_redemption` |
| `20260923192300` | `026_season_admin_setup_api` |
| `20260923210625` | `027_competitive_matchdays` |
| `20260923220301` | `028_participant_status_admin` |
| `20260923232516` | `029_season_finalization_archive_hall` |
| `20260924102756` | `030_trials_sanctions_api` |
| `20260924103256` | `030_trials_sanctions_acl_completion` |

The user's standard `db push --dry-run` failed because these timestamp versions
have no counterparts in the CLI's standard directory. This is user-provided
command evidence, not a rerun by this task. Canonical files remain under
`supabase/v2/migrations/001_...032_...`. No db push, repair, reset, blind pull,
fabricated timestamp history, renamed canonical migration or historical replay.

The [029 report](phase8j-completion-report.md) and
[030 report](phase8k1-completion-report.md) record versions but do not expressly
identify the applying tool; that missing provenance is not invented. Explicit
project precedents document MCP `apply_migration` in [019](phase8c-team-lock.md),
[023](phase8f0-pokemon-identity.md) and [027](phase8h-completion-report.md).
No project remote application script was found. This delivery used Supabase's
supported [Management API apply-migration endpoint](https://supabase.com/docs/reference/api/v1-apply-a-migration),
`POST /v1/projects/{ref}/database/migrations`, with exact committed SQL and canonical
names, preserving the existing recorded history and custom layout.

### Applications, schema and required Advisor correction

| Source | Remote version / name | Result |
|---|---|---|
| Unchanged committed 031 | `20260928110301` / `031_cup_engine_certification` | Newly applied once, HTTP 200 |
| Committed 032 from `a87d3951cab15ca54eddd2ce3b8d6489cb703576` | `20260928111840` / `032_cup_player_identity_index` | Applied once, HTTP 200 |

Immediately after each application, history was queried and the live handoff
updated with the version, validation-pending state and **DO NOT REAPPLY**. Final
history has **24 records**: the original 22 plus 031 and 032.

All seven Cup function bodies match committed SQL exactly: fixed search_path,
invoker security, PUBLIC/anon/authenticated EXECUTE denial and service execution.
Effective browser table/column INSERT/UPDATE/DELETE/TRUNCATE denial passes across
nine tables and five views. New tables have RLS and no browser grants. Hall
provenance/options, scores, immutable artifacts, constraints, indexes and triggers
match local structure; old function bodies and policies are unchanged. The initial
30 changed/new objects matched local catalog structure, with cloud ACLs checked
independently from local mock-role grants.

After the first complete passing remote run, combined Advisor detected one new
`duplicate_index` WARN: 031's `cup_player_identity` duplicated existing
`uq_season_players_id_season_trainer` on `(id, season_id, trainer_id)`.
The Cup FK and seven historical FKs already used the retained index; none used
the duplicate. Following the authorized post-031 correction rule, **032 drops only
the redundant unique constraint/index with default RESTRICT**. No CASCADE, data
change, FK removal, permission change or historical SQL edit.
032 SHA256: `9a0e14b45451ba929f72420959939cad6d78fed8c25bcb6bb8b5ed3f5fde18e4`.

The remote catalog delta is exactly that removal. All functions/security/FKs and
52 data hashes remain unchanged. Final 29 changed/new objects match the final local
catalog. The new catalog regression fails before 032 and passes after, including
the Cup FK's retained existing unique key.

### Runs, failures and validation

Real runner: `.venv-api/Scripts/python.exe tools/validate_supabase_v2_cups.py
--env-file .env.supabase-v2-rls.local --allow-staging-writes`. Real Auth users/JWT,
FastAPI TestClient in-process and production PostgREST; no public API deployment.

| Run | Result |
|---|---|
| `phase8l_validation_337ccf236dd8441cb7b5bab36ff7d960` | Exit 1 after L00 at `Cup changed League participation`; independent 52-table cleanup PASS |
| `phase8l_validation_e460264209704a75b11f0449aff79dea` | Exit 0 after fixture correction; all Cup/030 gates PASS; exact cleanup PASS; subsequent Advisor check exposed duplicate index |
| `phase8l_validation_3e013eb7f78749ccbed2b792a1b5b118` | **Final exit 0 on published `a87d395`, after 032**; all gates PASS |

The first assertion compared unordered PostgREST row lists. The harness now sorts
by immutable ID while comparing every field of every row. The first run did not
retain both arrays, so its exact difference cannot be reconstructed. Read-only
telemetry in the second run confirms complete before/after rows equal (also in
order for that run), without replacing the assertion. No product mutation was
observed. The final run used the ordinary runner without telemetry. 45 focused
tests and compilation passed after the fixture correction.

Final real suite: **20 Cup/integrated groups**, including L00-L08, ten race families
and cleanup, plus focused 030 typed sanctions/replay/correction/archived-history
regression. L07 rejects empty and each one-sided final eligibility through the real
API without certificate/Hall or partial writes, restores the fixture graph and
certifies. L08 certifies valid elimination/Swiss/doubles after later DQ and correction.
No intrusive rollback/failure DDL was sent to staging.

After adding 032, **511 unit tests** passed again. Fresh local
`validate_supabase_v2_cup_release --skip-regressions` passed: 001-032 and bootstrap
rebuilt twice each, **10,507 normalized schema/grants/ownership lines** identical,
catalog/security, L00-L08, ten races, nine all-public rollback boundaries and exact
46-table cleanup. Unchanged standalone 026-030 suites were not repeated; earlier
evidence remains above, and the real runner covers integrated flows plus focused
030 again. Compile/diff checks pass. Local PostgreSQL is stopped.

### Independent cleanup and Advisor

Fresh pre-DDL baseline: **42 public + four Auth + two Storage tables = 48**.
After 031: **46 public + four Auth + two Storage = 52**. Independent linked SQL
compared counts and deterministic SHA256 of ordered full-row JSONB arrays. All
48 original tables were unchanged by DDL; the four new ones empty. After each
attempt, after 032 and after the final run, all 52 tables exactly match baseline.
Auth users/identities/sessions/refresh_tokens are zero. Nonempty data remains
app_settings=2, shop_items=62, trainers=10, storage.buckets=1, storage.objects=3,
with identical full-row hashes. No Storage bytes touched. Final catalog/ACL/RLS and
migration history equal their post-032 snapshots. **STAGING_DONE_ZERO_RESIDUE.**

| Advisor inventory | Fresh BEFORE | Final AFTER |
|---|---|---|
| Security | 24 ERROR / 4 WARN / 5 INFO | 24 ERROR / 4 WARN / 9 INFO |
| Security + Performance | 24 ERROR / 4 WARN / 99 INFO | 24 ERROR / 4 WARN / 122 INFO |

**Zero new ERROR/WARN**, comparing finding/object/severity identities, not only
counts. 032 removed the intermediate duplicate-index WARN. Existing 24
`security_definer_view` errors from 018 and four function warnings remain unchanged.
Added INFO: four intentional backend-only RLS tables with no browser policies and
19 unindexed foreign keys. No unrelated hardening or speculative indexing added.

[Durable sanitized evidence](phase8l-staging-evidence.json) records migration
history, full-row hashes/counts, function hashes, security checks, catalog digests,
intermediate WARN and final Advisor delta. Raw logs/SQL remain in
`%TEMP%/phase8l-remote-20260928/`: `staging-first.log`, `staging-after031.log`,
`staging.log`, `032-unit.log`, `032-release.log`. No credentials or raw user rows
are included in the durable evidence.

### Git and scope closure

A8L-01 product correction: `39343ea2add1591826d0809cd7c3c42ec814043c`.
Final validated schema/fixture correction: `a87d3951cab15ca54eddd2ce3b8d6489cb703576`,
pushed and independently matched to remote main before 032 and the final real run.
The documentation closure commit contains this report, closed handoff, checkpoint
and evidence; its own hash is obtained from Git. Delivery finishes with ordinary
push, main/origin-main 0/0 and a clean tracked tree. Before publication, 66
relative document links/anchors, JSON/source consistency, protected-file metadata,
secret-pattern scan and `git diff --check` pass.

Protected guide remains untracked, not read/modified/staged/moved/deleted/hidden:
72,079 bytes, UTC mtime 2026-09-22 10:13:27. Only CLI cache is ignored. Historical
001-031, V1/runtime and approved rules remain intact. CORS, liveness-only health,
legacy DTO consumption and deferred D8 remain future notes. **8L DONE; approved
Phase 8 backend CLOSED; full-project estimate ~68% -> ~70%; Phase 9 not started.**

## Reproducible checks

Reference commands for future authorized validation; no execution remains pending
for this delivery. Release reset is local only. Future staging requires a new
preflight; never replay completed migrations.

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
| Cup / certification / Hall | 031 engine and per-Cup authority, 032 index completion; DONE |

No additional critical mutation gap was identified within this approved backend
scope. This is a small closure inventory, not a new broad audit or a claim that the
whole product is deployed. React consumption/polish, deployment/cutover, Companion,
save writes and deferred D8 remain outside this phase. Phase 9 is not started.

The 2026-09-26 context/documentation work did not read, modify, stage, rename or
delete the protected `docs/pokeapp-guia-completa-pestanas-y-producto.md`. Its local
untracked state is recorded in the handoff. Migrations 001–030 and Streamlit/V1
were unchanged by 8L implementation. Global progress is maintained in the
[project checkpoint](project-checkpoint.md), with no increment credited by this
historical documentation task. The remote closure above provides the subsequent
delivery evidence and the checkpoint records the resulting increment.
