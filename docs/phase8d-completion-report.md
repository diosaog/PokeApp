# POKEAPP PHASE 8D.0 + 8D

Date: 2026-09-22. RESULT: **DONE**.

## Start And End

START: branch main; HEAD `3217f55`; upstream origin/main, divergence 0/0.
Working tree: only user-owned untracked `docs/pokeapp-guia-completa-pestanas-y-producto.md`.

END: branch main; functional HEAD `0a61a7a`; closing documentation commit contains
this report (its hash is returned in the final delivery). Upstream origin/main.
Versioned tree clean after closing commit; only the protected guide remains.
No amended commit, force push or user-file modifications.

## 8D.0 Current Jornada

COLUMN / CONTRACT: `seasons.current_matchday_id UUID NULL`, official server-owned
pointer to the competitive round governing shop/promotions/penalties.
Migration: `020_current_matchday_store_ban_contract.sql`.
FK/integrity: composite `(current_matchday_id,id)` -> `matchdays(id,season_id)`.
NULL behavior: business conflict, no default or inferred first/last/open round.
Allowed statuses: scheduled/open and transitional closed; cancelled conflicts.
Future responsibility: season creation initializes it after creating the first
round; close/advance updates it transactionally. Neither endpoint is implemented.
Authenticated browser admins cannot write this new pointer directly; their
previous writable season columns retain their grants/RLS behavior.

## 8D.0 Store Ban

V2 representation: existing `penalty_type='store_ban'`, typed nullable integer
`start_matchday_number` and `end_matchday_number`. Positive bounds, start <= end.
Finished-case rule: actual V2 `trial_cases.status='resolved'`, with matching case,
accused trainer and season (global cases may support season-scoped penalties).
Window rule: inclusive; 3-4 blocks 3/4, not 2/5.
No-window rule: active for legacy compatibility.
Partial-window rule: either missing bound means active, preserving legacy.
resolved_at: not interpreted as expiry. No balance alteration for a Store Ban.
Reusable domain helpers and repository/SQL contracts added, not HTTP-only rules.

TESTS: 16 focused unit tests plus SQL FK/window/case fixtures; local PostgreSQL
migrations/bootstrap PASS. Staging 020 five check groups PASS, cleanup PASS.

## 8D Normal Purchase

METHOD/PATH: `POST /v1/seasons/{season_id}/shop/purchases`.
AUTH: Supabase-verified Bearer -> mapped globally-enabled trainer; active member.
HEADER: required `Idempotency-Key`, 1-128 visible ASCII characters, no whitespace.
BODY: `{"item_id":"<uuid>","confirm_base_price":false}`; strict, no extra fields.
RESPONSE: HTTP 200, same for replay. Purchase/season/trainer/player/item IDs,
quantity=1, frozen unit/total price, initial pending status, purchased_at,
historical balance_after, ledger/event IDs, official matchday ID/number.

ELIGIBILITY FLOW:
1. Verify enabled identity, season existence and active season membership.
2. Lock the season_players wallet row; find a same-key prior receipt.
3. Same semantic request replays it; incompatible item/meaningful flag is 409.
4. New purchase requires active season, explicit valid current round, no Store Ban.
5. Require enabled catalog item with positive base price, then evaluate promotions.
6. Sum season/trainer ledger under the wallet lock and reject insufficient funds.
7. Insert pending purchase, exact debit and public event in one SQL transaction.
8. Return persisted receipt. No redemption, save mutation or external network send.

PROMOTION FLOW:
- Pending non-comodin: 409 PROMOTION_PENDING.
- Pending comodines: base purchase allowed.
- Active unclaimed in-stock valid offer: 409 PROMOTION_AVAILABLE, never silent base fallback.
- Already claimed: base purchase allowed, no second discount.
- Expired/exhausted governing offer: 409 BASE_PRICE_CONFIRMATION_REQUIRED.
- Explicit confirmation: allows fallback, subject to all other rules.
- Current pointer selects offers; cancelled/other-round offers are irrelevant.
- Activation/expiration timestamps are respected without writing promotion state.

ECONOMY: source is SUM(coin_transactions.amount) by season/trainer. No mutable
coin balance, legacy money/saves/badges read or free reward path. FOR UPDATE on
season_players serializes spends; future wallet writers must use the same lock.
Price comes from shop_items; unit_price/total_price preserve purchase history.
Quantity is always one. balance_after is historical, not recomputed on retry.

IDEMPOTENCY: persistent unique `(season_id,trainer_id,idempotency_key)`.
Same request returns the same purchase/debit/event/balance after later catalog
and ledger changes. Different item or relevant confirmation returns 409.
Irrelevant confirmation is normalized to NULL, so true/false are equivalent.
Global enablement/active participation still gate replay; replay is not a charge.

ATOMICITY: one backend-only RPC inserts purchase + negative purchase ledger
reference + public PURCHASE_COMPLETED (deduped by purchase UUID). All-or-nothing
rollback, including event failure. No server catch-and-continue around writes.

SECURITY: SECURITY INVOKER, fixed empty search_path, service_role-only EXECUTE.
PUBLIC/anon/authenticated execute denied. Direct owner/admin purchase/ledger
INSERT/UPDATE remain blocked. Private reads remain owner/admin; public balances
and activity remain intentionally public to authenticated trainers. RLS unchanged.
No secret in API response, event or user-visible backend error.

## Migrations

020: authoritative round + typed ban windows/helpers; no purchase implementation.
021: nullable idempotency/receipt fields, scoped unique index and atomic RPC.
001-019: unchanged. 020 also unchanged after its application.
BOOTSTRAP: regenerated from 001-021 source files, never hand-maintained and
never executed against existing staging. Incremental 020 then 021 only.

## Local Validation

- Auth/API/shop/purchase/penalty/repository/schema tests: **239 PASS**, no skips.
- PostgreSQL 17.11: migrations and bootstrap build/reset/rebuild/fixtures PASS.
- Store Ban: same-season FK, NULL/cancelled pointer, case/status/bounds PASS.
- Concurrency: four sessions, distinct keys with funds for one -> one charge;
  same-key simultaneous requests -> same receipt, one purchase/debit/event.
- Rollback: forced failures in purchase, ledger and event inserts all revert effects.
- Historical receipt: later catalog/ledger changes do not alter retry price/balance.
- Promotions: pending comodin/non-comodin, active, claimed, ended/exhausted,
  timestamp transitions, explicit confirmation and current-round scope PASS.
- Compileall, bootstrap generation and git diff --check PASS.
- Existing warnings are retained: Streamlit bare-mode, Starlette/httpx deprecation,
  Git LF/CRLF. These are not failures.

Exact runnable commands and P01-P50/SB01-SB14 coverage mapping are recorded in
[the implementation document](phase8d-purchases.md#validation-and-reproduction).
The IDs are requirement coverage, not a fabricated claim of 50 Python test cases.
Local destructive validator remains restricted to loopback and a disposable
`pokeapp_v2_validation*` database. No V1 or remote reset was performed.

## Staging

Target: `https://uwleqeuzsveqlugugzba.supabase.co`, project Pokeapp 2.0.
020: applied after `fd108aa` push, context suite PASS, cleanup PASS.
021: applied after `0a61a7a` push, real purchase suite PASS, cleanup PASS.
Final run: `phase8d_validation_1a88417454f045e5bdc5dbcc773dc8a3`.
Result: **RESULT ok checks=29** (five context groups plus R01-R24).

| Remote checks | Result |
| --- | --- |
| R01-R05 real JWT/API purchase, persisted row/debit/event/balance | PASS |
| R06-R07 exact balance and insufficient-funds rollback | PASS |
| R08-R09 stable retry/history and conflicting idempotency key | PASS |
| R10 concurrent double-spend | PASS |
| R11-R14 Store Ban boundaries, outside window, no window, unfinished case | PASS |
| R15-R19 promotion gating and explicit fallback | PASS |
| R20-R21 direct RPC/table-write restrictions, including admin | PASS |
| R22 owner/admin visibility and other-trainer isolation | PASS |
| R23 public balance matches actual ledger | PASS |
| R24 anon API-data/RPC access denied | PASS |

Local ASGI application talked to real Supabase Auth/PostgREST using temporary
users; the API itself was not deployed. No real trainer or save was used.
Deep failure injection stayed local; no intrusive staging triggers were added.

CLEANUP: script verified deletions by recorded UUIDs and unique season, including
Auth users. Independent SQL confirmed zero fixture rows across Auth, trainers,
seasons, matchdays, season_players, shop items/promotions, trial cases, penalties,
purchases, coin transactions and activity events. No seeds or real data removed.
Independent security check: 32 public tables, all 32 RLS-enabled, 37 views;
helper and purchase RPC privileges remain service-only and invoker.
Remote purchase function body equals local migration:
MD5 `af6c9b572b498cbf5d60d1096d4231b1` (comparison checksum, not a security primitive).

## Git

COMMITS:
- `fd108aa supabase: define current matchday and store ban contract`.
- `0a61a7a api: add atomic v2 normal purchase`.
- Closing documentation/evidence commit, hash in the delivery message.

PUSH: normal pushes to origin/main; no force/amend. Final upstream alignment
and clean versioned tree are checked after the closing documentation push.
USER GUIDE: untouched, untracked, never staged; SHA256 unchanged:
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.

## Checkpoint

LAST COMPLETED: Phase 8D.0 + 8D, local and V2 staging.
NEXT: **Phase 8E promotional purchase atomic stock claim**, not implemented.

REMAINING PHASE 8:
- Promoted purchase/stock claim.
- Redemption and effect boundary.
- Close matchday/rewards/ledger/snapshot/movements and advance official pointer.
- Season/admin mutations and configuration version operations.
- Trainer status/flags.
- Saves/parser write boundary.
- Archive/Hall finalization.
- Other critical competition operations from the existing roadmap.

BLOCKERS: none for completed 8D. This does not declare the whole API complete.
FUTURE NOTES: all wallet writers must follow the same row-lock discipline;
Discord must remain post-commit/event-driven. Deployment, PIN operational setup,
real data migration, React/Cloudflare, shadow mode and cutover are separate work.
Streamlit legacy remains the runtime, V1 remains intact, V2 is not its source
of truth, no dual-write. PKHeX/Discord/Companion are untouched.

RECOMMENDED NEXT ACTION: implement only Phase 8E atomic promotional claim after
explicit authorization, preserving this normal-purchase contract.

END REPORT.
