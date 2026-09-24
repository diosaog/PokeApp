# Phase 8K.1 completion report — Trials / sanctions

Date: 2026-09-24. Starting HEAD `da81763`, branch `main`, origin 0/0.
Starting baseline: 431 unit tests, migrations 001–029; staging 029
`20260923232516`; estimated complete-project progress ~66%.

## Delivery status

Implementation and local validation **PASS**. **Not yet DONE.** Real staging,
independent cleanup, final Advisor delta and delivery commits remain required.

Authoritative product contract: [Trials / sanctions](phase8k1-trials-sanctions.md).
Discord is the external decision venue. PokeApp manually records the explicit
agreed verdict and applies consequences; there is no Discord integration or voting
engine. Any eligible enabled season participant may record/correct, without admin,
creator or accused authority requirements. Creator-only proposal edit/cancel.

## Implementation

Seven self-service FastAPI routes with strict typed DTOs, verified JWT, stable
errors and response whitelists. One service-only mutation RPC; case revision CAS,
canonical-body idempotency and transactional stable numbering. Typed immediate
Store Ban, integer ledger debt, exact decimal prospective cumulative points and
text-only release/warning notes. Additive 030; migrations 001–029 unchanged.

Decisions, effects and coin facts are append-only. Correction links the prior
decision, credits/debits exact differences and replaces prospective applicability.
Compensatory correction is allowed after finish/archive without modifying frozen
snapshots, rewards, movements, Hall or archive packages. Browser table and column
judicial writes are revoked. Ambiguous imports stay unclassified; the isolated
legacy mapper now understands explicit `no_culpable` without inventing verdicts.

## Validation ledger

- Unit suite: **466 PASS** (431 baseline + 35 focused API/adapter/import tests).
- `py -m compileall -q .`: PASS.
- Focused/integrated PostgreSQL: seven business/security groups plus cleanup and
  16 exact full-public-state rollback boundaries PASS, including replay, ambiguous
  legacy privacy, config-boundary protection and immutable history/ledger.
- Full migration/regression gate through 030: PASS, including 020/021/022 and
  026/027/028/029, historical identity/redemption and direct RLS/auth checks.
- Bootstrap reset/rebuild twice and schema/RLS assertions: PASS.
- Final migrations 001–030 rebuild twice: PASS. Exact schema/grants/ownership
  parity: **9,690 identical lines**, compared after rebuilding the final SQL.
- Catalog audit: zero browser table/column judicial writes; zero unsafe/new
  non-service RPC execution grants; both new tables have RLS.
- Real V2 JWT/API/PostgREST: pending implementation commit/push.

Concurrency covers concurrent numbering/create replay; proposal vs resolve; resolve
vs cancel; distinct/same-key resolves; correction vs correction/purchase; coin
sanctions vs normal/promo purchase; Store Ban vs purchase; points vs close; resolve
vs open/status/finish; post-finish/archive correction; independent trials against
one accused. Each uses separate DB sessions/HTTP clients. No production mutation
retry. A close losing its fingerprint check returns `STALE_INPUTS`.

Rollback injection is local only after counter/case/history writes; all five effect
types (first through last); ledger; case revision; event; receipt; correction and
compensation ledger. Each compares all public table rows before/after, including
fixture-unrelated tables. Staging receives no failure DDL.

## Staging preflight

Pinned project verified: `https://uwleqeuzsveqlugugzba.supabase.co`.
Latest migration verified 029=`20260923232516`. Only committed 030 may be applied;
no reset/bootstrap, historical replay, V1 or cutover.

Fresh pre-migration baseline covers all 40 public tables, four Auth tables and two
Storage metadata tables using row counts and ordered full-row content hashes.
Nonempty: `app_settings=2`, `shop_items=62`, `trainers=10`, `storage.buckets=1`,
`storage.objects=3`. All remaining tables empty, including Auth users, identities,
sessions and refresh tokens. Baseline existing object metadata inspected.

Security Advisor before: **24 ERROR / 4 WARN / 4 INFO**. The 24 ERROR findings are
the existing 018 `security_definer_view` objects. WARN: `set_updated_at` mutable
search path and authenticated execution of `current_trainer_id`,
`current_user_owns_trainer`, `is_current_user_admin`. INFO: RLS without policies on
`admin_operation_receipts`, `matchday_snapshot_revisions`, `robbery_cycles`,
`season_admin_state`. New errors/warnings must be zero. Unrelated 018 findings are
outside scope; see [Advisor reference](https://supabase.com/docs/guides/database/database-linter).
Object/finding/severity evidence: [Advisor inventory](phase8k1-security-advisor.json).

## Scope and next step

Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` has not been read,
modified, staged, renamed or deleted during 8K.1. It remains untracked.

No Cup implementation, React, Companion, PKHeX, save writes, Discord integration,
Streamlit runtime change, Hall/archive rewrite, D8 or broad refactor.

Progress remains ~66% until all gates close; expected completed estimate ~68%.
Next is **8L Cup engine / Swiss / certification / Hall**, not started automatically.
Its reduced scope and focused-test requirement are recorded in the contract;
exhaustive simulation/fuzz/property testing is explicitly superseded. Visual
improvements are deferred to React/polish.
