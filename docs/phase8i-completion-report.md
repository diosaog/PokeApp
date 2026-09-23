# Phase 8I: Participant Status Delivery

Local and real Supabase V2 staging validation completed, 2026-09-24 (Madrid).
No secrets are included.
Authoritative behavior: [participant status contract](phase8i-participant-status.md).

=== POKEAPP PHASE 8I ===

## RESULT

DONE. Implementation, local SQL/unit gates, real JWT/API/PostgREST staging,
independent security and zero-residue checks PASS. Existing Advisor findings
remain documented below; this does not declare the whole project security-clean.

## START / END / GIT

Start: main, `b34bd54`, origin/main 0/0, clean tracked tree. The sole untracked
protected guide is untouched, SHA256
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
Implementation: `baecb8ad702cce40cc71b078f24b8a327f8ec309`,
`api: add atomic participant status administration`, pushed to origin/main before
any staging mutation. Documentation closure is the following docs-only commit,
`docs: close phase 8i staging validation`; its hash is recorded in Git/final delivery
rather than embedded in its own contents. Final push must leave origin/main 0/0
and the tracked tree clean, with only the protected untracked guide remaining.

## STATUS CONTRACT

Three permanent season-level transitions from active. Account globally_enabled and
robbed flag remain separate. No inactive-to-inactive edit, generic PATCH or reactivation.

## RETIRE

Explicit POST retire -> retired; nonempty reason and roster CAS.

## ABANDON

Explicit POST abandon -> abandoned; no collapse into a generic retired state.

## DISQUALIFY

Explicit POST disqualify -> disqualified; no retroactive point removal or refund.

## EFFECTIVE ROUND

Server current SCHEDULED day in ACTIVE season. OPEN and final CLOSED reject.
Typed round evidence, left_at/reason/actor; timestamp alone is not eligibility.

## SCHEDULED MATCH RECONCILIATION

Validate original canonical pairs, delete only departing player's unpublished
pairs, validate survivors. Same day/config/pointer, surviving match IDs retained.
No rewards, winners, forfeits or fake opponents.

## DIVISION MEMBERSHIPS

Original assignment ranges retained, exact exclusive eligibility cutoff added to
current/future assignments. Historical completed ranges unchanged. Empty ranges
before first play are representable without deletion. No capacity-filling move.
027 helpers support smaller/empty divisions; existing domain scoring/movement stays.

## TEAM LOCK SAFETY

Departing player's current lock blocks. Other locks bind day/player/save, not
opponents, so they remain byte-identical; no 019 change or lock deletion.

## ROBBERY CYCLE

Clear inactive trainer's current robbed projection only. Same 025 completeness,
cycle number and actual last-redemption watermark; one rollover when remaining
active set is complete. Empty set does not roll over; no fabricated new cursor.
Redemptions, gifts and Pokemon flags remain durable and unchanged.

## SHOP / REDEMPTION EFFECTS

No cancel/refund/ledger rewrite, entitlement deletion or reversal of used canjes.
Existing 021/022/024/025 inactive checks block future operations. Explicit races
and post-status denials use the real adapters/RPCs, not in-memory locks.

## SAVES / IDENTITY

No save bytes, parsed JSON, entity ownership or identity changes. Synthetic
save metadata and identity data exist only inside validator scopes and are cleaned.

## CUP / TRIAL DEPENDENCIES

Same-season ongoing Cup direct participant or unknown team side blocks. Completed
Cup data stays. Generic Trial cases/penalties remain; current-day dependencies
block, no verdict or bracket rewrite.

## IDEMPOTENCY / CAS

026 shared actor/participant/status scope and canonical body hash. Same request
replays, different status/body under same key conflicts. Roster/setup +1 once,
day revisions +1 invalidate stale editors. New key after inactivity rejects.

## ATOMICITY / LOCKS

Principal -> receipt advisory -> season -> ordered players -> day -> memberships/
matches -> flags/cycle -> revision/event/receipt. No Python mutex, reverse hierarchy
or automatic retry. All effects in one transaction, private ADMIN event.

## CONCURRENCY

Shared scenarios cover same-key replay, different keys, retire vs abandon, two
different participants, status vs normal/promo purchase, shield/robbery redemption,
Team Lock, open/results/close, last-victim robbery and active-set cycle completion.

## ROLLBACK

Eight local injection points compare exact ALL-public-table data snapshots:
status, membership, pair deletion, trainer flag, cycle, revision, event, receipt.
Both full migrations and bootstrap runs PASS. No injection DDL is used in staging.

## MIGRATION 028

Additive only. 001-027 byte-unchanged. No new tables: 40 public RLS tables / 37
views. Two safe projections append effective round fields; existing security
options remain. Admin setup read adds the same fields; reasons/actors not public.
Bootstrap generated in exact 001-028 order. Reset helper updates are local-dev only.

## LOCAL

403 tests PASS (376 baseline + 27 focused tests), final run 38.019 seconds;
`py -m compileall -q .` PASS.
Exact ordered bootstrap comparison and `git diff --check` PASS.

Both full PostgreSQL 17.11 routes PASS, loopback 127.0.0.1:55439:
`pokeapp_v2_validation_phase8h` (migrations) and
`pokeapp_v2_validation_phase8i_bootstrap` (bootstrap), disposable databases only.
Each ran the complete old 019-027 gates, schema/introspection/RLS/Auth fixtures,
24 participant-status groups and eight full-public-data rollback injections.
Existing regression totals include identity 19, redemption 19, robbery 17,
setup 17 groups + nine rollbacks, matchdays 20 groups + seventeen rollbacks;
019/020/021/022 SQL contracts, concurrency and rollback also PASS.
Exact ordered `pg_dump --schema-only` comparison: **8,268 identical lines**,
including grants/ownership. Only random restrict/unrestrict tokens omitted.

Executed commands (using the existing portable PostgreSQL 17.11 binary path):

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8h --user postgres --allow-destructive-reset
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8i_bootstrap --user postgres --allow-destructive-reset --build-source bootstrap
git diff --check
```

Logs: `%TEMP%/phase8i-unit-final.log`, `phase8i-migrations-full.log`,
`phase8i-bootstrap-full.log`, and `phase8i-{migrations,bootstrap}-schema.sql`.

First development run found only harness adjustments: admin route inventory
16 -> 19, and redemption rejection type in the new race wrapper. Both corrected;
no old regression removed. Existing Streamlit/TestClient/LF-CRLF warnings retained.

## STAGING

Applied ONLY exact committed 028 from `baecb8a` after local gates/push, as
**`20260923220301`** (2026-09-23 UTC / 2026-09-24 Madrid). Pinned Pokeapp 2.0,
`https://uwleqeuzsveqlugugzba.supabase.co`; prior 027 `20260923210625` verified.
No reset/bootstrap/V1. DO NOT REAPPLY 028.

Real JWT/API/PostgREST run completed with exit code 0:
`phase8i_validation_fa87843e10cc4fb08dac9310fc4c20dd`.
24 new groups PASS (23 scenario entries plus fixture cleanup). Regressions:
027 matchdays 20 groups, 026 setup 17 groups, 019 Team Lock 13 checks,
020/021 purchases/context 29 checks, 024/025 redemption/robbery 17 groups PASS.
Status-vs-promotional-purchase and post-inactivity 022 checks also passed in the
new shared scenarios. Temporary Auth users and all synthetic data were removed.

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_participant_status.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

Final literal:
`RESULT ok groups=24; real JWT/API/PostgREST; regressions PASS; Auth cleanup PASS`

Log `%TEMP%/phase8i-staging.log`; no secrets printed. First remote run passed;
no remote reset, bootstrap, failure-injection DDL or automatic retry was used.
Intrusive rollback injection remained local; this is explicitly reported by the
remote Team Lock/purchase regression runners, not miscounted as a remote check.

## SECURITY

Enabled admin JWT guard, backend recheck, strict DTOs, sanitized errors and safe
receipts. New functions invoker/fixed path/service EXECUTE only. Browser admins
cannot direct-write status/cutoffs. Existing Advisor findings not claimed resolved.

Independent MCP checks already confirm 40/40 public tables with RLS, all eight
new/replaced function bodies matching local MD5, invoker/fixed search_path,
no anon/authenticated EXECUTE, and service_role EXECUTE. Nine affected tables have
neither browser table nor column INSERT/UPDATE/DELETE privileges. The two public
views preserve 018 security_invoker=false/security_barrier=true options.

Advisor before `2026-09-23T22:02:42.134Z` and after
`2026-09-23T22:17:54.762Z`: identical finding names, severities, counts and objects.
No finding introduced or cleared by 028. Existing findings:

- 24 ERROR [security_definer_view](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view): the existing 018 public safe-by-shape projections, not new definer RPCs.
- 1 WARN [function_search_path_mutable](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable): `set_updated_at`.
- 3 WARN [authenticated_security_definer_function_executable](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable): existing `current_trainer_id`, `current_user_owns_trainer`, `is_current_user_admin` identity helpers.
- 4 INFO [rls_enabled_no_policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy): intentional backend-only `admin_operation_receipts`, `matchday_snapshot_revisions`, `robbery_cycles`, `season_admin_state`.

These previous decisions/findings are not silently fixed in participant-status
work. The intermittently reported leaked-password-protection warning was not
returned in either observation; no Auth setting was changed or claimed fixed.

## CLEANUP

Protected guide hash unchanged. Local and remote runners verify fixture cleanup.
Independent MCP SQL after the runner also confirms all 40 public-table counts
exactly equal the pre-run baseline: 10 trainers, 62 catalog items, 2 app_settings
and zero rows in every other public table. Auth users, identities, sessions and
refresh_tokens are each zero. No synthetic fixture or Auth residue remains.

Exact before/after content fingerprints are equal:

| Existing data | MD5 before = after |
| --- | --- |
| 10 real trainers | `99db01fe5335bad3bd3fa7466b44e8d4` |
| 62 catalog items | `76d1c1d5137e6288f508d62786a6d312` |
| 3 Storage object rows | `744470d4653ef586ffd402c7abbc7691` |
| Storage buckets | `391ce69bf761cb4c199bbe89b510082a` |

No Storage bytes were read/written by this phase. Of 37 view definitions, 35 are
unchanged and exactly two have the intended append-only boundary changes; both
match the locally validated definitions: `public_season_players`
`1bf473eccdbd1b811a9a177edb269a6e` and `public_division_memberships`
`721dfea46ad66bf4b4183ba26ba1af7b`. Added columns match committed 028.
Portable local PostgreSQL was stopped cleanly after the local gates.

## PROGRESS BEFORE / AFTER

Before ~62%; after approximately ~64%, a planning estimate for the complete
project, not a test-derived percentage. Credit is limited to this now-validated
participant boundary; deployment/runtime migration and remaining APIs are not done.

## NEXT

Next: 8J finish/archive/Hall, not started. No 8J, Streamlit/V1, React, Companion, physical save writes,
Discord, deployment or runtime cutover included.

=== END REPORT ===
