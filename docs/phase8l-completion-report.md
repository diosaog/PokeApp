# Phase 8L delivery report — Cup engine / certification (open)

Started: 2026-09-24. Evidence reconciled: 2026-09-26.
Starting HEAD `87a98f5`, branch `main`, origin 0/0 at phase start.
Baseline: 466 unit tests, migrations 001–030, complete-project estimate ~68%.
030 already deployed as `20260924102756` and `20260924103256`; never replayed.

This existing file is the technical implementation/evidence report, retained at
its original path for continuity. Its filename is not a DONE claim. The
[live handoff](work-in-progress/phase8l-live-handoff.md) alone maintains current
operational state, Git changes and the next action. Follow the canonical
[MultiIA protocol](AI/PokeApp_Multi_AI_Continuity_Protocol.md).

## Delivery status

At the 2026-09-26 reconciliation, implementation was published in `d38b871` and
unchanged by subsequent commits through `bc419ba`. Local passing evidence is
recorded below. **Delivery remains IN PROGRESS, not DONE.**

Earlier reports say 031 was not applied to staging. No independent remote query
was performed during the context audit or this documentation reconciliation, so
that assertion remains historical/reported, not a fresh verification of absence.
No code, migration or staging change is part of this documentation task.

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

These are dated local observations, not new executions during the documentation
task and not a current staging certification.

| Check | Evidence inspected on 2026-09-26 | Result / limit |
|---|---|---|
| Unit suite, baseline plus focused engine/API coverage | `%TEMP%/pokeapp-general-review-unit.log`, 2026-09-26; `tools/run_unit_tests.py` | **501 tests, OK**, exit 0 recorded in preceding context review; no skipped tests reported |
| Compile | Preceding context review: `py -m compileall -q app tests tools` | PASS; not rerun for these document edits |
| Local PostgreSQL release | `%TEMP%/phase8l-release.log`, 2026-09-24 | Ends `Cup release RESULT ok; final local gate complete`; historical evidence, not a newly executed gate |
| Migrations 001–031 / bootstrap | Release log and preserved schema dumps | Rebuild and **10,515 normalized lines** of schema/grants/ownership parity recorded; current copies of both dump files have identical SHA256 |
| Inherited browser grants | Release log | Revocation checks PASS locally |
| 026–030 regressions | Release log | Setup 17, matchdays 20, participant status 24, lifecycle 19, trials 8 groups PASS |
| Cup flows and concurrency | Release log | L01–L06 and ten race families PASS in that run |
| Cup rollback | Release log | Nine all-public-state rollback boundaries and fixture cleanup PASS in that run |
| Real staging JWT/API/PostgREST, cleanup and Advisor delta | No 8L completion evidence available | Pending verification/delivery; no deployed public API claim |

Source provenance: implementation commit `d38b871`; inspected repository HEAD
`bc419ba`. Cup implementation/test/validator/migration paths have no intervening
diff between these commits. However, the SQL release log predates that commit and
does not record its source commit or complete working-tree fingerprint. Preserve
its PASS evidence without claiming a freshly reproduced gate against current HEAD.
The next executor must reconcile any relevant source/harness changes before
reusing a result; rerun only checks justified by an evidence gap or change.

The context audit found trailing whitespace in the handoff, so its earlier
`git diff --check` PASS was stale. The document-only reconciliation removes that
defect; its final document checks belong in the live handoff, not in the SQL ledger.

Ten race families: starts; results/results; results/close; closes; correction/close;
correction/finalize; DQ/results; discard/finalize; finalizes; Cup finalize/League
finish plus consistent certificate read. Separate DB sessions/HTTP clients.

Local rollback after initial pairings, standings, successor round, DQ status,
DQ advancement, certificate, Hall, event and receipt compares every public table's
full ordered rows. No failure DDL is sent to staging.

## Staging and independent cleanup

Implementation and 031 are already published; the previous instruction to wait
for their push is obsolete. Use the live handoff's next action, not an unconditional
instruction to apply 031. Before any authorized write, independently confirm the
pinned project and migration history, reconcile the committed source and validation
evidence, and obtain a fresh public/Auth/Storage baseline and Advisor inventory.

If 031 is absent, apply only its committed SQL through an available supported
migration mechanism. If already present, verify the recorded migration/schema and
continue validation without replaying it. Record remote version and validation
status immediately after application, then real API/JWT/PostgREST results,
independent cleanup and Advisor differences. Historical 8K.1 Advisor totals are
24 ERROR / 4 WARN / 5 INFO; they are not a fresh 8L preflight inventory.

No reset/bootstrap, historical migration replay, V1, runtime change or cutover.

## Reproducible checks

Reference commands for a later authorized validation task; this section does not
instruct a documentation-only task to run them. The release reset is local only.
The staging command is allowed only after the staging preflight described above.

```powershell
.venv-api\Scripts\python.exe tools/run_unit_tests.py
py -m compileall -q .
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cup_release --psql <local-psql.exe> --allow-destructive-reset
.venv-api\Scripts\python.exe -m tools.validate_supabase_v2_cups_sql --psql <local-psql.exe>
.venv-api\Scripts\python.exe tools/validate_supabase_v2_cups.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
git diff --check
```

Local evidence is under `%TEMP%/phase8l-{release,cups-dev,unit-final}.log`, the recent
unit log named above, and `%TEMP%/phase8l-{migrations,bootstrap}-schema.sql`.
Only random pg_dump restrict keys are removed when comparing dumps; ownership
and grants remain included. These raw files are machine-local and may be absent
in another checkout. The ledger above preserves their inspected result summary;
it does not manufacture missing commit/run provenance.

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

The 2026-09-26 context/documentation work did not read, modify, stage, rename or
delete the protected `docs/pokeapp-guia-completa-pestanas-y-producto.md`. Its local
untracked state is recorded in the handoff. Migrations 001–030 and Streamlit/V1
were unchanged by 8L implementation. Global progress is maintained in the
[project checkpoint](project-checkpoint.md), with no increment credited by this
documentation task. Any increment after 8L closes requires actual delivery evidence.
