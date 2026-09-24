# Phase 8K.1 — Authoritative trials and sanctions

Product contract supersedes the audit's proposed T1–T5 decisions. Migration 030
extends existing V2 cases, penalties, ledger, receipts and competitive captures.

**Discord is the voting/decision venue; PokeApp records the agreed result and
applies its mechanical consequences.** Entry is manual. There is no Discord
integration, application voting, jury, quorum, majority calculation or proxy vote.
Historical votes remain historical data and never determine these decisions.

## Authority and lifecycle

Verified JWT → globally enabled trainer → active season participant. Any such
participant can create, record or correct a case, including the creator or accused
acting as the recorder. Recording is not voting. Admin status and names confer no
recording authority; an admin outside the roster cannot mutate a case.

The server owns UUID, season, creator, accused, monotonically allocated case number,
timestamps and revision. A per-season transactional counter serializes allocation;
cancellation never frees a number. Imported cases are not assigned invented numbers,
verdicts or effects and cannot enter the new mutation workflow without reliable
authoritative provenance.

New cases are `open` (discussion). Only their creator may replace title, public
summary, visibility and private evidence while open, or cancel them logically with
a reason. Explicit `guilty` produces `resolved`; explicit `not_guilty` produces
`dismissed`. A guilty warning with no mechanical sanctions remains guilty.
Resolved cases use a correction, never proposal editing, cancellation or deletion.

All mutations require current participant eligibility, including administrative
corrections. Draft/discarded seasons reject judicial commands. Active, finished and
archived seasons permit administrative records; new/increased mechanical effects
require ACTIVE. Open cases never become a finish/archive prerequisite.

## API

All paths start `/v1/seasons/{season_id}/trials`.

| Method/path | Contract |
|---|---|
| GET collection | Safe visible cases, private detail only for authorized parties |
| GET `/{case_id}` | Same visibility rules; inaccessible case is 404 |
| POST collection | Title, summary, accused, visibility, optional private evidence |
| PUT `/{case_id}/proposal` | Creator-only details replacement, case CAS |
| POST `/{case_id}/resolve` | Explicit verdict, decision summary, full typed sanctions, case CAS |
| POST `/{case_id}/cancel` | Creator-only unresolved cancellation, reason, case CAS |
| POST `/{case_id}/correct` | Reason, explicit corrected verdict and full replacement sanctions, case CAS |

Every mutation requires `Idempotency-Key`. Unknown fields and client-controlled
actor, ledger IDs, applied flags, sanction ranges or effective round IDs are rejected.
There is no generic PATCH, delete, vote, jury or arbitrary penalty CRUD endpoint.

## Sanctions and timing

At most one entry per supported type; combine amounts/notes. `not_guilty` cannot
carry a mechanical sanction. Amounts are positive; coins are strict integer values
up to 2,147,483,647, points exact decimals with at most two places and a maximum of
9,999,999,999.99. Notes are bounded text; duration is 1–1,000 official matchdays.

| Type | Effect |
|---|---|
| `store_ban` | Immediately blocks existing 020–022 shop operations; server computes official round range |
| `coins_reduction` | One full signed ledger debit, even if the balance becomes negative |
| `points_reduction` | Cumulative fact captured from the next eligible unclosed League round |
| `pokemon_release` | Private administrative note only |
| `other` | Private note/warning only |

A scheduled or open current round counts as the first Store Ban round when it
closes. A one-round ban ends at that close, including a final CLOSED current pointer.
An N-round ban ends at its Nth official close. Insufficient remaining rounds reject
the entire decision with `STORE_BAN_ROUNDS_UNAVAILABLE`. Later configuration cannot
shorten the League below an outstanding authoritative ban's required end round.
Legacy 020 NULL/inclusive range semantics are preserved for legacy rows.

Coins use ledger provenance linking case, decision revision and current/previous
effect. Income compensates outstanding debt through the existing ledger. Purchases
already committed remain unchanged. No mutable balance or automatic refunds.

Points require an eligible future competitive capture; otherwise
`NO_FUTURE_POINTS_CAPTURE` rejects the whole decision, including other effects.
SQL captures cumulative net sanctions as decimal text through the JSON planning
boundary. `public_sanctioned_points` sums earned points from official schema-2
captures, then subtracts the latest captured cumulative reduction and death penalty
once. Rewards, match winners, movements, Last-B and League Hall remain unchanged.
Imported captures are not silently promoted to authoritative schema-2 history.

Notes never mutate Pokémon, identity, ownership, Team Lock, saves or Companion work.
There is no free-text command dispatcher or PKHeX invocation.

## Append-only correction

Corrections link a new decision to the previous decision. Old revisions, penalties
and sanction ledger entries are immutable. The current decision head controls
prospective applicability; superseded effects remain readable in private history.

The request states the full corrected sanctions, not incremental changes. Reducing
a coin penalty from 50 to 20 credits exactly 30; acquittal credits its remaining 20.
Increasing it debits only the difference while legal. A Store Ban duration correction
keeps the original starting round and changes total duration; it does not restart
the clock. Removing it ends remaining applicability. Removing and later adding a
ban is a new effect and must meet current lifecycle/timing rules.

Points corrections affect the next unclosed capture; old captures are frozen. A
compensatory correction after finish/archive may refund coins and record corrected
notes/verdict/net sanctions. It cannot introduce/increase mechanical effects,
rewrite final standings, Hall, archive checksum/package or frozen snapshots. A
correction at that boundary therefore leaves the captured points projection intact.

## Transaction, security and concurrency

One service-only invoker RPC owns each command. Lock hierarchy: enabled principal
SHARE → receipt advisory → season NO KEY UPDATE → ordered season players UPDATE →
current matchday UPDATE → case → decision/effects/ledger → case revision/event/receipt.
No Python mutex and no automatic retry with a refreshed revision. Matchday close
fingerprints include judicial changes; a changed input produces `STALE_INPUTS`.

Same actor, operation/resource scope, key and canonical body return the original
receipt; a different body conflicts. Decimal spelling and sanction ordering are
normalized before persistence. A replay still requires an enabled principal but
returns the committed receipt before evaluating changed participant/lifecycle state.

Safe reads expose case number, title, public summary, status, explicit verdict,
typed sanction summary and timestamps. Evidence, decision notes, correction reasons,
nominal history actors, receipts and audit event payloads are private. Creator,
accused and admin can read appropriate detail. Private cases and their sanctions
do not enter public projections. Old vote access is not broadened.

Migration 030 revokes browser table and column DML on cases, votes and penalties,
including inherited TRUNCATE, which is not protected by RLS.
All new business/helpers are service-role-only with fixed search paths. New history
tables use RLS. Existing 018 definer views are retained with safe added columns;
the new accumulated-points view is an invoker over existing safe projections.

## Validation and next phase

Shared fixtures run production repositories against independent real PostgreSQL
sessions or real Auth JWT → FastAPI → PostgREST. They cover all requested race
families, timing, full debt, prospective points, correction, privacy and direct-write
denial. Local-only failure triggers compare every public table before/after each
injected boundary. Staging uses unique `phase8k1_validation_<uuid>` fixtures and
scoped cleanup; no failure DDL, reset, bootstrap or historical migration replay.

8L is separate and is not started here. Approved reduced scope: Swiss + Top Cut,
elimination and doubles; practical avoidance of self-pairs/rematches and correct
byes; deterministic standings/Top Cut; real Bo3; corrections before downstream play;
logical cancellation; player/team disqualification; post-League Cups; certified
champion/finalist/Hall and multiple-Cup separation. Use **focused tests covering the
main Swiss, bye, Top Cut, Bo3, correction, cancellation, disqualification and
certification flows, plus a small set of representative end-to-end tournament
simulations**. No exhaustive fuzz/property campaign. Prepare bracket/standings APIs;
visual improvements belong to React/polish. This remains a medium/medium-heavy phase.
