# Phase 8F.1 / Full 8F Closure

## Result

PARTIAL: implementation and all local gates complete; staging gate pending.
The previous two-effect report is preserved in Git at `2bd0365`.
Do not mark full Phase 8F DONE until the remote validation and cleanup pass.

## Checkpoint

- Start: main / `2bd0365` / origin/main 0/0.
- End: implementation and closure commit hashes recorded at delivery.
- Protected user guide remains untracked and untouched.
- SHA256: `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
- No amend, force push, V1 operation, API deployment or runtime migration.

## Canonical Voucher

Code `robbery_shield_voucher`; display Comodin de Blindaje por Robo (accented in SQL).
Reward-only, category comodines, price zero, disabled for shop offers but redeemable.
Existing purchase RPC checks plus typed catalog constraints deny normal/promo buying.
Recipient is the ROBBER, proven by legacy `add_purchase(current_user, ..., 0)`.
One qty1 pending zero-price gift per robbery; unique origin_redemption_id, reciprocal
gift FK and acquisition guard. No ledger, promotion or stock mutation.
Existing 61 catalog items retain their data and purchasing semantics.

## Robbery And Voucher

Actor: enabled JWT trainer, active participant, own pending qty1 purchase.
Victim: different active same-season participant resolved from Entity ownership.
Target: current unambiguous bound observation, party or boxes 1-7, not blindado.
Victim already robbed in current cycle conflicts. Exact Entity flags: blindado,
robado, robado_from=victim UUID, robado_at=timestamp. Durable history/cycle/watermark
and trainer robbed projection are atomic with the gift, used purchase and private event.
The completing theft succeeds, then advances the cycle. Retirement pre-reset preserved.
Physical status pending, completed_at NULL, Entity owner unchanged (still victim).
Voucher: own party or boxes 1-8, current/unambiguous/not shielded; sets blindado and
blindaje_por_robo, physical not_required, no additional gift.
Blindar/Revivir preserve 024 behavior. No current-day, Store Ban or active-lifecycle
condition is invented for entitlement use. Normal/promo redemptions are equivalent.

## API And Atomicity

Existing endpoint/body only; actor from JWT, victim/head from server, never client.
Receipt exposes gift_purchase_id for theft, without raw/private evidence.
Same-key/purchase/target replay returns immutable receipt after identity advances.
Changed target conflicts; different key on consumed purchase conflicts.

Lock order: trainer SHARE -> season NO KEY UPDATE -> all existing season_players
ordered by UUID UPDATE -> purchase -> item -> Entity/head/observation -> cycle/flags
-> gift -> purchase used/event. Per-season serialization is intentional.
Future membership operations must acquire season then participants.
[Full contract, legacy evidence and lock rationale](phase8f1-robbery-voucher.md).

PostgreSQL tests cover same request (four workers), different keys, same target,
same victim/different entities, opposite A/B thefts, final two cycle operations,
and a paused victim-head race. Seven AFTER-trigger failure sites verify complete
rollback: redemption, Pokemon flag, trainer flag, cycle, gift insert, actor purchase
update and event. No retry masks failures.

## Migration 025

Adds typed catalog/acquisition/origin, gift/cycle history, backend-only robbery_cycles,
timestamp/trainer flag types, constraints/indexes; replaces api_redeem_purchase and
adds an acquisition trigger. Both invoker, fixed search_path, backend-only execution.
37 public RLS tables after application; all existing 37 views unchanged.
Normal/promo purchase RPCs and identity/auth helpers unchanged. 001-024 unchanged.
Bootstrap generated from 001-025. Reset used ONLY on disposable loopback PostgreSQL.

## Local

- Unit suite: 317 PASS (311 baseline plus six API/schema tests).
- Compileall: PASS (excludes virtualenvs, Git and node_modules).
- Bootstrap generated equality: asserted in tests.
- Full migrations SQL validator: final run PASS, PostgreSQL 17.11 loopback.
- Bootstrap SQL validator: PASS, all prior/new fixtures, 17 robbery check groups,
  19 shield/revive groups, seven robbery rollback sites plus four prior rollback sites.
- Schema-only dumps identical (random pg_dump restrict token omitted): SHA256
  EF8524F724D20607EFD67BCE7C587213D21E84D7EE36BA64E2EEE32409701B9A.
- Diff-check: PASS. Warnings: Streamlit no-runtime and Starlette TestClient deprecation;
  Git CRLF normalization notices. No suppressed validation failure.
- Fixture catalog price changes scoped to synthetic items.
- Local psql transport uses stdin to avoid Windows command length limits on
  synthetic identity payloads. Production transport unchanged.

## Staging

Verified target https://uwleqeuzsveqlugugzba.supabase.co, Pokeapp 2.0.
Latest preflight migration 024 `20260923172957`: 61 items, 10 trainers, 3 Storage
objects, zero seasons/purchases/redemptions/Auth users. 025 applied as
`20260923180416` after implementation commit/push `4cf21bf`.
First run `phase8f1_validation_f630a20aac7d4c16abf1c277bb3e89a7` failed on ReadError
at the first concurrent redemption. Cleanup succeeded; independent SQL confirmed
zero seasons/purchases/redemptions/cycles/Auth users and the original 10 trainers.
Validator now isolates worker sessions with HTTP/1.1, no business retries or
production transport changes. A dedicated unit test proves per-worker isolation.
Apply ONLY committed/pushed 025, no bootstrap/reset/V1.
Run `tools/validate_supabase_v2_redemptions.py --env-file .env.supabase-v2-rls.local --allow-staging-writes --robbery`;
then the same without --robbery for shield/revive regression.
Fixtures use phase8f1_validation UUID prefix, synthetic parsed metadata only.
Cleanup unlinks only synthetic receipt/origin graphs and removes all fixtures/Auth.
Independent SQL must confirm zero residue, unchanged old catalog, Storage, views
and helpers, plus exactly one retained canonical voucher.

Advisor preexisting findings are NOT falsely called clean: 24 shaped definer views,
mutable search_path on set_updated_at and three authenticated helper functions.
Cycle table intentionally denies all clients without policies/grants; any no-policy
informational notice must be documented and direct access denial verified.

## Git And Progress

Implementation `4cf21bf` committed/pushed before 025. Validator transport follow-up
and final closure evidence are separate commits; no migration reapplication.
Global before ~56%; after remains ~56% until all gates pass, then ~57%.
Remaining scope includes API, parser, React/Cloudflare, migration/shadow/cutover,
performance, full Launcher/Companion and safe physical save automation.
No Streamlit, V1, Discord, save/PKHeX write, physical ownership transition or dual-write.

## Next

Phase 8G - season/league administration API contract audit. Not implemented here.
PHASE 8F COMPLETE: NO until remote gates are recorded.
