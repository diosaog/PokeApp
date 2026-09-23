# Phase 8H: Competitive Matchday Operations

## Scope And Product Decisions

Additive 027 follows the approved [8G audit](phase8g-season-league-admin-audit.md)
and [026 setup contract](phase8g1-season-admin-api.md). No change to 001-026,
Streamlit/V1, authentication, domain mechanics, Discord, physical saves or deployment.

- D4=A: correct only the most recent closed round inside a safe window, with
  immutable revision evidence and compensating economy facts. No cascading repair.
- D5=A: cancel editing returns the SAME current round OPEN -> SCHEDULED, preserving
  canonical pairs, pointer and Team Locks. Existing winners/snapshots/movements block it.
- D6=A: final competitive close leaves season ACTIVE and pointer at its final closed
  round. No fictional next round, finish/archive/Hall or individual 12-coin bonus.
- No participant retirement/abandon/disqualification/late join (8I); no 8J lifecycle.

## HTTP Contract

Prefix: `/v1/admin/seasons/{season_id}/matchdays/{day_id}`.
Every route requires a verified JWT mapped to a globally enabled `is_admin` trainer.
Participation and display name are irrelevant. SQL rechecks the admin under lock.

| Method / Suffix | Body | Outcome |
| --- | --- | --- |
| GET (no suffix) | none | Safe day state, CAS revisions and match IDs/players/winners |
| POST `/open` | expected_revision | Current SCHEDULED -> OPEN, timestamp, private event/receipt |
| PUT `/results` | expected_results_revision, results | Edit/remove winners in current OPEN round |
| POST `/cancel-editing` | expected_revision, reason | Safe OPEN -> SCHEDULED, same round/pairs/pointer |
| POST `/close` | expected_results_revision | Atomic official close and optional next round |
| POST `/correct` | expected_snapshot_revision, reason, results | Safe revision + compensation |

All five mutations require `Idempotency-Key`. `results` is a nonempty batch of
`{match_id, winner_season_player_id}`; null removes a winner only while OPEN.
Correction requires non-null winners. UUIDs, strict nonnegative revision integers,
bounded nonempty reasons and unique match IDs are validated; batches are sorted by
ID for stable hashing. Unknown fields (actor, plan, rewards, pointer, etc.) fail 422.

401 invalid/missing JWT; 403 non-admin/disabled; 404 scoped resource not found;
409 business/CAS/dependency conflicts; 422 malformed request; 503 sanitized backend
failure. Receipts contain operation/event IDs, season/day/state, revisions, pointer
and replay flag, never Auth IDs, SQL, private teams or parsed saves.

## Revisions And Replay

- `matchdays.revision` and `results_revision` begin at zero. Each confirmed open,
  result batch, cancel, close or correction advances both. Reads/rejections do not.
- Two editors at the same base cannot overwrite one another. A result edit racing
  close has one accepted transition and a stale/state rejection for the other.
- Existing 026 `admin_operation_receipts` stores exact public-request hash and safe
  original response. Scope includes actor, operation, season/day and key.
- Same key/body/actor replays even after pointer advancement; changed content
  conflicts. Different admins have different receipt namespaces, but day locks/CAS
  still prevent duplicate close. No automatic mutation retries in adapters.

## Planning And Atomic Commit

Close/correct uses two backend-only RPC calls. `api_admin_matchday_context` locks
and revalidates the authoritative inputs, returning their SHA256 content hash.
`app/application/matchdays.py` uses the existing pure domain services:
`rank_division`, `build_standings_from_rankings`, `calculate_division_movements`,
`last_b_steal_award`, `select_shop_promotions`, `discount_price`.

`api_admin_matchday` reacquires the locks and hashes fresh inputs. Any intervening
change rejects with STALE_INPUTS; callers must explicitly refresh/reconsider. The
client never supplies a plan/hash. Trusted backend plans are checked against exact
participants and configured reward/point amounts. Ranking is not duplicated in SQL.

All business writes are ONE SQL transaction:
immutable revision -> current snapshot -> ledger -> free purchase -> movement /
membership ranges -> next day/pairs -> promotions -> pointer -> closed status ->
private event -> receipt. Any failure rolls all of them back.

Lock hierarchy: principal SHARE -> receipt advisory -> season NO KEY UPDATE ->
all relevant players ordered by UUID FOR UPDATE -> day -> ordered matches ->
ordered configs SHARE -> catalog SHARE / promotion rows UPDATE -> derived facts.
Reuse of 026 season lock serializes against 019/021/022/024/025 operations without
Python mutexes. Context lock release is safe because the commit revalidates hashes.

## Ranking And Frozen Evidence

Snapshot schema version 2 records config/version, exact players/divisions, results,
standings, penalties, ranking inputs, movement outcome, close time and revision.
Trainer slug is frozen as stable domain tie-break key; ranking IDs are season-player
IDs. Two-player ties use head-to-head; larger ties use adjusted deaths then that key.

Adjusted deaths follow existing legacy inputs: current authoritative Box 8
observations + revive count + twice `season_player_stats.revived_after_wipe`.
Revive count is the maximum of applied revive redemptions and used revive purchases
to avoid counting the same use twice. The new typed wipe count defaults zero and
is backend-only; no manual stats UI/API is introduced. A selected save without an
identity revision fails RANKING_INPUTS_UNAVAILABLE, rather than guessing. No selected
save retains the existing zero-death fallback.

Applicable admin/resolved-trial penalties are frozen with their trainer/season/day
scope. Points and configured round coin rewards remain separate from penalty
summaries; cumulative sanctions are not subtracted again every round. No mutable
balance column or generic manual standings editor is added. Season points can be
derived from official latest closed snapshots and their frozen penalty evidence.

`matchday_snapshot_revisions` retains every immutable revision. `matchday_snapshots`
is only the latest official projection; its update requires the next revision and
matching immutable content/config. Historical pre-027 imports keep their old
contract and cannot enter the new correction flow without 8H evidence. Backend
fixture cleanup can delete synthetic rows; browsers cannot write either surface.

## Economy And Last-B Reward

Positive configured `coin_rewards` become `coin_transactions` credits; zero omits
the row. Unique (day, player, snapshot revision) plus receipt/CAS dedupes rewards.
Source FK/reference identifies exact immutable revision. No balance mutation.

Legacy evidence: `app/liga/ranking.py::finalize` grants the configured last-B free
Robar purchase even at final close. 027 uses ONLY canonical `robar_pokemon` ShopItem,
not a fuzzy display name and not `robbery_shield_voucher`. Missing canonical item
fails REWARD_ITEM_UNAVAILABLE. Quantity 1, unit price 0, pending, reward acquisition,
no debit/stock claim, typed originating day/revision/player and durable uniqueness.
025 paid/voucher provenance validation remains intact; a separate constrained
matchday-reward branch checks the snapshot's last-B recipient.

## Movement, Next Round And Promotions

Non-final close applies existing A/B promotion/relegation count, records stay/move
outcomes, ends old membership ranges at the closed number and begins new ranges
at number+1. It prepares exactly that scheduled round using effective next config,
all unordered within-division pairs and server pointer advancement. It does not
open the next round. Unexpected pre-existing next-day data is rejected, not overwritten.

Final close has no movements or next round. Final rewards still apply and ACTIVE
remains available for review; 8J owns actual finish/archive/Hall.

Narrow legacy evidence: `app/liga/ui.py` expires current/earlier discounts;
`app/tienda/discounts.py` prepares next-round offers with existing domain quota /
weighting, immediately announced and activated after 24 hours. 027 mirrors those
transitions atomically: pending next offers, stock 2 normal / 1 mega, no stock debit
on close, current/older pending/active/exhausted -> ended. Server RNG is seeded by
day UUID so repeated planning is stable. Existing next offers are not rerolled;
correction preserves them. No Discord delivery or changes to 8D/8E purchase rules.

## Safe Correction Window

Most recent closed day only, original config and frozen ranking inputs, nonempty
reason and snapshot CAS. Old result history is retained in immutable revisions.
The prepared next round must remain adjacent and SCHEDULED with no winners,
locks, snapshots, movements or penalties. Even opening it closes this first-version
window until a genuinely safe cancel restores SCHEDULED. No cascade engine.

Additional conservative content hash covers external purchases/ledger/redemptions,
locks, save metadata, identity revisions, flags, stats, penalties and competitions.
Changed facts reject CORRECTION_WINDOW_CLOSED regardless of transaction timestamps.
Any season-linked Cup, including one already present at close, blocks correction:
its internal competition dependencies are not a supported cascade in this phase.
Pending physical effects and used/redeemed free rewards also reject. No save bytes
are read/written by this phase; hashes are not private payload projections.

Allowed correction appends revision N+1, signed compensation ledger differences
with reason/source, and rejects unsafe negative balances. Never edits/deletes old
ledger rows. If last-B changes, the untouched pending gift is auditably cancelled
with revision/reason and a new pending gift is issued; same recipient keeps the
original gift. Completed purchases/redemptions are never rewritten.

Provisional next pairs/memberships/current movement projection can be rebuilt only
inside that window. Prior official movement outcome remains in the old immutable
snapshot. Final-round correction has no next-day side effects. Replay never doubles
compensations, cancellations, gifts or new revisions.

## Validation And Operations

`tools/validate_matchday_fixtures.py`: shared real DB/API fixture scenarios;
`tools/validate_supabase_v2_matchdays_sql.py`: loopback-only rollback injection;
`tools/validate_supabase_v2_matchdays.py`: pinned opt-in V2 JWT/API/PostgREST tests.
The latter requires `--env-file .env.supabase-v2-rls.local --allow-staging-writes`.
Secrets are never logged. Unique `phase8h_validation_<uuid>` prefixes and explicit
cleanup isolate synthetic data; independent SQL must verify zero Auth/DB residue.

027 is incremental, applied once. Never replay bootstrap/reset on existing staging.
`bootstrap.sql` is generated from 001-027 for an EMPTY V2 database only.
Local failure triggers must never be installed in staging.

Security: new history table has RLS, no browser grants/policies; 027 helpers/RPCs
are invoker, fixed search_path, service-only EXECUTE. Table/column browser writes
to official snapshots/movements/ledger are revoked without widening read access.
Private ADMIN events share the transaction. Existing Advisor findings remain a
separate launch-security follow-up; do not call the project globally clean.

Exact commands, counts, migration version, incidents, cleanup and git delivery:
[completion report](phase8h-completion-report.md).
