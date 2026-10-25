# POKEAPP — Phase 23 shop and item-use circuit

Observed 2026-10-25 Europe/Madrid. **PHASE 23: PARTIAL.** The local
purchase/authorization foundation is complete and un-deployed. Physical save
application remains gated by Phase 22's real-emulator qualification and is not
enabled by this packet.

## Existing behavior retained

The existing shop and purchase RPCs already debit coins atomically at purchase
time, persist a single pending entitlement, enforce price/balance rules and
recover idempotent retries. The existing inventory and internal redemptions are
unchanged. No real account, balance, save, history or competitive state was
used for validation.

## New local authorization boundary

Migration `054_item_use_authorizations.sql` adds a private, service-only
authorization journal for the physical-use effects that already have an
approved redemption contract: `revive` and `steal`. Preparation binds the
purchase, season/trainer, target Pokémon, current parsed save and exact save
hash plus operation/idempotency keys. It validates ownership, identity
revision, target location and current-save pointer without consuming the
purchase.

Completion accepts only an explicit result state. `APPLIED_VERIFIED` requires
the same save hash and current pointer, then invokes the existing redemption
RPC in the same transaction. `FAILED_RECOVERABLE`, `RECOVERY_REQUIRED` and
`BLOCKED_UNCERTAIN` preserve the entitlement. Scope, replay and conflict
checks fail closed; browser roles cannot access the table or RPCs. The API
exposes prepare, Launcher-scoped status listing and scoped completion routes.

No new robbery rules were introduced and the web inventory still uses its
existing redemption flow. Mentas, Cápsula Habilidad and other explicit item
mechanics remain **NOT STARTED** until their game-specific rules and physical
contracts are approved. The Launcher write engine remains capability-gated and
production writes remain disabled; no APPLIED receipt is produced by this
packet.

## Validation

- New API/domain and SQL contract tests: **8 PASS**.
- Migration/bootstrap/schema contract: **15 PASS**; bootstrap regenerated from
  54 migrations.
- Existing RLS validator: **5 PASS**.
- Targeted compile, diff and Ruff checks for the new Python modules: **PASS**.
- Affected purchase/redemption HTTP tests were not rerun because this checkout's
  available Python lacks the `postgrest` package; no product failure was
  observed. No local PostgreSQL executable is available, so real migration,
  transaction, concurrency and RLS execution remains a release gate.

No full historical suite, PostgreSQL cluster, deployment, migration apply,
Launcher packaging, physical save write or owner data mutation was performed.

## Files and next unit

The implementation adds the 054 migration, generated bootstrap entry, domain,
application, repository, FastAPI routes/schemas and focused tests. Existing
dependency wiring registers the repository without enabling a physical writer.

Phase 23 is **DONE LOCAL** for the authorization schema/API foundation and
**PARTIAL** overall. The next exact unit is a disposable PostgreSQL/real
Launcher integration gate: apply 054 locally, prove purchase remains pending
through interruption/restart and is consumed once only after native
`APPLIED_VERIFIED`, then connect the existing capability-gated write engine.
Only after Phase 22's qualified emulator and private-release gates may this be
considered for production deployment. No Phase 24 starts here.
