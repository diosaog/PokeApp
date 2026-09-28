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

2026-09-28 (Europe/Madrid), after local finalization, resumed release and fix publication.

## Current objective and authorized scope

Complete Phase 8L within the approved Cup engine / certification / Hall scope.
The current user instruction authorizes implementation, tests, necessary staging
validation, commit and push. It supersedes the earlier audit-only restriction.
No React, Launcher, Companion, PKHeX, visual work, rule changes or Phase 9.

## Current Git

- Branch `main`; entry HEAD `73f8453668a7eae6d4f7cfc400f80b15f8b147b2` matched
  freshly queried remote main on 2026-09-28.
- Fix and validation evidence published in
  `39343ea2add1591826d0809cd7c3c42ec814043c` (`fix: validate cup certification
  eligibility before hall creation`). Fresh remote main matched that full hash;
  `git rev-list --left-right --count HEAD...origin/main` returned `0 0` and the
  tracked tree was clean after push.
- The commit containing this final documentation update records that verified
  publication; it changes no tested source. Obtain the current documentation
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
- Remote 031 application/version: **UNKNOWN**. Do not infer absence or replay it
  from a missing exposed REST table alone.
- Historical DO NOT REAPPLY: 029=`20260923232516`;
  030 schema=`20260924102756`; 030 ACL completion=`20260924103256`.

## Staging / security / cleanup state

- **STAGING_UNVERIFIED**. No remote write or fixture was started by this task.
- Fresh read-only HTTP 200 from pinned V2
  `https://uwleqeuzsveqlugugzba.supabase.co/rest/v1/`; neither Cup 031 tables nor
  its RPCs appear in the exposed schema. This is only REST visibility evidence,
  not migration/source/grants verification.
- No Supabase management tools are exposed in this session. Plugin discovery
  found Supabase available but not installed; installation/connection was
  suggested and is not confirmed. Existing local credentials cover Auth/REST,
  not management SQL or Advisor. Never print or commit them.
- Fresh migration inventory, public/Auth/Storage baseline, Advisor inventory,
  real JWT/FastAPI/PostgREST validation and independent cleanup remain pending.
- Historical Advisor 24 ERROR / 4 WARN / 5 INFO is not a fresh preflight result.
  Previously existing remote residue remains UNKNOWN until independent inspection.

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

When Supabase management access is available, verify the pinned project,
migration history/source/schema/grants,
fresh public/Auth/Storage baseline and Advisor inventory. Apply 031 only if proven
absent, otherwise validate without replay. Run the existing staging validator with
the fixed engine and L07/L08, independently verify cleanup/Advisor delta, then close
the report/checkpoint. Do not repeat local gates without a source change or evidence
gap. Phase 9 remains unstarted.

## Do not do

No staging reset/bootstrap, historical migration replay, remote failure DDL,
V1 changes, protected-guide operations, scope expansion or Phase 9 work.
