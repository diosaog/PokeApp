# Phase 8H: Competitive Matchday Delivery

Date: 2026-09-23. [Authoritative contract](phase8h-matchday-operations.md).
This report distinguishes implementation, local evidence and real V2 staging.
No credentials are included. No API deployment or Streamlit/V1 runtime switch.

=== POKEAPP PHASE 8H ===

## RESULT

DONE: implementation, 376 tests, migrations/bootstrap, schema parity, concurrency,
17 exact rollback points, real V2 staging and independent zero-residue cleanup PASS.
This is NOT API deployment, runtime cutover or globally clean launch security.

## START / END / GIT

- Start branch `main`, HEAD `3503d876e007b6a240d0be9778e211498ca9149b`.
- Start upstream `origin/main`, ahead/behind 0/0; tracked tree clean.
- Baseline: 343 tests; 001-026; 8G.1 DONE local + staging.
- Only original untracked file: protected `docs/pokeapp-guia-completa-pestanas-y-producto.md`.
- Its SHA256: `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
- Implementation commit pushed: `bef5c4d04fe68948c816aec5e275bec313fe064f`,
  `api: add atomic matchday close and safe correction`.
- Final report delivered in a subsequent documentation-only commit,
  `docs: close phase 8h staging validation`. Its hash is reported at delivery,
  avoiding a circular self-reference inside this file.
- Normal commit/push, no amend/force; final target `main` / `origin/main` 0/0.
- Tracked tree clean at delivery; only protected original untracked guide remains,
  with the same SHA256. No migrations 001-026 or protected runtime files changed.

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

DONE. Verified exact V2 project
`https://uwleqeuzsveqlugugzba.supabase.co` and latest 026 `20260923192300`.
After local gates and push `bef5c4d`, applied ONLY its exact committed 027 via MCP
as **20260923210625**. No reset/bootstrap/V1. Do not reapply 027.
Run: `phase8h_validation_ba915696f7bb4e2684d9d7523a3740ca`.

- 8H: **20 groups PASS**, including both supported and blocked corrections,
  real races, exact-once economy/gift, final ACTIVE state and direct browser denials.
- 026 setup regression: **17 groups PASS**.
- 019 Team Lock regression: **13 checks PASS**.
- 020/021 context/purchase regression: **29 checks PASS**.
- Identity/redemption/robbery/voucher regression: **17 groups PASS**.
- Literal result: `RESULT ok groups=20; real JWT/API/PostgREST; regressions PASS; Auth cleanup PASS`.
- First remote run passed; no remote SQL patch/retry or failure injection needed.
- Known prior Windows/httpx intermittency is not claimed generally fixed by this run.

Validator: `.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_matchdays.py
--env-file .env.supabase-v2-rls.local --allow-staging-writes`.
Real verified JWT -> FastAPI TestClient -> production adapters -> PostgREST.
No API deployment. Per-worker transports; secret output redacted. Successful
Auth/database cleanup and independent content comparisons completed after exit 0.

## SECURITY

Independent SQL confirms 40/40 public tables with RLS after 027.
All ten 027 function bodies (nine new, one replacement) match local MD5 checksums;
invoker, fixed search_path and service-only EXECUTE verified. No table/column
browser writes on days/matches/snapshots/history/movements/ledger.
The 37 existing view definitions are unchanged (aggregate MD5 below).
New snapshot history is backend-only, without browser policies/grants. New
helpers/RPCs are fixed-search-path invoker, service-only EXECUTE. Browser admin
cannot bypass the API to write authoritative days/results/snapshots/movements/
ledger or invoke privileged RPCs. Reads preserve existing privacy/projections.

Advisor is NOT globally clean. Before/after comparison at 21:06 / 21:11 UTC:

- **24 existing ERROR**: 018 public definer projections, unchanged.
- **1 existing WARN**: mutable search_path in `set_updated_at`.
- **3 existing WARN**: authenticated EXECUTE on definer identity helpers
  `current_trainer_id`, `current_user_owns_trainer`, `is_current_user_admin`.
- **INFO 3 -> 4**: backend-only tables without browser policies. The sole addition
  is `matchday_snapshot_revisions`, alongside receipts, admin state and robbery cycles.
  RLS plus revoked grants is intentional; do not add permissive policies to hide it.
- No new definer/search_path/EXECUTE warning from 027. No Auth settings changed.
  Previous intermittent leaked-password-protection warning is not claimed fixed.

These existing findings remain separate launch-hardening work. See the
[recorded advisor explanations/remediation links](phase8g1-completion-report.md#advisor-y-limites).

## CLEANUP

Synthetic prefix `phase8h_validation_<uuid>`; no real trainer/catalog/Storage writes.
Local fixtures have cleanup in finally. Independent MCP SQL checked ALL 40 public
table counts against preflight: zero fixture residue. Only original 10 trainers,
62 catalog items and 2 app_settings rows remain; other public tables are empty.
Auth users, identities, sessions, refresh tokens and orphan sessions: **zero**.
Real content fingerprints and all ten affected SQL function bodies match exactly.
Protected guide remains excluded from git. Temporary local PostgreSQL was stopped.

| Original Data | Same MD5 Before / After |
| --- | --- |
| trainers (10) | `99db01fe5335bad3bd3fa7466b44e8d4` |
| shop_items (62) | `76d1c1d5137e6288f508d62786a6d312` |
| storage.objects (3) | `744470d4653ef586ffd402c7abbc7691` |
| storage.buckets | `391ce69bf761cb4c199bbe89b510082a` |
| public view definitions (37) | `7298ac90ff441476b6efd0ea28160361` |

## PROGRESS BEFORE / AFTER

Before: **~59%**. After full local/staging closure: **~62%**, approximately +3
percentage points. This is a weighted estimate of delivered product/architecture,
not an endpoint/test count: the competitive round transaction and safe correction
boundary are now proven end-to-end. React/Cloudflare, migration/shadow/cutover, Companion/physical
automation, 8I/8J and remaining APIs/security are still separate work.

## NEXT

**Phase 8I: participant status / lifecycle administration** can be scoped next.
8H is DONE; no 8I implementation in this task. 8J still owns finish/archive/Hall.

=== END REPORT ===
