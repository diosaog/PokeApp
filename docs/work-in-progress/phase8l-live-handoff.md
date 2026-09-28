# Phase 8L - Live Handoff

This is the single maintained operational record for Phase 8L. Documentation is
memory, not authority; verify Git, source, processes and remote state on entry.

## Memory references

- [Canonical MultiIA protocol](../AI/PokeApp_Multi_AI_Continuity_Protocol.md).
- [Master project protocol](../PokeApp_2.0_Protocolo_Maestro_MultiIA.md).
- [Project checkpoint](../project-checkpoint.md).
- [Approved Cup contract](../phase8l-cup-engine.md).
- [Delivery report and dated evidence](../phase8l-completion-report.md).

## Status

**READY FOR STAGING - A8L-01 corrected; all local gates PASS. Delivery is blocked
by missing Supabase management access for remote preflight. Not DONE.**

## Last updated

2026-09-28 12:41 CEST, final staging delivery capability/source preflight.

## Current objective and authorized scope

Complete the remaining real V2 staging delivery within the approved Cup scope.
The current instruction authorizes verified incremental migration, real validation,
cleanup and Git delivery. Do not reopen completed local work unless remote evidence
reveals a product defect; do not rerun the full local gates merely for reassurance.
No React, Launcher, Companion, PKHeX, visual work, rule changes or Phase 9.

## Current Git

- Final staging task entry: `main`, HEAD
  `6689402ac7e82f1522f98a7e2712f5053622f713`, matching fresh remote main;
  divergence `0 0`, tracked tree clean, only the protected guide untracked.
- Fix and validation evidence published in
  `39343ea2add1591826d0809cd7c3c42ec814043c` (`fix: validate cup certification
  eligibility before hall creation`). Fresh remote main matched that full hash;
  `git rev-list --left-right --count HEAD...origin/main` returned `0 0` and the
  tracked tree was clean after push.
- The commit containing this staging-preflight update records the verified
  entry and capability blocker; it changes no tested source. Obtain the current documentation
  commit from Git and compare remote refs on entry, rather than treating the
  fix hash as permanently current. The inherited audit notes remain in the report.
- The protected guide remains pre-existing and untracked. Never add, delete,
  move or hide it to manufacture an entirely clean working tree.

## Completed / verified

- Corrected completed-match eligibility using each round's frozen draw. Completed
  matches must reconstruct as scheduled, not an automatic result.
- Related checks reject an ineligible forfeit winner, retroactive forfeits/voids
  justified only by a later DQ, and reactivation after the final draw.
- Preserved valid historical results, late final-loser DQ, doubles members,
  correction/recreated successor behavior, byes and post-League operations.
- Before-fix real SQL reproduction: empty final eligibility still created one
  certificate/Hall. All 46 public tables returned exactly to baseline afterward.
- 45 focused engine/API tests and 511 general tests PASS; compileall PASS.
- Focused real SQL: L00-L08, ten race families, nine exact rollback boundaries,
  all-public cleanup (46 tables) PASS. L07 checks rejection without partial writes;
  L08 certifies elimination/Swiss/doubles after played results, DQ and correction.
- Fresh migration/bootstrap rebuild twice each, inherited ACL/RLS/catalog checks,
  exact 10,515-line schema/grants/ownership parity PASS. Setup 17 and matchday 20
  regression groups PASS before interruption. Resumed participant 24, lifecycle
  19 and trials 8 groups PASS with exact all-public cleanup. Rebuilt-database Cup
  L00-L08, ten races, nine rollback points and final catalog/schema/data checks
  PASS. Resumed process exit 0; all required local gates are covered by the logs.
- 59 document links/anchors checked; compileall, diff-check and unchanged
  historical migrations confirmed. Source fingerprints match the tested files.
- Source SHA256 and exact commands/results/limitations are in the
  [finalization evidence](../phase8l-completion-report.md#finalization-correction-and-evidence--2026-09-28).
  Raw logs use `%TEMP%/phase8l-finalization-*`; do not confuse them with old logs.

## Migrations

- **No new migration required. 001-031 and bootstrap are unchanged.**
- Full graph validation belongs to the trusted application planner; 031 rechecks
  fingerprint/CAS and final provenance under locks before the atomic commit.
  The report records why this combined defense closes A8L-01 without duplicating
  the engine in SQL. SQL alone does not validate arbitrary privileged plans.
- 031 remains committed/published from `d38b871`.
- Remote 031 classification: **D — UNKNOWN / CANNOT VERIFY**. Applied before this
  task: UNKNOWN; applied during this task: NO; exact remote version: UNKNOWN.
  Do not infer absence or replay it from missing exposed REST tables alone.
- Source verified against published `d38b871`, and 001–030 against `87a98f5`;
  no diff. Committed 031 and working file have identical SHA256
  `868efbca7a2ecb76138a2e12b37cd35b08cad7a849effa4fdf1dae7cfdcde362`.
- Historical DO NOT REAPPLY: 029=`20260923232516`;
  030 schema=`20260924102756`; 030 ACL completion=`20260924103256`.

## Staging / security / cleanup state

- **STAGING_UNVERIFIED**. No remote write or fixture was started by this task.
- On 2026-09-28 at 10:41 UTC, fresh read-only HTTP 200 from pinned V2
  `https://uwleqeuzsveqlugugzba.supabase.co/rest/v1/`; neither Cup 031 tables nor
  its RPCs appear in the exposed schema. This is only REST visibility evidence,
  not migration/source/grants verification.
- This final-delivery session again exposes no Supabase management/MCP operations.
  Fresh integration discovery explicitly returns Supabase `installed=false`.
  Installation/connection was requested through the normal workflow; no completed
  connection is confirmed. No management-token/database-URL environment variable,
  Supabase CLI executable or CLI token file is available in the checked locations.
  Existing configured keys cover Auth/REST, not management SQL or Advisor.
- Exact missing capabilities: authoritative project inventory, migration history,
  SQL catalogs/function definitions/ACL/RLS, supported migration application, and
  Security Advisor. The pinned endpoint responds, but management identity/schema
  and migration state cannot be independently established.
- Fresh migration inventory, public/Auth/Storage baseline, Advisor inventory,
  real JWT/FastAPI/PostgREST validation and independent cleanup remain pending.
- Historical Advisor 24 ERROR / 4 WARN / 5 INFO is not a fresh preflight result.
  Previously existing remote residue remains UNKNOWN until independent inspection.
- Evidence: `%TEMP%/phase8l-final-staging-preflight.json` (no secrets), plus tool
  discovery and Git checks. Source equals the tested `39343ea`; local unit/SQL gates
  were not rerun. The existing staging runner was inspected, not executed: it would
  create Auth users and fixtures before the required management preflight is met.

## Active / interrupted operations

- First full release attempt was interrupted during participant-status fixtures;
  its worker and PostgreSQL were no longer running on resumption. The log has no
  final result/exit code; do not label that whole attempt PASS.
- Local PostgreSQL recovered WAL and reached ready state after a startup wait
  timeout. Scoped recovery removed two seasons and seven trainers from exact run
  `phase8i_validation_e3e8f4f7d42442cdaf53edf8facf1c50`. Every nonfixture public row
  was verified unchanged; schema/grants/catalog still match bootstrap.
- Resumed worker `%TEMP%/phase8l-finalization-resume.py` completed with exit 0;
  log `%TEMP%/phase8l-finalization-release-resumed.log`, matching `.exit` file.
  Participant, lifecycle, trials, Cups and final parity/cleanup are complete.
- **No active worker remains.** Local PostgreSQL was stopped after checking no
  other client sessions. Do not assume it is running on a future entry.
- Local cluster `%TEMP%/pokeapp_pg17_phase8c_20260922/cluster`, loopback `55439`.
  Task databases: `pokeapp_v2_validation_phase8l_finalization`, its `_bootstrap`,
  and `pokeapp_v2_validation_phase8l_finalization_probe`. No staging run IDs exist.

## Files / areas changed

- `app/domain/services/cup_engine.py`: historical certification invariants.
- `tests/test_cup_engine.py`, `tests/test_api_cups.py`: targeted regressions.
- `tools/validate_cup_fixtures.py`: shared L07/L08 integrity and valid DQ fixtures.
- `tools/validate_supabase_v2_cups_sql.py`: independent all-public cleanup check.
- This handoff, delivery report and checkpoint: evidence and actual remaining work.

## Protected file

`docs/pokeapp-guia-completa-pestanas-y-producto.md` was not read, changed or staged.
Entry metadata: 72,079 bytes, last write UTC 2026-09-22 10:13:27. It must remain
untracked. Clean tracked state and that intentional exception are reported separately.

## Not yet validated / remaining delivery

1. Establish management access to the pinned project and run the full remote
   preflight; apply committed 031 only if verified absent, never replay it blindly.
2. Complete real JWT/API/PostgREST checks, independent zero-residue cleanup and
   fresh Advisor delta, then update report/checkpoint and close 8L.

## Next exact step

Install and connect Supabase with access to V2 `uwleqeuzsveqlugugzba`; confirm that
its management operations are actually callable in this session. The user has
already authorized delivery; no further generic deployment permission is needed.
Then verify the pinned project,
migration history/source/schema/grants,
fresh public/Auth/Storage baseline and Advisor inventory. Apply 031 only if proven
absent, otherwise validate without replay. Run the existing staging validator with
the fixed engine and L07/L08, independently verify cleanup/Advisor delta, then close
the report/checkpoint. Do not repeat local gates without a source change or evidence
gap. Phase 9 remains unstarted.

## Do not do

No staging reset/bootstrap, historical migration replay, remote failure DDL,
V1 changes, protected-guide operations, scope expansion or Phase 9 work.
