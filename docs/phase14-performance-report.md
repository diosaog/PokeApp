# Phase 14 - performance execution and closure

Closed 2026-10-12. **STATUS: PHASE 14 DONE.**
**PHASE 15 READINESS: READY FOR CUTOVER.** Stop before Phase 15.

## Entry and measured baseline

Phase 14 entry was the verified clean `main`/`origin` checkpoint
`eab706e22bf08004d85b5d9e3253e344659f3c04` (0/0). The initial hosted and local
measurements were retained; no Phase 13, 11 or 12 rerun was needed. The same
five-round authenticated GET method was used before and after the optimization.
The populated local fixture used six synthetic participants, six current Team
Locks and real PostgreSQL 17.11. The hosted owner season was observed read-only
and is sparse.

## Optimization

Inventory previously resolved every rival Team Lock identity with two reads per
rival and also read the season twice. `FrontendReads.inventory` now validates the
season once and asks the repository for all rival public identities in two
bounded reads: observations restricted to the exact trainer/save pairs and six
party slots, then unambiguous entities restricted to the observed IDs. Conflicting
saves, foreign ownership, malformed rows, duplicate slot identities, ambiguous
entities and collection overflow fail closed. Rival parsed saves and private lock
snapshots remain outside the projection.

The transport/call-slope tests prove two identity reads for one or six rivals.
The synthetic endpoint response is byte-for-byte identical before and after. In
local PostgreSQL the inventory median fell from **1.1566 s to 0.8973 s** (22.4%).
The equivalent hosted sparse read moved from **1.8671 s to 1.6028 s**; this is
reported as a same-method observation, not a populated-rival claim.

## Validation and delivery

The final source passed **809 Python tests** once, including the 36 inventory/read
privacy and call-slope tests and 73 related API/read/preview/scouting/general
checks. Python compilation and `git diff --check` passed. Ruff was unavailable in
the environment and was not installed solely for closure. React/browser and
TypeScript/build evidence from the unchanged Phase 13 frontend remains valid;
no web source changed in Phase 14.

Commit `d05e28e01639d146976300dbcd7bb16baa92c9d1` was pushed before deployment.
Only Railway API was deployed: project **PokeApp V2**, service `pokeapp-api`,
production deployment **`9b75a24f-ca5e-474b-9c3c-555625cceb14` SUCCESS**, source
`d05e28e01639d146976300dbcd7bb16baa92c9d1`, image
`sha256:cdc7a9bcc7edd5fc2c5cf9b76fbe86b3be58b204303f5c029bd62a09246e1120`.
Previous compatible deployment `3845ce2d-6488-43ef-893a-1459c2aed0bb` remains
recorded. Cloudflare was not redeployed.

A temporary Railway project was accidentally created when an early command ran
from an unlinked bundle directory; it was stopped and deleted immediately. The
real service was then positively verified and deployed from the committed bundle.
The final Railway project list contains only PokeApp V2.

## Remote preservation and 503 limits

Read-only before/after captures show 34 migration records, 59 scoped tables,
owner-stable business data, security catalogs and all 135 private Shadow rows
unchanged; Shadow remains `reconciled`. Storage bytes and business writes are
zero. Owner Auth/session/refresh activity is separated from stable business
comparison. No Cloudflare or Supabase write was needed.

The retained hosted inventory samples are five 200 responses before and five 200
responses after, with no retry and no 5xx. The historical intermittent READ 503
cause is **UNKNOWN / NOT REPRODUCED**; the deterministic Phase 13 matchday-close
503 remains unrelated and already fixed. No retry, timeout or failure suppression
was added.

## Cleanup and remaining limits

The exact disposable database `pokeapp_v2_validation_phase13_phase14_perf`, local
API and PostgreSQL process were removed/stopped; no local frontend was started.
The populated rival-count result is local evidence only because the hosted owner
season was not mutated. Overview remains the slowest hosted area and is deferred
without speculative broad projection changes. Scouting/preview/Admin remain
measured controls. Full Launcher/save ingestion, cutover and Phase 15 are outside
this package.

The structured evidence is in [phase14-performance-evidence.json](phase14-performance-evidence.json).
Raw measurements remain private under `%TEMP%/phase14-performance-20261011/`.

**STATUS: PHASE 14 DONE. PHASE 15 READINESS: READY FOR CUTOVER. STOP.**
