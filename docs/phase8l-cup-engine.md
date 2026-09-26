# Phase 8L — Cup engine and certification

Approved behavior contract; not a deployment or completion claim. Read the
[MultiIA continuity protocol](AI/PokeApp_Multi_AI_Continuity_Protocol.md).
The [live handoff](work-in-progress/phase8l-live-handoff.md) maintains current
operational state; the [delivery report](phase8l-completion-report.md) retains
dated implementation and validation evidence. The rules below are unchanged by
the 2026-09-26 documentation reconciliation.

The supported contract is a small deterministic Cup backend: Swiss + Top 4,
single elimination, and doubles round robin + Top 2 + final. It improves the
legacy flows without claiming official competitive Pokemon tournament rules.
Bracket/ranking data is ready for React; visual polish remains a later phase.

## Authority and lifecycle

Nine mutations require verified JWT, globally enabled trainer and `is_admin`.
The admin need not participate. Names and client-supplied actor fields confer no
authority. Reads require an enabled JWT; discarded Cups are visible to admins.
There is no generic PATCH, reset, delete, manual champion or standings writer.

Each new Cup belongs to one season. Create/start/play/finalize work in ACTIVE,
FINISHED and ARCHIVED seasons, and reject DRAFT/DISCARDED. Players must already
have a same-season identity and be globally enabled at entry/start. League
retirement/abandonment/disqualification does not erase that identity or reactivate
it. Cup DQ is a separate side status. Existing 028 conservative Cup dependencies
are retained, including its protection of doubles sides with a NULL trainer.

Draft setup can be replaced with Cup CAS. Side order is the explicit seed order;
members within a team are canonicalized by UUID. Starting freezes identities,
safe names, seeds and rules and persists actual pairings. There is no random
reshuffle on replay. Draft DQ keeps the excluded side and its membership history.

`draft -> active -> finished` is explicit. `finished` requires certification;
recording a final score does not certify. Draft/active may become `discarded`
with reason and literal `DISCARD` confirmation. All played history, results,
standings and command revisions remain stored. Certified Cups cannot be discarded.

## API

Mutation base: `/v1/admin/seasons/{season_id}/cups`. Every mutation requires
`Idempotency-Key`; existing Cups additionally require `expected_revision`.

| Method/path | Purpose |
|---|---|
| POST collection | Name, format, ordered sides/members, Swiss round count |
| PUT `/{cup_id}/setup` | Replace unused draft setup |
| POST `/{cup_id}/start` | Revalidate, freeze, persist first round |
| PUT `/{cup_id}/rounds/{number}/results` | Atomic batch of previously unrecorded results |
| POST `/{cup_id}/rounds/{number}/close` | Close complete round, rank, prepare successor |
| POST `/{cup_id}/rounds/{number}/correct` | Reasoned result correction with dependency guard |
| POST `/{cup_id}/participants/{side_id}/disqualify` | Side/team DQ with reason |
| POST `/{cup_id}/discard` | Logical cancellation with reason and confirmation |
| POST `/{cup_id}/finalize` | Revalidate graph and atomically certify/Hall |

GET `/v1/seasons/{season_id}/cups` and `.../{cup_id}` expose typed safe summaries,
members, bracket positions, phases, rounds, result kinds, rankings, Cup revision,
certificate provenance and champion/finalist side IDs. No private history reason,
actor audit, Auth data, arbitrary metadata or Pokemon/save material is returned.
Ambiguous pre-031 Cups stay in their existing projections. The new API does not
promote them to certified state; mutation returns `LEGACY_CUP_UNSUPPORTED`.

## Version 1 rules

Swiss requires at least four entrants at start, at most 64 sides and 1–10 rounds
(default 3). All eligible sides play once per round, with one real NULL bye for an
odd pool. Rank by wins, Buchholz (sum of actual opponents' wins), then frozen seed
and UUID. A bye awards one win, no loss and no synthetic opponent/Buchholz value.
There are no invented Bo3 games in Swiss: its results specify the winner only.

Pair adjacent ranked players while preferring unplayed opponents. A single local
swap removes the common avoidable last-pair rematch. Otherwise accept a rematch
instead of blocking the Cup. Give the bye to the lowest-ranked player among those
with the fewest previous byes. This is deterministic and bounded, not an optimizer.
After the configured Swiss rounds, eligible Top 4 seeds play 1–4 and 2–3, then final.
If DQ leaves two or three eligible qualifiers, preserve four bracket slots with
real byes; no fake entrants. Fewer than two eligible qualifiers cannot produce a
certified champion/finalist: close rejects `INSUFFICIENT_TOP_CUT`; discard remains
available. There are no legacy early 4-win qualification or 3-loss elimination gates.

Elimination uses a standard seed bracket padded to a power of two with NULL slots.
Winners advance in persisted bracket order. Semifinals, elimination rounds and
finals accept only completed Bo3 `2-0`, `2-1`, `1-2`, `0-2`. The winner is derived
from scores. Winner-plus-score requests, ties, partial scores and coercions fail.

Doubles has 2–16 sides, exactly two distinct trainers per side and no trainer in
two sides. Membership has relational same-Cup/same-season FKs, not JSON-only names.
The circle schedule gives every pair one series; an odd-team rest awards no win.
Rank by series wins, game difference, games won, valid two-way head-to-head, then
frozen seed/UUID. Forfeits award a series win without invented game scores. The top
two eligible teams play a Bo3 final. The champion is the side plus both members.

## Corrections and disqualification

Only unrecorded scheduled matches use `results`. Changing a played result requires
`correct` and a reason. A round is the dependency unit: any played later round
blocks correction with `PLAYED_RESULT_DEPENDENCY`. Unplayed successors can be
recreated deterministically; earlier played match IDs remain. Previous values and
prepared successors remain in append-only revision snapshots. Closed corrected
rounds recompute standings and their next round; open rounds still need explicit close.

DQ preserves completed results and member identity. It removes the side from
future Swiss pairing/qualification. Pending matches become scoreless forfeits,
byes or void matches as appropriate; eliminated brackets retain their original
sides and advance remaining winners coherently. In doubles, DQ applies to the
whole team. A recorded final winner cannot be removed by DQ: correct the final
first, while uncertified, or discard. No DQ can rewrite a played downstream match.

## Persistence, transaction and history

Additive `031_cup_engine_certification.sql` adds Cup CAS/rules, typed members and
rounds, numeric scores, standings inputs, append-only `cup_history` and immutable
`cup_certificates`. Migrations 001–030 are unchanged. Legacy rows retain NULL rules
provenance; old `finished`, position or champion names are not certification evidence.

The pure server engine plans from an explicit safe database graph. The service-only
context RPC handles an existing receipt first. The commit RPC rechecks the input
fingerprint and current Cup CAS under locks before applying the server plan. Neither
the HTTP DTO nor browser roles can supply a plan. This follows the established 027
planning/commit boundary. A concurrent change returns `STALE_REVISION` or
`STALE_INPUTS`; production never retries a mutation with refreshed state.

Lock order is enabled admin SHARE, receipt advisory, season NO KEY UPDATE, ordered
season players UPDATE, roster trainers SHARE, Cup, ordered sides/members, rounds/
matches, standings/certificate/Hall, then revision/history/event/receipt. The shared
season/player locks serialize with 026–030 without a Python mutex. Idempotency scopes
actor + season + Cup + operation + key and canonical body/resources. Exact replay
returns the original receipt after authorization, even after later lifecycle changes.

Certification reproduces every generated round using frozen eligibility at draw
time, verifies side/member identity, results, advances, final and standings, then
stores a safe versioned snapshot and SHA256 checksum. SQL verifies final provenance
again under the fingerprint lock. Certificate, FINISHED state, per-Cup Hall,
revision/history, admin event and receipt commit together. The private actor/time
are typed provenance; public content excludes command reasons and audit actors.

The Hall keeps its existing uniqueness for League and unlinked legacy entries;
new Cup entries are unique by Cup ID. Doubles uses a NULL single-trainer champion
and a typed champion side whose two members are frozen. The existing public Hall
projection adds Cup/certificate/side IDs and safe frozen members. Its established
018 security options are preserved. Cup Pokemon team is always `[]`; no live save,
League Team Lock, parser, PKHeX or invented team is consulted.

League final snapshots, rewards, movements, Hall, archive JSON/checksum and its
`cup_hall_status=pending_cup_api` remain unchanged by later Cup operations.

Browser table/column INSERT/UPDATE/DELETE and inherited TRUNCATE are revoked on all
Cup write surfaces, including views. All new RPCs/helpers are fixed-search-path
invoker, service-only. New tables have RLS and no browser grants. Certificates and
certified source rows reject updates, and terminal Cup commands reject correction.

## Validation boundary

Focused unit/API tests and representative complete tournaments replace exhaustive
simulation/fuzz/property campaigns. Shared real-DB fixtures cover the three modes,
bye rotation, Bo3, correction, DQ, cancellation, post-League operation, multiple
Hall entries, direct-write denials and ten race families. Local failure triggers
compare all public rows before/after nine major start/close/DQ/finalization boundaries.
No failure DDL is applied on staging.

`tools.validate_supabase_v2_cup_release` rebuilds migrations/bootstrap twice, compares
schema/grants/ownership exactly, simulates inherited browser ACLs before 031,
checks RLS/catalogs and runs relevant 026–030 regressions once. The staging runner
uses uniquely prefixed fixtures, real JWT/FastAPI/production PostgREST and scoped
cleanup. Delivery evidence and the final small Phase 8 inventory are maintained
in [the completion report](phase8l-completion-report.md).
