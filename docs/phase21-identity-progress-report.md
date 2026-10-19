# Phase 21 - Trusted Gen6/7 identity and native progression

**Status at source closure: SAFE IMPLEMENTATION READY / REWARDS GATED.**

Phase 21 adds conservative, season-scoped trusted identity evidence for Generation 6/7 saves and additive native progression evidence for X/Y, Omega Ruby/Alpha Sapphire, Sun/Moon and Ultra Sun/Ultra Moon. Existing Generation 3-5 reader and receipt semantics remain compatible. No physical save bytes are written and no owner competitive data is changed.

## Identity and progression

Identity schema 2 is only accepted for the native Gen6/7 path. Trainer scope, immutable candidate evidence, PID/encryption-context collisions, eggs, trade or incomplete origin facts, ambiguous clones and unsafe reappearances fail closed as `UNKNOWN`/ambiguous. Identity IDs are deterministic and scoped to the save, trainer and season; later visible edits do not rewrite immutable evidence.

Native progression is structured and game-specific. Gen6 exposes Kalos badges plus independent League/Hall-of-Fame/champion facts. Gen7 exposes island challenge progress and independent champion facts; it does not fabricate gym badges. Native facts are read-only observations and do not prove legitimate gameplay, a unique physical Pokémon, or a complete battle-entry transition.

## Rewards and history

Gen6/7 progression rewards remain blocked (`pending_validation` or `pending_policy`) until approved transition evidence and policy exist. No backfill or speculative award was performed. Existing Gen3-5 rewards are unchanged. Frozen history, Team Locks, owner seasons, economy and save data are preserved.

## API, SQL and web

Migrations `048_trusted_gen67_identity.sql` and `049_native_progress_read.sql` are additive and locally validated. The service-only native projection uses a strict allowlist, fixed search paths and fail-closed shape/game checks. The public progress read presents badge/island/champion facts without private identity data; React does not rank, authorize or award.

## Validation

- Full Python: **916 PASS**.
- Focused Phase 21 identity: **16 PASS**; progress/API: **30 PASS**.
- Compatibility suites: 13 + 9 + 5 + 8 + 3 + 11 PASS.
- Schema/contract: **15 PASS**.
- Native synthetic checks: **360 assertions PASS** and PostgreSQL native gate PASS.
- Legacy identity SQL/security gate: **19 PASS**.
- Fresh migration/bootstrap builds: **54 public / 15 private tables**, identical.
- React progress: **7 PASS**; affected browser: **2 PASS**.
- Vite build, formatting and targeted Ruff syntax gates PASS.
- Disposable PostgreSQL databases were dropped and the local cluster stopped.

Evidence for native fixtures is retained privately under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase21/20261018`; public JSON fixtures contain only sanitized metadata and hashes. They do not replace authentic proof of every legitimate gameplay transition.

## Delivery boundary

At this source checkpoint, production remains at migration 047 and the pre-Phase-21 application deployments. Remote migration, deployment and positive owner-season mutation must occur only after this committed source is pushed and a fresh preservation baseline is captured. No PIN or owner mutation is required for read-only verification.

Phase 22 is not started. The next controlled step is fresh remote baseline, apply 048/049 once, deploy the compatible API and web, run read-only smoke, and record whether the safe projection is deployed. Rewards remain gated.
