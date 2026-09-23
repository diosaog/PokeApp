# Phase 8F.1 / Full 8F Closure

## Result

DONE: all four effects validated locally and in Supabase V2 staging.
The previous two-effect report is preserved in Git at `2bd0365`.
Remote validation and independent zero-residue cleanup passed on 2026-09-23.

## Checkpoint

- Start: main / `2bd0365` / origin/main 0/0.
- Implementation: `4cf21bf api: complete atomic robbery and reward voucher redemption`.
- Validator: `d356bc1 test: isolate concurrent staging validator HTTP sessions`.
- Both pushed to origin/main; final documentation-only closure hash is in Git/delivery.
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

- Unit suite: 318 PASS (311 baseline plus seven API/schema/validator tests).
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
Applied ONLY committed/pushed 025, no bootstrap/reset/V1. Do not reapply it.
`tools/validate_supabase_v2_redemptions.py --env-file .env.supabase-v2-rls.local --allow-staging-writes --robbery`:
RESULT ok checks=17, Auth cleanup PASS. Successful run:
`phase8f1_validation_7edb684878e148529dc01947019b4f12`.
The same command without --robbery: RESULT ok checks=19, Auth cleanup PASS;
`phase8f_validation_0380178e697146859ab3b8b4d2c56998`.
Fixtures use phase8f1_validation UUID prefix, synthetic parsed metadata only.
Cleanup unlinks only synthetic receipt/origin graphs and removes all fixtures/Auth.
Independent SQL confirmed zero rows in 18 fixture business tables plus Auth users,
identities and sessions. Original 10 trainers and 3 Storage objects preserved;
62 catalog rows, exactly one canonical voucher. Prior 61 rows unchanged except
the new acquisition_mode default. 37/37 tables have RLS and all 37 views preserved.
Checksums:
- old catalog excluding new column: f1cbe1216934d72dd5a1096d939dbf7a (unchanged);
- views: d4da4cee7449e34f3ab16eeb74819c3d (unchanged);
- buckets: a1bad2c31b4a666ab2a70cd1519f5a69 (unchanged);
- api_redeem_purchase: 1a0666e2b105044215860e375ee6af96 (local=remote);
- check_purchase_acquisition: 7168cec18d5b9ad69ecca8c3651b420e (local=remote).
All three purchase functions and both identity functions match preflight MD5s.
Anon/authenticated cannot execute either new/current mutation function; service_role
can. Invoker and fixed empty search_path verified remotely. Browser/admin/anon
direct writes and cycle reads denied in real fixtures. No deployment or V1 access.

Advisor preexisting findings are NOT falsely called clean: 24 shaped definer views,
mutable search_path on set_updated_at and three authenticated helper functions.
New finding: one INFO [RLS enabled, no policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
on robbery_cycles, justified: backend-only, no browser grants/policies, RLS deny-all
verified. No new ERROR/WARN. Existing findings remain:
[24 definer views](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view),
[one mutable search_path](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable),
[three permitted auth helpers](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).
This is not a claim of an empty Advisor report or a global production transport fix.

## Git And Progress

Implementation `4cf21bf` committed/pushed before 025. Validator transport follow-up
and final closure evidence are separate commits; no migration reapplication.
Global BEFORE ~56%; AFTER ~57%; CHANGE +1 percentage point (approximate):
the remaining two redemption effects and their security/staging gates are now closed.
Remaining scope includes API, parser, React/Cloudflare, migration/shadow/cutover,
performance, full Launcher/Companion and safe physical save automation.
No Streamlit, V1, Discord, save/PKHeX write, physical ownership transition or dual-write.

## Next

Phase 8G - season/league administration API contract audit. Not implemented here.
PHASE 8F COMPLETE: YES. All four internal effects are DONE; physical automation remains out of scope.
