# Phase 10.5H — Team Lock warning and Team Preview modes

Closed 2026-10-07. **H DONE / STAGING_DONE_ZERO_RESIDUE.**
[Local evidence](phase10-5h-closure-evidence.json),
[public evidence](phase10-5h-public-evidence.json).

Entry main/origin `9b7a8dce5953c852b104dc086c69ab689705ffe4`, divergence 0/0,
clean tracked tree. G delivery and 30 remote migrations through 038 were freshly
verified. Application source **9ecf83d76bc570e88b494b548a3757f252220692** was
committed and pushed before deployment. Documentation closure is a later commit;
obtain its exact HEAD from Git.

## Implementation and boundaries

Batallas opens Team Preview. Espectador has two distinct independent trainer
selectors and always shows the existing public Team Lock projection, including
self. Batalla has one selector; only the trainer matching the verified JWT gets
the approved private projection. Admin status does not grant rival private access
through this endpoint. Unknown authority parameters are rejected with 422.

The dedicated bounded `GET /v1/read/seasons/{season_id}/team-preview` reads the
season's current competitive Team Locks. It never substitutes a live party, PC,
parser observation or another day's lock. Missing lock is explicit null; malformed
snapshots fail closed. Existing public/private DTO allowlists strip identity,
original-trainer, parser and internal metadata. Public fields are not expanded.

Missing Team Lock produces a prominent warning in preview and beside editable
League results. Recording results remains available under C's existing eligibility
rules. The explicit existing lock confirmation consults the save only after the
owner opens it. Its command, body and backend semantics are unchanged; an explicit
unknown-outcome retry preserves the request and refreshes only the affected reads.
Mode/selector changes isolate cached projections; season changes reset selection.

No migration, database schema, backend mutation, lifecycle, Hall, Cup, championship,
G counter or sporting rule changed. No replacement cutoff or broader scouting
scope is invented. Frozen historical teams are not recalculated.

## Validation

- **FRESH PASS:** 79 focused Python; full workspace **725 Python**, exit 0,
  no failures/errors/skips. This includes 19 pre-existing untracked map tests,
  outside H and unstaged; committed H source accounts for 706 tests.
- **FRESH PASS:** **29 React / 19 Edge**. Affected browser suites cover new modes,
  missing locks, result controls, exact lock retry and existing navigation;
  desktop/mobile screenshots reviewed. Zero failed/skipped/flaky browser tests.
- **FRESH PASS:** compile, targeted Ruff, full web Prettier, TypeScript/production
  build, Worker dry-run, affected hosted-script syntax and diff checks.
- **FRESH PASS:** real PostgreSQL **17.11**, four projection/security/history groups,
  production composition/repository with exact selected columns, existing RLS and
  service-only RPC rights, **49/49 public tables restored exactly**. Server stopped
  after clients finished. Harness corrections are recorded in the local evidence.
- **NOT RERUN:** rebuild/bootstrap/parity and mutation concurrency/rollback matrices,
  because their contracts and source are unchanged. G results remain **HISTORICAL**.
  Dedicated Hall/Cup SQL matrices were not rerun; their unchanged Python and existing
  affected browser behavior are covered by the fresh gates above.

## Delivery and preservation

Railway **7886ed9c-eb63-4f97-8450-f8d129fa18d8 SUCCESS**, 234 committed API inputs,
source above. Backend health and new-route authentication passed before frontend
deployment. Cloudflare **7545db42-055b-44fd-97ef-a069c8e77c4b**, version
**51669d19-b5c6-49c0-b1b0-96a4fcbc01b3**, 100%, same source. Live assets exactly match
the production build; deep SPA, MIME, CSP, nosniff, HTTPS and exact CORS pass.

Narrow real public smoke: **11 API requests**, including expected 401/422 denials;
**six browser states** across desktop/mobile, nine browser API responses, zero
browser errors/interception/business writes. PIN login, self/rival/spectator modes,
absence warnings, no save/overview read, and logout pass. The initial public browser
attempt used an incorrect accessible label for the season selector; the corrected
locator passed without a product change. That failed attempt remains raw evidence.

The owner's current J2 has no own Team Lock. Positive private snapshot and lock
command/retry proof is **LOCAL ONLY**; no owner lock/result was created to prove it
publicly. Full and scoped baselines were captured before/after: **55/55 scoped
tables identical**, stable owner identity/credential hashes identical, **30/30
migration records identical**, no remote fixture or cleanup. Only owner Auth login
and session activity is excluded from scoped equality. Storage metadata is included;
no Storage bytes were touched. Advisor stays **24 ERROR / 5 WARN / 131 INFO**, zero
new or removed ERROR/WARN. The protected guide and unrelated untracked files remain
untouched and unstaged.

## Performance and remaining decisions

Preview replaces the broad overview dependency with one browser request and five
bounded database reads (six for self). There is no per-player HTTP loop or broad
new invalidation. Four hosted samples measured **1.94–3.23 seconds**; these are
staging observations, not a benchmark. Read consolidation/latency remains a
candidate for M/Phase 14. Team Lock replacement cutoff and wider scouting scope
remain owner decisions; neither blocks H.

Antonio can now test:

1. Batallas → Espectador: select any two different trainers without a scheduled match.
2. Batalla: select self and a rival; private details require one's own existing lock.
3. Select a trainer without a lock: see the warning, then continue to editable League results.
4. Repeat on mobile; selectors and warnings should remain readable.

**STOP after H. Next package: I, awaiting the next owner instruction.**
Phase 10.5 IN PROGRESS; **Phase 11 NOT READY / NOT STARTED**.
