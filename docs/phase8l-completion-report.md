# Phase 8L completion report — Cup engine / certification

Date: 2026-09-24. Starting HEAD `87a98f5`, branch `main`, origin 0/0.
Baseline: 466 unit tests, migrations 001–030, complete-project estimate ~68%.
030 already deployed as `20260924102756` and `20260924103256`; never replayed.

## Delivery status

Implementation complete; final local regression gate running. **Staging has not
been modified. This is not yet a DONE delivery claim.**

Authoritative contract: [Cup engine](phase8l-cup-engine.md). The reduced scope is
Swiss + Top 4, elimination and doubles RR + Top 2/Bo3 final, with focused tests.
No tournament framework, solver, Elo, extensive fuzzing, visual work or Phase 9.

## Implementation

Eleven typed FastAPI routes: nine admin mutations and two safe reads. Verified
enabled JWT/admin authority, Cup CAS, canonical receipts, explicit start/results/
round close/correction/DQ/discard/finalize. Pure deterministic server engine plans
from a database snapshot; one service-only commit RPC rechecks its fingerprint
under compatible season/player locks. No client plan or automatic mutation retry.

031 adds typed side members, rounds, numeric Bo3 scores, ranking inputs, append-only
command history and immutable certification. Singles and doubles champion/finalist
are side identities; both doubles members are retained. The existing Hall supports
multiple Cups per category/season while retaining League/legacy uniqueness. The
public Hall includes Cup/certificate provenance and frozen members. Pokemon team
is empty because no authoritative Cup Pokemon team source exists.

Post-League Cup operation preserves League snapshots, rewards, movements, Hall,
archive JSON/checksum and the frozen pending-Cup marker. Ambiguous imports remain
uncertified. Draft/active cancellation is logical; DQ never changes League status.
Browser table/column DML and inherited TRUNCATE are revoked, including view paths.

## Validation ledger

- Focused pure-engine/API tests and full baseline suite: final count pending.
- Compileall: PASS; final diff check pending documentation closure.
- Migrations 001–031 and bootstrap rebuilt twice: PASS.
- Exact schema/grants/ownership parity: **10,515 identical normalized dump lines**.
- Simulated inherited browser grants before 031: revoked successfully.
- Final relevant 026–030 regression and Cup SQL run: running.
- Nine Cup rollback boundaries: development pass; final release repeat running.
- Real staging JWT/API/PostgREST: pending; no API deployment claimed.

Ten race families: starts; results/results; results/close; closes; correction/close;
correction/finalize; DQ/results; discard/finalize; finalizes; Cup finalize/League
finish plus consistent certificate read. Separate DB sessions/HTTP clients.

Local rollback after initial pairings, standings, successor round, DQ status,
DQ advancement, certificate, Hall, event and receipt compares every public table's
full ordered rows. No failure DDL is sent to staging.

## Staging and independent cleanup

Pending final local gate and pushed implementation. Apply only committed 031 to
the pinned V2 project, with fresh public/Auth/Storage baseline and Advisor inventory.
No reset/bootstrap, historical migration replay, V1, runtime change or cutover.

## Reproducible checks

```powershell
.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cup_release --psql <local-psql.exe> --allow-destructive-reset
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cups_sql --psql <local-psql.exe>
.venv-api\Scripts\python.exe tools/validate_supabase_v2_cups.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
git diff --check
```

Local evidence is under `%TEMP%/phase8l-{release,cups-dev,unit-final}.log` and
`%TEMP%/phase8l-{migrations,bootstrap}-schema.sql`. Only random pg_dump restrict keys
are removed when comparing dumps; ownership and grants remain included.

## Small Phase 8 closure inventory

Scoped inspection of registered routes and approved Phase 8 contracts:

| Domain | Authoritative boundary |
|---|---|
| Auth / identity / Team Lock | PIN bridge + verified JWT; 019 lock; 023 identity contracts |
| Purchases / promotions / redemption | 020–025 eligibility, ledger, effects and robbery |
| League setup / operation / participation | 026–028 admin CAS and frozen-round contracts |
| League finish / archive / Hall | 029 immutable source and historical package |
| Trials / sanctions | 030 recorded Discord verdict, typed effects and compensation |
| Cup / certification / Hall | 031 explicit engine and per-Cup authority; delivery gates above |

No additional critical mutation gap was identified within this approved backend
scope. This is a small closure inventory, not a new broad audit or a claim that the
whole product is deployed. React consumption/polish, deployment/cutover, Companion,
save writes and deferred D8 remain outside this phase. Phase 9 is not started.

Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` has not been read,
modified, staged, renamed or deleted. It remains untracked. Migrations 001–030 and
Streamlit/V1 are unchanged. Weighted project progress remains ~68% until delivery;
the expected increment for fully validated 8L is about two percentage points.
