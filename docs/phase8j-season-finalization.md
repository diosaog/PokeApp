# Phase 8J: Season Finalization, Archive And Hall

Implementation from `e2628c5`, approved D6=A/D7=A; D8 remains deferred.
Execution evidence and completion status: [delivery report](phase8j-completion-report.md).
This is isolated V2 API work, not a Streamlit/V1 change or deployment.

## Explicit Commands

Verified JWT -> enabled trainer -> is_admin. No name or participant requirement.
All three POSTs under `/v1/admin/seasons/{season_id}` require Idempotency-Key:

| Suffix | Strict body | Transition |
| --- | --- | --- |
| `/finish` | expected_revision | ACTIVE -> FINISHED |
| `/archive` | expected_revision, optional label | FINISHED -> ARCHIVED |
| `/discard` | expected_revision, reason, confirmation="DISCARD" | unused DRAFT -> DISCARDED |

Revisions are strict nonnegative integers, labels trimmed 1-120 characters,
reasons trimmed 1-500. Unknown authority/state/source fields are rejected. No
generic PATCH, reopen, reactivation, regeneration or next-season endpoint.

API returns typed IDs/state/revision/timestamp, not raw SQL, Auth IDs or team/save
payloads. Scope, actor, requested operation/state and archive/Hall IDs are checked.
401/403 auth; 404 scope; 409 state/source/dependency/CAS; 422 malformed; unknown
backend errors sanitized 503. No automatic mutation retry.

## Finish And Review

027 final close continues to leave ACTIVE. Review lasts until explicit finish;
there is no timer. Under the established locks, finish requires the current
pointer to a CLOSED configured final day, all days 1..N CLOSED with no holes or
extras, no committed future configuration beyond that final day, valid historical
pairings/eligibility and exact current/immutable snapshot revision agreement.
Latest official snapshot schema must be 2. Every eligible standing is present once,
positions are contiguous, round reward ledger totals agree, and the committed
last-B reward exists where the snapshot requires it. Used gifts remain valid facts.
Missing/inconsistent source rejects, never fabricates missing competition/rewards.

Finish changes only lifecycle/timestamp, setup revision, private event and receipt.
It does not archive, grant 12 coins, alter awards/locks/saves, clear the final
pointer or transfer individual progression. Existing ACTIVE guards reject later
competitive/config/setup/status mutations, including corrections. Successful old
idempotent receipts can still replay without a new write under their old contracts.
024/025 redemption eligibility is not globally changed by season finish/archive.

## Frozen Historical Authority

Relational seasons, players, configs, memberships, rounds, matches, current and
immutable snapshots, movements, rewards and Team Locks remain canonical. None is
deleted/reset by archive. The archive JSON is a required frozen audit/export
package for this endpoint, not a replacement database or mutable source of truth.
Failure to serialize/store it rolls back the entire archive transaction.

Existing `season_archive_snapshots` gets typed final snapshot revision provenance,
label and SHA256 checksum. Existing `hall_of_fame_entries` gets archive/snapshot/
historical Team Lock FKs. Existing unique season archive and season/competition
Hall constraints ensure exact-once. No new tables or second lifecycle framework.

Package version 1 includes season identity/label/times, safe roster and status
boundaries, explicit configuration fields, final official standings and round
summaries, movements, League winner/finalist and sanitized historical public team.
No Auth UID, arbitrary metadata, raw/parsed save, private Team Lock, sanction notes
or internal receipts. It does not copy whole competitive snapshots or their input
payloads. SHA256 covers the canonical stored JSON text; provenance/checksum remain
typed archive columns outside the package to avoid a recursive checksum.

League champion/finalist come from positions 1/2 of the LAST official closed
snapshot, not a re-ranking of current UI, current saves or mutable cumulative data.
Full final standings in the package retain the supported podium positions.
Hall is created only at archive, with the same timestamp and provenance. No second
writer or generic Hall regenerate API. Existing pre-029 Hall/archive rows are not
silently overwritten: a conflicting existing artifact fails explicitly.

## Champion Team

Narrow legacy source: `app/season/archive.py::_team_snapshot_for` uses final lock,
then earlier lock, then a live legacy trainer snapshot. V2 permits the first two
only: champion's final CLOSED day lock, otherwise most recent valid CLOSED
historical lock within that season. UUID order breaks any tie. No live-save fallback.

The stored public array must contain six named species; an invalid array is
skipped in favor of an earlier valid lock. No valid source means `[]` with NULL
source_team_lock_id, supported by the existing non-NULL JSON column. Never invent
a team. A recursive allowlist reprojects public species/nickname/level/gender,
types/item/move names/sprite/form/shiny fields. Private fields and nested metadata
are dropped even if erroneously present inside public JSON. Private snapshot is
never selected. If the final competition is empty, finish can record completion,
but archive fails HISTORICAL_SOURCE_INVALID because existing League Hall requires
a champion. This is not an invented no-winner Hall record.

## Cup Hall Boundary

Narrow sources: `007_competitions.sql`, the 8G archive/Hall audit, and
`app/season/archive.py::_cup_hall_entries`. Legacy has format-specific closed
state/winners. V2 `cups.status` alone does not certify finality of a bracket;
`cup_matches` lacks a typed final marker, standings positions are nullable and
not unique, doubles sides may lack a trainer, and Hall uniqueness is per
season/type although several Cups of a type can exist. No V2 Cup close API yet
guarantees winner provenance across these shapes. Therefore deterministic generic
Cup synchronization is NOT safely supported in 8J. Existing Cup/Hall rows remain
untouched; package explicitly says `pending_cup_api`. League archive is not blocked.
Cup administration/finalization must define this contract in its own API work.

## Logical Discard And Visibility

DRAFT only. Pure roster/default stats/config/divisions/membership setup can remain.
Any prepared day, competition/snapshot/movement, ledger/purchase/redemption,
promotion, save/identity/Pokemon or trainer flag, robbery cursor, Cup/Trial/penalty,
archive/Hall, selected save, inactive participant, nonzero badges/wipe count blocks
with DISCARD_NOT_ALLOWED. No destructive legacy wipe and no global reset.

Public season view already excludes discarded. 029 wraps existing season-scoped
public projections and Cup child views with parent visibility checks, preserving
columns, grants and 018 security options. Restrictive SELECT policies on draft
setup tables prevent alternate direct discovery while preserving admin audit.
Private owner-only purchase/redemption/save/history reads retain their existing
contract, even for pre-029 imported discarded seasons that could not be discarded
through this new endpoint. Activity's extra restriction covers public facts only;
its pre-existing owner/admin policies still govern private redemption events.
Policy parent lookup uses existing safe `public_seasons`/`public_cups` projections:
raw `seasons` is admin-only under RLS and would hide valid owner history as well.
This regression was caught by the unchanged 019 SQL owner-read tests and fixed.
The full 024 regression also verified private events in an imported discarded
season; restrictions were narrowed rather than weakening that prior contract.
Backend-only tables and private owner data receive no unnecessary policies.

## Atomicity And Immutability

026 receipt namespace `lifecycle` hashes explicit operation and body with
actor/season/key. Same semantics replay; changed command/label/revision/reason
under the same key conflicts. setup_revision advances exactly once, roster and
config revisions do not change. Stale CAS has no writes.

Principal SHARE -> receipt advisory -> season NO KEY UPDATE -> UUID-ordered
players -> numbered days/ordered matches -> snapshot/history -> Team Lock/archive/
Hall -> event/receipt. Compatible with 019-028; no Python mutex or inverse order.
Archive lifecycle/package/Hall/revision/event/receipt are one transaction; finish
and discard use the same atomic framework. Events SEASON_FINISHED, SEASON_ARCHIVED,
SEASON_DISCARDED are private/admin, not Discord notifications.

Hall/archive UPDATE triggers reject mutation even by service. Browser table and
column INSERT/UPDATE/DELETE are revoked; RPC/helpers are invoker, fixed-path and
service-only. Existing privileged synthetic cleanup can delete its own artifact
graph; no deletion endpoint or test-only production bypass is introduced. Trusted
service-role maintenance is not equivalent to browser/admin API access.

## Validation And Remaining Work

28 new unit tests preserve the earlier 403 and extend the admin route inventory
19 -> 22 without removing authorization assertions. Shared PostgreSQL/staging
fixtures cover real transitions/races/privacy/denials and artifact preservation.
Ten local rollback injections cover all required stages plus receipt failure for
EACH command, comparing all public-table contents. No failure triggers on staging.
Full 019-028 regressions, migrations/bootstrap schema parity, unit/compile/diff
checks precede implementation push and application of ONLY committed 029.

After 8J completion, remaining critical API work before Phase 9 includes Juicios/
sanctions (authoritative verdict and penalty/economy effects) and Cup finalization
with certified Hall sources. They remain legacy islands, with no router in
`app/api/routes`. A scoped contract audit is next, not automatic implementation.
Save upload/selection/parser ingestion still needs its own approved boundary;
Phase 9 is specifically parser isolation and is not started by this task. D8 stays
deferred. No runtime switch, React, Companion, PKHeX writes or V1 changes.
