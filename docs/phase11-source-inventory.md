# Phase 11 — authoritative source capture and mapping checkpoint

2026-10-09 Europe/Madrid. **Source identity/access verified; migration not done.**
Resume `dc1b1462c53ed77ddc3af9bac0aa0d9b3de74eb5`, main/origin 0/0, clean tracked
tree. [Current operational record](work-in-progress/phase11-live-handoff.md),
[sanitized evidence](phase11-source-evidence.json). The original HTTP 544 source
blocker is resolved. This checkpoint is blocked on destination placement, not on
whether the project is PokeApp.

## Actual source and preservation

The owner confirmed `fdtytpeyfzyssfrsulxd`, `diosaog's Project`, eu-north-1.
Fresh management metadata reports ACTIVE_HEALTHY. The public catalog exactly
matches the seven legacy runtime tables and their expected hosted columns.
Read-only capture at **2026-10-08 23:23:37 UTC / 2026-10-09 01:23:37 Madrid** used
one SQL statement/snapshot for the raw rows, counts and hashes below. Private
raw response bytes preserve numeric representation; mapping reads use exact
decimal decoding. No legacy runtime reader or local SQLite fallback was invoked.

| Source                  |   Rows | Meaning                                                                              |
| ----------------------- | -----: | ------------------------------------------------------------------------------------ |
| `public.settings`       |      9 | League, Swiss Cup, Anto save/snapshot/badges/PIN, trainer flag, Discord hash caches. |
| `public.saves`          |      1 | Save 434 owned by Anto; one matching Storage object.                                 |
| `public.purchases`      |      2 | Pending Revivir Pokemon and Robar Pokemon, 12 each, J1.                              |
| `public.redemptions`    |      0 | No recorded applied inventory effects.                                               |
| `public.pokemon_flags`  |      0 | No persisted per-Pokémon flags.                                                      |
| `public.shop_discounts` |      0 | No promotional rows.                                                                 |
| `public.team_locks`     |      0 | No current/frozen Team Locks to fabricate.                                           |
| `storage.buckets`       |      1 | Existing `saves` bucket.                                                             |
| `storage.objects`       |      1 | Exact save bytes captured privately and hash-verified.                               |
| Four Auth tables        | 0 each | No source Auth identities/sessions to translate.                                     |

The private capture also establishes absence of lifecycle/configuration/archive,
Hall, judicial, completion-reward and wipe-counter settings. This is absence of
recorded evidence, not proof no unrecorded action ever occurred.

All **13/13** source table count/hash records remain identical after discovery
and download. The save has 524,410 bytes and its recorded SHA-256 matches the
download. Read-only parsing leaves those bytes unchanged. Source Advisor baseline:
**5 ERROR / 11 WARN / 19 INFO**. No source grants, policies, schema, metadata,
runtime settings or physical saves were changed.

The initial discovery harness mistakenly accepted only HTTP 200; Supabase returned
HTTP **201 with a valid catalog**. The successful response was retained privately,
decoded and used; subsequent reads accepted successful HTTP statuses. This was a
harness assumption, not an unavailable/corrupt source or a mutation attempt.

## Mapping facts and truthful limits

| Domain                | Observed truth / required mapping                                                                                                                                                                                                                                                                                                                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trainers              | Ten explicit League names: Anto, Victor, Rober, Samu, Daviry; Sergio, Iker, Aaron, Miguel, Barto. Preserve exact A/B order and 5/5 capacities. Existing V2 has ten seeded canonical trainer candidates; preserve current owner Auth/PIN/admin and never overwrite credentials from the legacy PIN setting. No target identity mapping has been committed.                                                                     |
| League                | `tramo=1`, `active=false`, empty matches/results/movements/round snapshots. The Boolean governs matchday editing, not season lifecycle. Do not invent completed days, wins, positions, champion or Hall.                                                                                                                                                                                                                      |
| Lifecycle             | No `season_lifecycle_v1`. Tracked legacy `load_season_lifecycle()` defaults to active, with unknown start time. That is effective runtime behavior, not an explicit stored timestamp/status or independently verified deployed V1 revision.                                                                                                                                                                                   |
| Configuration         | No `season_config_v2`. Tracked runtime fallback defines four rounds, 5/5 capacity, three movements and exact reward tables. Preserve any use as runtime-default provenance; do not invent a historical stored version or effective date. Exact deployed V1 revision still limits that inference.                                                                                                                              |
| Economy               | Anto has eight legacy badges, no League awards or completion claim, no recorded sanctions, two pending purchases costing 12 each. Live `rpc_total_spent(text)` was inspected without executing it: it sums all purchase prices for that user, agreeing with 24. Tracked V1 formula applied to the captured source yields 32 - 24 = **8 coins**. This is derived current economic state, not eight proven dated reward events. |
| Inventory             | Preserve purchase IDs 206/207, pending state, item, actual prices, J1 and source timestamps with their timestamp-type provenance. No redemption, purchased-revive death, robbery or physical save effect can be inferred from a pending purchase.                                                                                                                                                                             |
| Progress              | Source save 434 and current-save pointer agree. The isolated neutral parser reads **W2, eight Unova badges, Champion not defeated**. Filename alone is not game authority. The legacy eight-badge value agrees; it does not prove completion. Other trainers have no save observation and remain UNKNOWN.                                                                                                                     |
| Deaths/revives        | Actual Box 8 has five Pokémon, agreeing with Anto's legacy snapshot. Zero applied purchased revives are recorded; wipe counter is absent (legacy runtime default 0, not evidence about unrecorded physical behavior). Preserve provenance rather than turning other players' missing saves into observed zero deaths.                                                                                                         |
| Team/history          | No Team Lock, official snapshot, archived season or Hall record is present. Preserve absence; do not substitute current party or invent original first-lock/start times.                                                                                                                                                                                                                                                      |
| Trainer flags         | Aaron has a manual robbed flag and its source note/seed identifier. Preserve that fact independently; it is not proof of a modern robbery receipt or physical transfer.                                                                                                                                                                                                                                                       |
| Cup                   | Configured legacy Swiss Cup: eight named participants, round 1 of maximum 7, four explicit pairs, no winners/history/results, explicit zero wins/losses/byes. V2's legacy branch uses `rules_version=NULL`; do not regenerate pairings or certify as modern Cup. League DQ/Cup state remain separate.                                                                                                                         |
| Non-business settings | Discord notification hash caches are operational suppression/cache state, not competitive data or credentials. Exclude from normal domain migration while retaining private source evidence. Never resend notifications during import.                                                                                                                                                                                        |

## Concrete destination conflict

V2 still has the protected manual active season
`c6bcac5b-0b89-403f-8242-41ac58286ade`. Fresh catalog confirms
`uq_seasons_one_active`. `seasons_lifecycle_timestamp_chk` also requires a start
timestamp for an active season. V1 cannot supply a truthful start timestamp and
cannot become a second active public season under the current contract.

`league_state.active=false` cannot be used as permission to import the legacy
season as draft/archived. Nor may the import merge its ten-player roster and
economy into the owner's separate manual season. Normalizing either season to
make the constraint pass would violate preservation.

The concrete proposed resolution is an **isolated relational import destination
for Shadow**, outside the current competitive lifecycle. Its scope is awaiting
owner approval; no schema, operational lifecycle exception or substitute target
has been created. A private raw capture by itself is not the requested completed
domain migration. After placement is approved, start-time UNKNOWN still needs
explicit truthful representation rather than an invented date.

Code references: [legacy lifecycle default](../app/season/archive.py),
[V2 lifecycle timestamp constraint](../supabase/v2/migrations/001_core.sql),
[one-active-season index](../supabase/v2/migrations/008_indexes.sql). Both destination
constraints were independently inspected in the live V2 catalog during this resume.

For economy, a migration-time opening snapshot of 8 with source provenance,
pre-opening inventory costs already included, and a private eight-badge economic
high-water mark is a viable design candidate. It would avoid fabricated historical
award timestamps, a second 24 debit, duplicate badge payouts, and a false completion
claim. It is **not implemented**; ordinary progress settlement must not run during
import. Final mapping depends on the selected destination contract.

## V2 reconciliation, effects and resumption

V2 is ACTIVE_HEALTHY; **33/33** migration records remain identical, latest
041=`20261008204133`; **267/267** catalog objects unchanged. All public/Storage rows
match readiness. **59/59 owner-excluded table hashes** equal verified 10.5 closure.
Full Auth differences are limited to owner activity; stable identity/credentials
remain equal, non-owner Auth rows remain absent. V2 Advisor stays
**24 ERROR / 5 WARN / 143 INFO**, with identical ERROR/WARN findings.

Railway `2d71ec3b-095d-49a7-aa15-31749fe67b52` remains SUCCESS; Cloudflare deployment
`ea9c837d-86f0-4b0a-826d-a4774371b56e`, version
`77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, remains 100%. Both identify
`eb4e402891cbaa02e0999229874ac3003e016ae0`. No deployment was required or performed.

**Remote migration/business writes: zero. New SQL/helpers/journal/batches: none.**
No unknown import outcome exists. Restart/rollback/concurrency/reconciliation
proof for a migration runner is still NOT EXECUTED. No local PostgreSQL runner
or full application test suite was started for this source-capture checkpoint.
Read-only source parsing, metadata/baseline checks and documentation checks are
the new evidence; prior full tests are not relabeled as Phase 11 migration proof.

Private artifacts: `%TEMP%/phase11-resume-20261009/v1/` and `v2/`.
The captured evidence files have a verified private copy/manifest under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261009/` for durable resumption.
Raw rows, PIN and credential-bearing hashes stay private. No protected guide or
unrelated untracked file was accessed. Only documentation is committed; read Git
for the checkpoint commit, distinct from application/deployed source.

Resume with the destination decision, recheck source/destination state, then
implement and locally prove the approved deterministic migration before remote
writes. **PHASE 11 NOT DONE; PHASE 12 NOT READY / NOT STARTED.** No cutover.
