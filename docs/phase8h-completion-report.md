# Phase 8H: Competitive Matchday Delivery

Date: 2026-09-23. [Authoritative contract](phase8h-matchday-operations.md).
This report distinguishes implementation, local evidence and real V2 staging.
No credentials are included. No API deployment or Streamlit/V1 runtime switch.

=== POKEAPP PHASE 8H ===

## RESULT

LOCAL PASS: implemented; 376 tests, migrations/bootstrap, schema parity,
concurrency, 17 exact rollback points, compileall and diff-check PASS. Staging pending.
Do not start 8I or treat 027 as applied remotely until this section is updated.

## START / END / GIT

- Start branch `main`, HEAD `3503d876e007b6a240d0be9778e211498ca9149b`.
- Start upstream `origin/main`, ahead/behind 0/0; tracked tree clean.
- Baseline: 343 tests; 001-026; 8G.1 DONE local + staging.
- Only original untracked file: protected `docs/pokeapp-guia-completa-pestanas-y-producto.md`.
- Its SHA256: `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
- End commits/upstream/guide verification: pending final gates.

## OPEN

Enabled mapped admin, no participation/name requirement. Current SCHEDULED day,
ACTIVE season, exact effective configuration/roster/pairs and revision CAS.
OPEN timestamp, private event and receipt together; no economy effects.

## RESULTS + REVISION

Batch winner edits/removals only on current OPEN day; each winner belongs to its
exact match. Null resets status to scheduled; a winner makes it completed.
No reported/confirmed product workflow. Strict results-revision CAS prevents
last-writer-wins. Idempotent replay cannot repeat the revision/event.

## CANCEL EDITING

OPEN -> SCHEDULED, same day number/pointer/prepared matches. Winners, snapshot or
movement facts block with DEPENDENT_DATA_EXISTS. Existing Team Locks survive
unchanged. Never uses terminal SQL cancelled status for this command.

## CLOSE TRANSACTION

Backend context/fingerprint -> existing pure domain planner -> one authoritative
SQL commit with fresh locked fingerprint. Changed inputs -> STALE_INPUTS, no
automatic retry. Snapshot, ledger, gift, movements, memberships, next round/pairs,
promotions, pointer, closed status, ADMIN event and receipt commit or rollback together.

## SNAPSHOT / REVISION

New immutable `matchday_snapshot_revisions`; current official projection remains
`matchday_snapshots`. Revision 1 at close, N+1 on allowed correction. Frozen inputs
include effective config, participants/divisions, winners, ranking inputs, penalties,
points/rewards, movement outcome, timestamp/revision. No raw saves/Auth/private teams.
Revision UPDATEs cannot destroy old evidence; current projection requires matching
new history. Old pre-027 imported snapshots are not silently made correctable.

## REWARDS / LEDGER

Configured per-position coin rewards; positive credits only, zero omitted.
Exact day/player/revision source FK and uniqueness; balances remain ledger-derived.
Domain points/penalty semantics reused, not reimplemented. No generic standings
editor or repeated deduction of cumulative sanctions from each round reward.

## LAST-B ROBAR REWARD

Preserved demonstrated legacy rule, including final round, when enabled.
Canonical `robar_pokemon`, quantity 1, zero unit price, pending reward acquisition;
typed day/snapshot/player provenance and uniqueness. No debit or promotion stock
claim. NOT robbery_shield_voucher. Paid and 025 voucher origin rules stay intact.
Missing canonical item fails REWARD_ITEM_UNAVAILABLE, never fuzzy-name dispatch.

## MOVEMENTS

Existing domain A/B promotion/relegation rules. One movement per player/day,
including stay; historical membership ranges end at the closed day and new ranges
begin next day. Immutable snapshot retains prior official movement evidence when
a permitted correction replaces the current projection.

## NEXT MATCHDAY

Non-final: number+1, exact next effective config, SCHEDULED, all unordered
within-division pairs after movement. No automatic open. Unexpected existing
competitive dependencies reject rather than being destructively overwritten.
Next promotions follow existing domain selection, pending with 24-hour activation,
stock 2 normal / 1 mega. Expire current/earlier pending/active/exhausted offers.
Corrections preserve offers; no reroll, Discord or change to purchase contracts.

## CURRENT POINTER

Non-final pointer advances in the same close transaction, never client-supplied.
No committed intermediate state with rewards but a stale/missing next round.
Read-state route supplies safe IDs/revisions necessary for subsequent CAS commands.

## FINAL ROUND

Final close still gives configured rewards/free Robar and frozen snapshot.
No movements/next day; current pointer remains final closed day and season ACTIVE.
No finish/archive/Hall or automatic individual 12 coins. Those remain 8J.

## CORRECTION WINDOW

Most recent closed day only, frozen inputs/config, explicit reason and snapshot CAS.
Next day, if any, must be adjacent SCHEDULED with no results, Team Locks, movement
or penalties. Later snapshot/open/results, used or redeemed gift and pending
physical effects block. A conservative content hash also detects downstream
economy/locks/saves/identity/flags/stats/penalties/competition changes without
trusting timestamps. Fail closed with CORRECTION_WINDOW_CLOSED; no cascade engine.
Any season-linked Cup, even pre-existing at close, also blocks correction; there
is no implicit permission to rebuild its dependent matches or participants.

## COMPENSATIONS

Append signed ledger differences with revision/source/reason; never delete or
rewrite original credits/debits. Reject unsafe negative-balance compensation.
Changed last-B cancels only untouched pending reward with auditable metadata and
issues a new pending gift. Unchanged recipient keeps the original gift. Used
purchases/redemptions are not changed. Same request replays without new facts.

## ATOMICITY / LOCK ORDER

Reuse 026 principal SHARE / receipt advisory / season NO KEY UPDATE / ordered
player UPDATE hierarchy, then day/matches/config and catalog/promotion/derived rows.
Compatible with earlier mutations; no Python mutex and no auto mutation retry.
Input hash closes the gap between planning and commit. Local-only trigger failures
compare complete public-table data before/after, not merely a subset of balances.

## CONCURRENCY

Real separate DB connections cover two admins opening, result-batch CAS, edit vs
close, same/different-key close, close vs draft setup, 021 purchase vs close,
019 Team Lock vs close, correction vs next open/results and two corrections at
one snapshot revision. Assertions cover exact-once ledger/gift/movement/next pairs/
pointer, compensation replay, strict source uniqueness and immutable old revisions.
No remote failure triggers; staging reuses business races with real JWT/API clients.

## MIGRATION 027

`027_competitive_matchdays.sql`: typed day/results revisions, snapshot history,
reward provenance/FKs/dedupe, movement uniqueness, backend wipe-revive count,
RPCs/helpers and direct-write hardening. 001-026 unchanged.
`bootstrap.sql` generated normally; reset helper updated for isolated local tests
only. Never bootstrap/reset on existing staging or V1.

## LOCAL TESTS

- `.\.venv-api\Scripts\python.exe tools/run_unit_tests.py`: **376 PASS**
  (343 baseline + 33 new), disposable SQLite and no live credentials.
- Direct discovery also passed 374 tests before the last two transport tests were
  added. PowerShell reported a native-stderr wrapper failure despite Python's OK;
  the final isolated runner explicitly propagates Python exit code 0.
- `py -m compileall -q .`: PASS.
- PostgreSQL 17.11 loopback 127.0.0.1:55439, disposable database
  `pokeapp_v2_validation_phase8h`: migrations/bootstrap **PASS**.
- Exact schema parity: **8,076 lines**, ownership/grants included; only random
  pg_dump restrict/unrestrict tokens excluded. Compared ordered full dump content.
- Final 8H suite: **20 scenario groups PASS**, **12 exact close rollback injections
  and 5 correction rollback injections PASS**, on both final migrations rebuild
  and full bootstrap validation. Each compares all public-table data before/after.
- Explicit regressions: 019 Team Lock, 020 pointer/Store Ban, 021 normal purchase,
  022 promotion, 023 identity, 024/025 effects/robbery and 026 admin.
- `git diff --check`: PASS.
- Warnings are retained: Streamlit cache/no-runtime, Starlette/httpx TestClient
  deprecation, SQLite ResourceWarnings in direct discovery, Git LF/CRLF notices.

Local iteration incidents, not hidden: an ambiguous PL/pgSQL `code` variable was
renamed; the local PostgREST test adapter gained JSON argument and SETOF response
handling for actual 019 cross-flow races; the duplicate-gift test stopped trying
to insert generated `total_price`. These fixes do not alter migrations 001-026.

Exact SQL commands (same Python interpreter; `$pg` is the portable PostgreSQL bin):

```powershell
$pg = "$env:TEMP\pokeapp_pg17_phase8c_20260922\portable\pgsql\bin"
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql "$pg\psql.exe" --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8h --user postgres --allow-destructive-reset
.\.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_matchdays_sql --psql "$pg\psql.exe" --rebuild
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql "$pg\psql.exe" --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8h --user postgres --allow-destructive-reset --build-source bootstrap
```

First full migrations run passed before the final additional Cup guard. The final
001-027 rebuild reran all 20 8H groups and 17 injections; the final full bootstrap
run reran every older 019-026 regression plus that same expanded 8H suite. Schema
dumps from the final migrations rebuild and final bootstrap are identical.

## STAGING

PENDING. Only after local gates + implementation commit/push: verify project
`https://uwleqeuzsveqlugugzba.supabase.co`, expected latest 026 version
`20260923192300`, then apply ONLY exact committed 027. No reset/bootstrap/V1.

Validator: `.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_matchdays.py
--env-file .env.supabase-v2-rls.local --allow-staging-writes`.
Real verified JWT -> FastAPI TestClient -> production adapters -> PostgREST.
No API deployment. Per-worker transports; secret output redacted. Successful
Auth/database cleanup and independent content comparisons required before DONE.

## SECURITY

40/40 public tables with RLS expected after 027; 37 existing views unchanged.
New snapshot history is backend-only, without browser policies/grants. New
helpers/RPCs are fixed-search-path invoker, service-only EXECUTE. Browser admin
cannot bypass the API to write authoritative days/results/snapshots/movements/
ledger or invoke privileged RPCs. Reads preserve existing privacy/projections.

Advisor is NOT asserted globally clean. Pre-existing 018 definer-view findings,
identity-helper warnings and mutable `set_updated_at` search_path are separate
launch-hardening work. Expected new no-policy INFO is intentional backend-only
history, not permission to add broad browser policies. Actual remote count pending.

## CLEANUP

Synthetic prefix `phase8h_validation_<uuid>`; no real trainer/catalog/Storage writes.
Local fixtures have cleanup in finally; remote fixture/Auth cleanup and independent
SQL zero residue/fingerprint checks pending. Protected guide remains excluded from git.

## PROGRESS BEFORE / AFTER

Before: ~59%. Until staging closes, delivered-project estimate remains ~59%.
Expected completed 8H contribution roughly +2 to +3 percentage points, not an
endpoint/test count. React/Cloudflare, migration/shadow/cutover, Companion/physical
automation, 8I/8J and remaining APIs/security are still separate work.

## NEXT

8I only after 8H DONE. No 8I implementation in this task.

=== END REPORT ===
