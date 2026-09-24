# Phase 8K.1 completion report — Trials / sanctions

Date: 2026-09-24. Starting HEAD `da81763`, branch `main`, origin 0/0.
Starting baseline: 431 unit tests, migrations 001–029; staging 029
`20260923232516`; estimated complete-project progress ~66%.

## Delivery status

**DONE: implementation, local gates, real V2 staging, independent cleanup and
security delta PASS.** Implementation and ACL follow-up were committed/pushed
before their respective staging application. This report closes documentation.

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
- Real V2 JWT/API/PostgREST: PASS. FastAPI runs through TestClient with real
  Supabase Auth verification and production PostgREST adapters; no API deployment
  or frontend cutover is claimed.

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

## Staging delivery and cleanup

Pinned project verified: `https://uwleqeuzsveqlugugzba.supabase.co`.
Preflight latest migration verified 029=`20260923232516`. Only SQL from committed
030 was applied, in two recorded steps:

| Version | Name / change |
|---|---|
| `20260924102756` | `030_trials_sanctions_api`: initial schema/functions/grants |
| `20260924103256` | `030_trials_sanctions_acl_completion`: inherited TRUNCATE revoke only |

The final 030 source includes both steps. **Do not replay either deployment or
029.** No new 031 file, reset/bootstrap, V1, historical migration replay or cutover.

Run: `phase8k1_validation_3cd8ac2e16104311b3064c44869c8847`, exit 0.

| Real staging suite | PASS |
|---|---:|
| 030 judicial flows/security plus cleanup | 8 groups |
| 029 lifecycle/archive/Hall | 19 groups |
| 028 participant status | 24 groups |
| 027 competitive matchdays | 20 groups |
| 026 setup/configuration | 17 groups |
| 020/021 current round, Store Ban and purchases | 29 checks |
| 022 promotions | 27 checks |

Fresh pre-migration baseline covers all 40 public tables, four Auth tables and two
Storage metadata tables using row counts and ordered full-row content hashes.
Nonempty: `app_settings=2`, `shop_items=62`, `trainers=10`, `storage.buckets=1`,
`storage.objects=3`. All remaining tables empty, including Auth users, identities,
sessions and refresh tokens. Baseline existing object metadata inspected.

After 030 and before fixtures, the original 46 tables remained content-identical;
the two added public tables were empty. After the runner finished, an independent
MCP SQL comparison found **all 48 tables identical to the fresh fixture baseline**:
42 public tables, Auth users/identities/sessions/refresh_tokens, Storage objects and
buckets. Forty-three tables were empty; the five nonempty seed/Storage tables kept
their original full-content hashes. Zero fixture residue, zero real-data drift.
Auth deletion was also verified separately by the runner. No Storage bytes touched.

Security Advisor before: **24 ERROR / 4 WARN / 4 INFO**. The 24 ERROR findings are
the existing 018 `security_definer_view` objects. WARN: `set_updated_at` mutable
search path and authenticated execution of `current_trainer_id`,
`current_user_owns_trainer`, `is_current_user_admin`. INFO: RLS without policies on
`admin_operation_receipts`, `matchday_snapshot_revisions`, `robbery_cycles`,
`season_admin_state`. New errors/warnings must be zero. Unrelated 018 findings are
outside scope; see [Advisor reference](https://supabase.com/docs/guides/database/database-linter).
Object/finding/severity evidence: [Advisor inventory](phase8k1-security-advisor.json).

Final Advisor: **24 ERROR / 4 WARN / 5 INFO**, no removed findings and **zero new
ERROR/WARN**. Only added finding: `public.trial_case_counters`,
`rls_enabled_no_policy`, INFO (backend-only counter, browser has no access).
The previously documented intermittent Auth leaked-password-protection WARN
appeared during fixtures but was absent from the final response; no Auth setting
was changed or claimed fixed.

Managed-environment ACL finding during staging: `authenticated` inherited TRUNCATE
on `trial_cases`, `trial_votes`, `penalties`, unlike fresh local roles. 030 now
explicitly revokes it as well as INSERT/UPDATE/DELETE. A local regression simulates
the inherited grant and proves the exact migration revoke removes it. The committed
ACL statement is applied as a narrow 030 completion, without replaying the schema
migration or touching historical migrations/data. No TRUNCATE operation is executed.

Independent final catalog audit: `browser_write_grants=0` (table/column writes and
TRUNCATE), `unsafe_functions=0` (service-only invoker helpers/RPCs with fixed search
paths), `rls_tables=2`.

## Commits and reproducible checks

- `9e9ea65`: implementation, tests, 030 and contract; pushed before initial deployment.
- `20f0362`: inherited ACL hardening and local regression; pushed before applying
  the narrow committed 030 revoke.
- Documentation closure: the commit containing this finalized report/checkpoint.
- Migrations 001–029 unchanged. Final tracked tree clean; `main` / `origin/main` 0/0.

```powershell
.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --port 55439 --database pokeapp_v2_validation_phase8k1_release --allow-destructive-reset
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_trials_sql --psql <local-psql.exe> --database pokeapp_v2_validation_phase8k1_final
.venv-api\Scripts\python.exe tools/validate_supabase_v2_trials.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
git diff --check
```

Bootstrap was rebuilt independently with final schema/RLS assertions, and compared
using normalized `pg_dump --schema-only --schema=public` (only random restrict keys
excluded). Local evidence: `%TEMP%/phase8k1-{unit-final,release,acl-sql,acl-rebuild,staging}.log`
and `%TEMP%/phase8k1-{migrations,bootstrap}-schema.sql`. Final local server stopped.

## Scope and next step

Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` has not been read,
modified, staged, renamed or deleted during 8K.1. It remains untracked.

No Cup implementation, React, Companion, PKHeX, save writes, Discord integration,
Streamlit runtime change, Hall/archive rewrite, D8 or broad refactor.

Weighted complete-project progress: **~66% → ~68%** for delivered judicial backend
and integrations, with no credit for the preceding audit alone.
Next is **8L Cup engine / Swiss / certification / Hall**, not started automatically.
Its reduced scope and focused-test requirement are recorded in the contract;
exhaustive simulation/fuzz/property testing is explicitly superseded. Visual
improvements are deferred to React/polish.
