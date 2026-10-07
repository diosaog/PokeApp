# Phase 10.5I - Shop and economy alignment

Closed 2026-10-07. **I DONE / STAGING_DONE_ZERO_RESIDUE.**
[Local evidence](phase10-5i-closure-evidence.json),
[public evidence](phase10-5i-public-evidence.json).

## Entry and implementation

Entry main/origin `e3d4003337e4410dae46ebaa1de632696b1d80a9`, 0/0,
clean tracked tree; H delivered. Fresh remote observation confirmed 30 migrations
through 038 and H's deployed source. No prior migration was edited or replayed.

Wallet and purchase receipts use exact integer strings at the API/browser boundary;
the ledger remains the sole balance truth. Large and negative balances survive
without truncation. Public announced pending promotions show their real dates when
present, cannot be bought early at a promotional price, and transition to the
server's effective price/stock. Private promotion metadata remains private.

Legitimately earned robbery shield vouchers are labeled as rewards in inventory,
never sold, and can target only owned eligible Pokemon through the existing
transactional redemption boundary. Unknown-outcome retry preserves its original
key and body. Finished/archived seasons allow eligible spending with a null
matchday, preserving actual active-window Store Ban rules. No fictitious day,
League reward, new sporting rule or physical save mutation is introduced.

## Economy and reward authority

Persistent season configuration now exposes basic Admin controls for
`badge_reward_coins` (default 4) and `game_completion_reward_coins` (default 12).
Both accept nonnegative integers; zero records a proof claim without a zero-value
ledger row. Config versions take effect at their real configured League window;
changes never reprice previous claims. Old-client config command replay remains
compatible when the new fields were omitted.

Only validated, owned, current parser observations can pay rewards. Private
immutable claims and the existing participant wallet lock make badge deltas and
Champion completion atomic, auditable and idempotent. Unknown/unobserved evidence
pays nothing; observed zero is distinct. Regressed/old/replayed evidence does not
repay badges or create compensating debits. Champion completion pays once per
season/challenge, independently of competitive League finish/title/archive.
Eight badges alone are insufficient. No manual attestation, GET side effect or
migration-time reward backfill exists.

Reader/3 adds nullable neutral `champion_defeated` evidence for the supported native
Gen3/4/5 families. Black/White uses the Hall-of-Fame record rather than the Ghetsis
story flag; inconsistent records remain unknown. Old reader/2 progress can prove
badges but cannot prove completion. Native serialization/reparse fixtures exercise
the flags and BW exception. Sources are the pinned PKHeX 24.11.11
[Gen3 flags](https://github.com/kwsch/PKHeX/tree/24.11.11/PKHeX.Core/Resources/text/script/gen3),
[Gen4 flags](https://github.com/kwsch/PKHeX/tree/24.11.11/PKHeX.Core/Resources/text/script/gen4),
[Gen5 flags](https://github.com/kwsch/PKHeX/tree/24.11.11/PKHeX.Core/Resources/text/script/gen5)
and [BW player data](https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/Saves/Substructures/Gen5/PlayerData5.cs).
PKHeX stays isolated. **Full Launcher/cloud ingestion is still unfinished**:
these backend acceptance hooks do not claim that local Launcher sync uploads saves.

Purchased revive preserves one adjusted death (-0.2) while deducting proven overlap
with the same still-visible Box-8 death. Another revive is rejected until an
intervening alive observation proves a new death. Party or any non-dead box can
prove that transition. Ambiguous/unlinked legacy overlap remains UNKNOWN.
G wipe revival stays two adjusted deaths (-0.4). Closed correction inputs, initial
snapshots, F certificates/Hall and existing memberships are never rewritten.

## Database, tests and delivery

Forward **039_shop_economy_alignment**, applied once as **20261007121317**;
31 remote migration records, all previous 30 identical. New private
`progress_reward_claims` has RLS, no browser table/column access and no update grant.
Sixteen affected helpers are invokers with fixed search paths and service-only
execution. Purchase/promotion/reward/redemption mutations retain ownership checks,
wallet locking, exact replay, conflict checks, concurrency protection and rollback.

FRESH PASS: **732 Python** (713 committed-scope plus 19 pre-existing untracked map
tests left untouched), **33 React**, **12 affected Edge**, native parser/IPC/Launcher,
compile, targeted Ruff, Prettier, TypeScript/production build and deployment dry-run.
Real PostgreSQL 17.11: I ten groups / five rollback boundaries; affected
022/024/025/026/E/G regressions pass, each restoring all 50 public tables exactly.
Four clean migration/bootstrap builds give **12,590 identical schema/grant/owner
lines**. Full unrelated H/F/Cup matrices were NOT RERUN; frozen F/history and
finish concurrency are covered by the fresh affected G regression. PostgreSQL
was stopped after all validators ended. Corrected historical fixture assumptions
and harness-only failures are recorded in the evidence, without hiding cleanup.

Application source **a5d1b627928d2e3fe05c90bcdb51851409e5687d** was committed/pushed before remote writes.
Railway **2402be29-d1ec-4e20-b4c4-3f218ee45893 SUCCESS**, 234 committed API inputs,
then Cloudflare **75e91cf3-123f-4fda-a836-a61e87c9b09f**, version
**8f9deb86-8ebb-4b55-be52-4790ba8decf5**, 100%, both from that source.
Live asset bytes, HTTPS/deep SPA/MIME/CSP/nosniff and exact CORS pass.

Two successful API runs (18 requests total) and four successful real browser
states cover authenticated Shop, inventory, exact balance, configuration and
mobile/desktop rendering. No interception or business mutation. Positive purchase,
voucher/reward and post-League mutation proof is **LOCAL ONLY**. No voucher or
progress was fabricated in the owner season. Final comparison preserves all 55
original scoped tables; the new proof table is empty, and all 56 post-apply tables
and 31 migration records are identical to the post-apply baseline. Owner Auth/PIN/
admin, seasons, results, ledger, memberships and Team Locks remain unchanged.
Only owner Auth session activity is excluded from row equality, with full baselines
and separate stable credential/identity checks. No Storage bytes were touched.
Advisor **24 ERROR / 5 WARN / 138 INFO**, zero new or removed ERROR/WARN.

## Files, limitations and next step

Changes cover API/read models and economy repositories, neutral parser/adapter,
039/bootstrap/reset tooling, Shop/inventory and two basic Admin controls, generated
API types and affected tests. The application commit lists all 40 paths; closure
documentation is committed separately. Protected guide and unrelated untracked
ZIP/map/validator files remain untouched and unstaged.

No per-player HTTP loop or broad new query invalidation was added. Inventory adds
one bounded eligibility RPC. Single hosted samples: Shop 2.21-3.31 s, inventory
2.29-2.59 s, overview 3.83-4.82 s. These are M/Phase 14 measurement candidates,
not a performance benchmark or a global refactor.

Antonio can inspect the wallet/upcoming promotions in Tienda and the two reward
values in Administration > Configuration without saving changes. Voucher canje
can be exercised when a legitimate voucher and eligible own target exist; do not
create owner fixtures merely for this check. No further owner test is required to
close I. J already has the two basic controls; only broader Admin humanization
remains in its scope. Normal lifecycle authority, residual title/finalist rules,
Team Lock cutoff, scouting, League-DQ/Cup interaction and future game milestones
retain their outstanding owner-decision scope.

**NEXT: J, awaiting explicit owner instruction. STOP after I.**
Phase 10.5 IN PROGRESS; **Phase 11 NOT READY / NOT STARTED**.
Final application HEAD is above. Documentation closure HEAD is the subsequent
commit containing this report and handoff; obtain its exact hash from Git.
