# Phase 8J: Season Lifecycle Delivery

Local and real Supabase V2 staging validation completed, 2026-09-24 (Madrid).
No secrets included. Authoritative [contract](phase8j-season-finalization.md).

=== POKEAPP PHASE 8J ===

## RESULT

DONE. Explicit lifecycle, local unit/SQL/regression/rollback/parity gates, real
JWT/API/PostgREST staging and independent security/zero-residue checks PASS.
Existing Advisor findings remain unchanged; this is not a global security-clean claim.

## START / END / GIT

Start main, `e2628c5`, origin/main 0/0, clean tracked tree. Protected untracked
guide SHA256 `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
Implementation `5f77a48595a93525a8236599ee5c7352778a9803`,
`api: add atomic season finalization and archive`, pushed before staging changes.
Validator-only follow-up `d46d8a70faeb3aad52991f89307b06b87c1688f1`,
`test: validate lifecycle rejection requests before staging`, pushed before the
successful remote rerun. No API or SQL change in that follow-up.
Documentation closure: `docs: close phase 8j staging validation`; its hash belongs
in Git/final delivery, not its own contents. Final push must leave origin/main 0/0,
tracked tree clean and only the original protected untracked guide remaining.

## FINISH CONTRACT

Explicit ACTIVE -> FINISHED after complete configured final competition, exact
snapshot provenance and reward facts. No auto archive, bonus or save changes.

## REVIEW BOUNDARY

Final competitive close -> explicit finish. No timer or reopen.

## FINAL POINTER

Final CLOSED pointer retained, including after archive. No next season generated.

## ARCHIVE

FINISHED only. One transaction commits lifecycle, frozen package, League Hall,
revision, private event and receipt. Relational history is not deleted.

## ARCHIVE SNAPSHOT

Version 1, typed source revision FK, label and SHA256. Explicit public fields;
no raw/parsed saves, Auth, private locks, sanctions notes or admin receipts.
Required serialization failure rolls back, never leaves a partial archive.

## LEAGUE HALL

Champion/finalist from last official snapshot positions. Existing unique
season/competition and season archive constraints, typed provenance, no rebuild.

## CHAMPION TEAM SOURCE

Final historical public Team Lock -> latest earlier valid closed lock -> empty
team. Recursively sanitized public fields, no live save fallback. No champion
means explicit archive source error rather than fabricated Hall data.

## CUP / OTHER HALL SOURCES

Pending Cup API. Current generic V2 schema lacks certified bracket-final/unique
winner/doubles mapping semantics; no invented reconstruction. Existing Cup Hall
retained and League archive unblocked. Narrow evidence documented in contract.

## HISTORICAL IMMUTABILITY

Existing competitive ACTIVE guards reject writes after finish. Archive/Hall
UPDATE guards and browser DML revokes. 024/025 redemption semantics unchanged.

## DRAFT DISCARD

Logical unused DRAFT only, exact confirmation/reason/CAS. Prepared/competitive/
economic/save/identity/Cup/Trial dependencies block; no global or physical deletion.

## VISIBILITY

Existing public views gain parent discard filters; restrictive base SELECT policies
preserve safe owner reads and admin audit. No new public projection or wider grant.

## IDEMPOTENCY / CAS

026 lifecycle receipt scope hashes actor/season/explicit operation/body/key.
Same request replays. Conflicts/stale revision have no effects; revision increments once.

## ATOMICITY / LOCKS

Principal -> advisory receipt -> season -> ordered players -> days/matches/snapshots
-> team/archive/Hall -> event/receipt. Real database locks, no automatic retry.

## CONCURRENCY

Same/different finish/archive/discard keys; correction, purchase, Team Lock, status,
independent next activation/create and draft setup races; exact-once Hall creators.

## ROLLBACK

Ten local injection cases: finish lifecycle/event/receipt; archive lifecycle/
snapshot/Hall/event/receipt; discard lifecycle/receipt. Full public-data equality.

## MIGRATION 029

`029_season_finalization_archive_hall.sql`, additive, no new table; 001-028 unchanged.
Bootstrap generated from 001-029. Development reset helper only supports local rebuild.

## LOCAL

Expanded focused run PASS: 19 groups and ten full-public-state rollback cases,
exit 0 (`%TEMP%/phase8j-focused-final.log`). Both complete migrations/bootstrap
routes exited 0 with all 019-028 regressions and the same 19 groups / ten rollbacks.
Existing SQL totals: identity 19, redemption 19, robbery 17, setup 17 plus nine
rollbacks, matchdays 20 plus seventeen rollbacks, participant status 24 plus eight
rollbacks. All 019/020/021/022 contracts and their concurrency/rollback gates PASS.
431 unit tests PASS (403 baseline + 28 new), final run 23.419 seconds;
`py -m compileall -q .`, exact ordered 001-029 bootstrap and `git diff --check`
PASS. Existing Streamlit/TestClient/LF-CRLF warnings retained.
Exact ordered `pg_dump --schema-only` parity: **8,987 identical lines**, including
grants/ownership; only random restrict/unrestrict tokens omitted. Dumps:
`%TEMP%/phase8j-{migrations,bootstrap}-schema.sql`. Local PostgreSQL stopped cleanly.

Commands (portable PostgreSQL 17.11, disposable loopback databases only):

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8j_release --user postgres --allow-destructive-reset
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8j_bootstrap --user postgres --allow-destructive-reset --build-source bootstrap
git diff --check
```

Logs: `%TEMP%/phase8j-unit-final.log`, `phase8j-final-migrations.log`,
`phase8j-final-bootstrap.log`. SQL failure injection is exclusively local.

Development issues were not hidden: SQL alias/role-catalog lookup fixed; old
route-absence inventory updated for the newly approved commands; bootstrap
regenerated after SQL edits. Full 019 regression exposed a real owner-read bug
in the first restrictive policy; corrected parent lookup uses the existing safe
view instead of admin-only raw seasons. Earlier checks are rerun, not removed.
The full 024 regression also caught hidden private owner events on imported
discarded seasons. Restrictive policies were narrowed to setup/public activity;
existing private financial/save/redemption reads remain unchanged.
The expanded source test rejected the earlier SQL that did not compare relational
match winners with frozen inputs; final SQL now checks that correspondence.
The empty-competition fixture initially submitted an empty results edit, correctly
rejected by 027. It now opens/closes the empty day without an invalid edit; the
existing matchday API was not changed. Full gates rerun with the corrected fixture.

## STAGING

Applied ONLY exact committed 029 from `5f77a48` after full local green and push,
as **`20260923232516`** (2026-09-23 UTC / 2026-09-24 Madrid).
Exact target `https://uwleqeuzsveqlugugzba.supabase.co`, prior 028 `20260923220301`
verified. No remote reset/bootstrap/V1. **DO NOT REAPPLY 029.**
Successful run, exit 0:
`phase8j_validation_f57115bdc43d4bb1b6be7e50de831da6`.
19 new groups PASS (18 scenario entries plus scoped cleanup). Regressions PASS:
028 participant status 24 groups, 027 matchdays 20 groups, 026 setup 17 groups,
019 Team Lock 13 checks, 020/021 purchases/context 29 checks, 024/025 redemption/
robbery 17 groups. The shared 028 scenarios include real 022 promotional races.
The runner exercises production FastAPI in-process using real Supabase JWT and
PostgREST, not a deployed API or mocked database. No deployment occurred.

Final literal:
`RESULT ok groups=19; real JWT/API/PostgREST; regressions PASS; Auth cleanup PASS`

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_season_lifecycle.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

Log `%TEMP%/phase8j-staging.log`; secrets redacted; intrusive rollback remains local.

First remote attempt `phase8j_validation_068c218da980417b996f561d2fed4b98`
stopped in the fixture's finished-results denial: it sent an empty result batch,
so HTTP DTO validation correctly returned INVALID_REQUEST before the lifecycle
guard. The fixture now sends a valid historical match/winner. One new unit test
validates all four denial payloads against the actual HTTP models. No API/SQL
change or migration reapplication. Independent MCP check after that attempt:
all 40 public-table contents/counts and real-data fingerprints equal baseline;
Auth users/identities/sessions/refresh_tokens all zero. Corrected fixture rerun:
19 SQL groups and ten rollback cases PASS, with 431 unit tests and compile/diff
gates PASS; product SQL/API unchanged. The rerun above then passed all remote
gates. Initial log retained at `%TEMP%/phase8j-staging-first-attempt.log`.
Remote Team Lock/purchase runners explicitly skip intrusive failure injection;
those rollback checks are local evidence, not miscounted as remote checks.

## SECURITY / ADVISOR

Independent post-DDL checks PASS: 40/40 RLS tables, 37 views, all six new function
definitions match local MD5, fixed-path invoker and service-only EXECUTE. All old
function bodies/security unchanged. Exactly 21 public views gain parent filters;
all 37 match local definitions and preserve options/grants. Browser table/column
artifact DML is denied. Existing data hashes/counts unchanged by DDL.
Ten restrictive discard visibility policies; no anon/authenticated EXECUTE on
the six new functions. Seasons/archive/Hall have no browser table or column
INSERT/UPDATE/DELETE privileges. After the full run, all function/view definitions,
security options, grants and new artifact columns still match the post-DDL check.

Advisor before `2026-09-23T23:24:55.472Z`, after `2026-09-23T23:46:50.865Z`:
identical names, severities, counts and object/signature set. No added/removed
finding. Exactly 24 ERROR / 4 WARN / 4 INFO before and after. Existing findings:

| Finding | Severity / count | Existing objects |
| --- | --- | --- |
| [security_definer_view](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view) | ERROR / 24 | The 018 public safe-by-shape projections listed below. No new definer RPC. |
| [function_search_path_mutable](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable) | WARN / 1 | `public.set_updated_at` |
| [authenticated_security_definer_function_executable](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable) | WARN / 3 | `current_trainer_id()`, `current_user_owns_trainer(p_trainer_id uuid)`, `is_current_user_admin()` |
| [rls_enabled_no_policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) | INFO / 4 | Backend-only `admin_operation_receipts`, `matchday_snapshot_revisions`, `robbery_cycles`, `season_admin_state`. |

The exact 24 view findings, all in `public`:

```text
public_activity_events, public_coin_balances, public_cup_matches,
public_cup_participants, public_cup_standings, public_cups,
public_division_memberships, public_divisions, public_hall_of_fame,
public_matchday_movements, public_matchday_snapshots, public_matchdays,
public_matches, public_penalties, public_season_config_versions,
public_season_player_stats, public_season_players, public_seasons,
public_shop_items, public_shop_promotions, public_team_locks,
public_trainer_flags, public_trainers, public_trial_cases
```

These previous findings/decisions were not silently changed by 029. Leaked-password
protection was not returned by either observation; no Auth setting was changed
or claimed fixed. The project is not declared globally security-clean.

## CLEANUP

Local and remote scoped cleanup PASS. Independent MCP SQL after completion:
all **40 public-table row counts AND full-content hashes** exactly equal the
pre-run baseline. Only 10 real trainers, 62 catalog items and 2 app_settings rows;
every other public table has zero rows. Auth users, identities, sessions and
refresh_tokens are each zero. No synthetic fixture or Auth residue remains.

| Existing data | MD5 before = after |
| --- | --- |
| 10 real trainers | `99db01fe5335bad3bd3fa7466b44e8d4` |
| 62 catalog items | `76d1c1d5137e6288f508d62786a6d312` |
| 2 app_settings rows | `9f58a5f36ce10e6d4f41fc540ea85a69` |
| 3 Storage object rows | `744470d4653ef586ffd402c7abbc7691` |
| 1 Storage bucket | `391ce69bf761cb4c199bbe89b510082a` |

No Storage bytes were read/written. 37 views retained: 21 expected parent-filter
changes, 16 definitions unchanged; all match local SQL and preserve security
options/grants. No old function definition/security changed. Protected guide
hash remains the START value. 001-028 byte-unchanged; V1/Streamlit, domain,
Discord, parser/PKHeX and runtime/deployment untouched. Local PostgreSQL stopped.

## PROGRESS BEFORE / AFTER

Before ~64%; after approximately ~66% for the complete project, a planning
estimate, not a test-derived percentage. Credit covers only this validated
lifecycle boundary, not frontend/runtime migration or remaining API contracts.

## NEXT

Determine remaining Juicios/sanctions and Cup-finalization API contract gaps.
No Phase 9 or further API implementation starts automatically.

=== END REPORT ===
