# Phase 8J: Season Lifecycle Delivery

Implementation in progress, 2026-09-24. Do not infer staging completion from this
document until executed evidence is recorded below. [Contract](phase8j-season-finalization.md).

=== POKEAPP PHASE 8J ===

## RESULT

Local implementation, unit, full SQL/regression, rollback and schema parity PASS.
029 applied; PENDING completion of real staging validation and final cleanup.

## START / END / GIT

Start main, `e2628c5`, origin/main 0/0, clean tracked tree. Protected untracked
guide SHA256 `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
Implementation `5f77a48595a93525a8236599ee5c7352778a9803`,
`api: add atomic season finalization and archive`, pushed before staging changes.
Documentation closure will be recorded after real validation.

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
Synthetic prefix `phase8j_validation_<uuid>`; real JWT/API/PostgREST, 027/028 and
prior regressions are now running, not yet declared complete.

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
gates PASS; product SQL/API unchanged. Corrected remote validation pending.

## SECURITY / ADVISOR

Independent post-DDL checks PASS: 40/40 RLS tables, 37 views, all six new function
definitions match local MD5, fixed-path invoker and service-only EXECUTE. All old
function bodies/security unchanged. Exactly 21 public views gain parent filters;
all 37 match local definitions and preserve options/grants. Browser table/column
artifact DML is denied. Existing data hashes/counts unchanged by DDL.
Advisor before: 24 ERROR / 4 WARN / 4 INFO; final comparison pending.
No global-clean claim.

## CLEANUP

Local scoped cleanup built in. Independent staging public/Auth counts and real
trainer/catalog/Storage fingerprints still pending. Protected guide untouched.

## PROGRESS BEFORE / AFTER

Before ~64%. No completion credit until all gates pass.

## NEXT

Determine remaining Juicios/sanctions and Cup-finalization API contract gaps.
No Phase 9 or further API implementation starts automatically.

=== END REPORT ===
