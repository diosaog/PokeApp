# Phase 8I: Participant Status Administration

DONE local + real Supabase V2 staging, 2026-09-24. Implementation follows the
approved 8G audit and 8I instruction, starting from `b34bd54`. 403 unit tests,
24 shared groups, eight local rollback points and full regressions PASS.
Validation/commit/staging evidence is in the [completion report](phase8i-completion-report.md).
028 is already applied as `20260923220301`; do not reapply it on this staging.

## Product Boundary

Three distinct, permanent season statuses: `active -> retired`, `active -> abandoned`,
`active -> disqualified`. No generic PATCH, reactivation, inactive-to-inactive edit,
late join, season finish/archive/Hall or implicit refund. `globally_enabled` stays
account-level; `robbed` stays a mutable trainer flag. An inactive player remains a
historical participant and retains all previously earned official facts.

Only ACTIVE seasons with the authoritative current day SCHEDULED qualify. OPEN
returns ROUND_OPEN; final CLOSED, missing/cancelled pointer returns
MATCHDAY_NOT_SCHEDULED. DRAFT roster removal remains 026, not this operation.

## API And Authority

POST `/v1/admin/seasons/{season}/participants/{participant}/retire`, `/abandon`,
`/disqualify`. The resource UUID is a season_player, not a global trainer.
Verified Supabase JWT, globally enabled trainer, `is_admin=true`; admin need not
participate. No name-based or client-provided authority. SQL repeats the check.

Required `Idempotency-Key`; strict body has exactly `reason` (trimmed, 1-500 chars)
and `expected_roster_revision` (strict nonnegative integer). Actor, destination,
current day, effective round, old status and timestamp are derived on the server.

Safe receipt: operation/event IDs, season/participant, old/new status, reason,
effective day ID/number, actor trainer ID, timestamp, roster/setup revisions and
replay marker. No Auth UID, save payload, Pokemon strategy or SQL diagnostics.
The HTTP boundary revalidates receipt scope, actor and destination and filters extras.

Errors: 401 JWT; 403 disabled/non-admin; 404 season/participant scope; 409 state,
dependencies, CAS/idempotency; 422 malformed; 503 sanitized unknown backend failure.
Stable business codes include SEASON_NOT_ACTIVE, PARTICIPANT_NOT_FOUND,
PARTICIPANT_ALREADY_INACTIVE, PARTICIPANT_HAS_CURRENT_TEAM_LOCK, ROUND_OPEN,
MATCHDAY_NOT_SCHEDULED, DEPENDENT_DATA_EXISTS, ONGOING_COMPETITION_DEPENDENCY,
STALE_REVISION and IDEMPOTENCY_CONFLICT. No automatic mutation retries.

## Exact Historical Boundary

028 adds typed `status_effective_matchday_number`, reason and actor to
season_players; existing `left_at` records server time. The boundary is the CURRENT
scheduled round, not a client number and not inferred from timestamps. Recorded
status evidence is update-immutable. Existing pre-028 import fixtures may retain
NULL evidence; they are not certified as competitive status transitions.

Membership eligibility is the intersection of its original inclusive assignment
range with `round < eligibility_ends_before_matchday_number`, if present, and the
player's status boundary. Original assignment rows are never deleted by a status
operation. Completed historical ranges are unchanged. Current/future assignments
gain the exclusive cutoff. This can represent an EMPTY range when the player
leaves before the first scheduled round of an assignment, without fabricating
round zero, violating the original inclusive-range constraint, or deleting evidence.

Example: assignment `[2, infinity)` plus cutoff `2` records an assignment that
never became competitively eligible. Assignment `[1, infinity)` plus cutoff `3`
retains eligibility for rounds 1 and 2. `participant_memberships_at` is the
backend query authority for this intersection, including historical queries.

Two existing safe public views append ONLY their corresponding round boundary;
admin reasons/actors remain outside public projections. Existing 018 view security
options, row access rules and all other view definitions are preserved. The admin
setup read/DTO also exposes both boundaries, so consumers need not guess from dates.

## Scheduled Reconciliation And Divisions

The current day ID/number/config/pointer never change. Validate canonical pairs
before the mutation; delete ONLY unpublished pairs involving the departing player;
validate the remaining canonical all-vs-all set. Surviving match IDs, order,
assignment and Team Locks are untouched. No fake opponents, forfeits, standings,
rewards, snapshots or movements are created by retirement.

Config A/B capacities remain original setup targets. Remaining divisions may be
smaller or empty; no automatic fill/rebalance at status change. A singleton has
zero matches; an empty division has no standings or last-B gift. Even all-inactive
does not automatically finish the season. Existing domain ranking/rewards use the
actual surviving A then B ranking; existing movement clamps to both division
lengths at the NEXT normal close. No mechanics code or scoring config changed.

027 had assumed every registered participant remained active. 028 replaces only
the affected eligibility checks/context/close helpers: historical eligibility,
surviving standings count, empty B and preserving cancelled assignments. External
correction fingerprint includes typed status boundaries once present: a new baja
blocks correcting the older closed round rather than cascading backward. For a
season with no 028 transition, the old fingerprint is byte-compatible. New reduced
rounds still use 027 atomic rewards, immutable snapshots and next-day preparation.

## Dependencies

The departing player's Team Lock on the current scheduled day blocks the operation.
019 locks bind player/day/save/snapshots, not opponent/match IDs; hence another
player's exact lock remains valid when the departing player's pairs are removed.
No lock deletion/replacement and no 019 change.

Any current winner/non-scheduled match/result code, snapshot/history, reward,
movement, current-day penalty/trial or later prebuilt day rejects. No backward
repair. Cup dependencies are narrowly relational: a same-season draft/active Cup
with the trainer as a side blocks; a NULL trainer side is also conservative because
arbitrary doubles/team metadata is not a supported membership contract. Finished/
archived Cup history stays intact. Generic non-day Trial cases and penalties are
retained, including unresolved cases; a season status change does not erase their
accused/voter identities or constitute a verdict. No bracket rebuilding.

## Robbery, Economy And Saves

Legacy evidence: `app/domain/services/trainers.py::apply_status_transition` clears only
the current robbed projection, and `reset_robbed_cycle_if_complete` explicitly
does nothing for an empty active set. 028 applies the same projection rule while
using 025 durable redemptions as cycle truth, not legacy mutable flags.

Under the same season/player locks as 025, clear the inactive trainer's `robbed`
flag/payload. If a cycle exists and every REMAINING active trainer is already a
victim in that cycle, increment it once and set history_watermark_id to its actual
last_redemption_id. Clear current robbed flags for remaining active trainers just
as 025 does. No new cursor is fabricated when no robbery occurred; no vacuous
advance with zero active players. Replay cannot re-advance. Historical redemptions,
voucher purchases, physical pending effects and Pokemon entity flags stay intact.

021/022 future purchases and 024/025 future redemptions already reject inactive
participation. This includes replay requests where those contracts check current
eligibility first. Prior purchases/ledger/entitlements are NOT cancelled, refunded,
rewritten or deleted. No save, parsed JSON, entity identity or physical bytes are
changed. No new save API or Companion capability and no Discord emission.

## Transactions And Security

Reuse 026 receipt/revision infrastructure. Shared `participant_status` scope by
actor/season/participant/key includes explicit operation in the canonical hash.
Same key/body/operation replays the original receipt before state/CAS checks;
same key but another status/reason/revision conflicts. Different key for an already
inactive player returns PARTICIPANT_ALREADY_INACTIVE. Roster/setup each advance
once; current day revision/results_revision also advance to invalidate stale editors.

One transaction: status/evidence -> membership boundary -> scheduled pairs/day
revision -> current flags/cycle -> roster/setup revision -> private ADMIN event ->
durable receipt. Failure at any step rolls back all public-table changes.

Lock order: admin principal SHARE -> 026 receipt advisory -> season NO KEY UPDATE
-> ordered season_players FOR UPDATE -> current day -> ordered memberships/matches
-> trainer flags/cycle -> event/receipt. This serializes with 019-027 using real
database locks, not Python mutexes. No reverse season/player ordering is introduced.

028 adds no tables. 40 public tables retain RLS, 37 views remain. New helper/RPC
functions are invoker, fixed search_path, service-only EXECUTE; PUBLIC/anon/
authenticated cannot invoke them. Existing 026 browser table/column write revokes
also cover the new status columns. Admin browser status writes are still denied.

## Validation

Use `.venv-api` dependencies and the isolated `tools/run_unit_tests.py` runner.
Local PostgreSQL reset is allowed ONLY on loopback `pokeapp_v2_validation_*`.
`tools/validate_supabase_v2_schema.py` runs 001-028/bootstrap, prior regressions and
the new shared scenarios plus eight exact full-data rollback injection points.
`tools/validate_supabase_v2_participant_status_sql.py` is the focused local runner.

Staging runner: `tools/validate_supabase_v2_participant_status.py --env-file
.env.supabase-v2-rls.local --allow-staging-writes`. Pinned V2 only, synthetic
`phase8i_validation_<uuid>` data and temporary Auth users, real JWT -> API ->
PostgREST. 027 regression plus earlier setup/Team Lock/purchase/robbery gates follow.
No failure triggers, reset/bootstrap, real trainer changes or save bytes remotely.
028 was applied after full local green and implementation push `baecb8a`.
Real validation and independent cleanup passed; no real trainer/catalog/Storage
change and no new Advisor findings. Do not repeat 028 or bootstrap/reset staging.

The legacy Streamlit/V1 runtime is unchanged. No deployment, cutover or dual write.
8J finish/archive/Hall is next; no 8J implementation is included.
