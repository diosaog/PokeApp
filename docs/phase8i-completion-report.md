# Phase 8I: Participant Status Delivery

Local validation completed, 2026-09-24; staging still pending. No secrets are included.
Authoritative behavior: [participant status contract](phase8i-participant-status.md).

=== POKEAPP PHASE 8I ===

## RESULT

Implementation and all local gates PASS. Staging still PENDING.
Only after implementation push may committed 028 be applied remotely.

## START / END / GIT

Start: main, `b34bd54`, origin/main 0/0, clean tracked tree. The sole untracked
protected guide is untouched, SHA256
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
End/implementation/closure commits recorded only after execution.

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

NOT YET APPLIED. Only allowed target Pokeapp 2.0,
`https://uwleqeuzsveqlugugzba.supabase.co`, expected latest 027 `20260923210625`.
After local gates and implementation push: apply only committed 028, run synthetic
real JWT/API/PostgREST fixtures and independent cleanup checks. No reset/bootstrap.

## SECURITY

Enabled admin JWT guard, backend recheck, strict DTOs, sanitized errors and safe
receipts. New functions invoker/fixed path/service EXECUTE only. Browser admins
cannot direct-write status/cutoffs. Existing Advisor findings not claimed resolved.

## CLEANUP

Protected guide hash unchanged. Local fixture cleanup verified by runners;
independent real staging/Auth/content fingerprints still pending.

## PROGRESS BEFORE / AFTER

Before ~62%. Do not award completion progress until all staging gates PASS.

## NEXT

8J only when 8I DONE. No 8J, Streamlit/V1, React, Companion, physical save writes,
Discord, deployment or runtime cutover included.

=== END REPORT ===
