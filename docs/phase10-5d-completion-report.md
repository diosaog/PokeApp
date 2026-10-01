# Phase 10.5D ? Daily sporting ranking and unresolved ties

Delivery date: 2026-10-01 Europe/Madrid. **DONE: local gates, public delivery/auth reads, independent cleanup/security and publication.**
Entry `92d9e5548fe028cda78a95ab41375e0dcea28184`, main/origin 0/0 and no tracked
changes. Implementation `2c8ad428163ee21d8954b5fc70139805f1b87704` was committed and
pushed before remote application/deployment. [Contract](phase10-5-functional-alignment.md),
[operational record](work-in-progress/phase10-5-live-handoff.md),
[local evidence](phase10-5d-validation-evidence.json).

## Sporting behavior and downstream consequences

Every modern daily group uses wins descending then fewer authoritative integer
adjusted competitive deaths. No H2H, name, slug, UUID or insertion order resolves
sporting equality. Immutable domain groups expose an explicitly named transport
order; `unique_order()` refuses a residual tie. The consequence planner checks
position points, position coins, unique Top 3 places, A/B movement boundaries and
the last-B theft reward before any allocation consumer runs. Future consequences
requiring uniqueness must join this check before consuming an order.

A neutral tied block shares global/division sporting positions. Internal allocation
slots prove completeness only; the public DTO does not expose them. A consequential
tie rejects close/correction with 409 and a bounded, whitelisted review. The admin
records an external full-group order and reason, bound to the exact sporting inputs.
Changed results, adjusted deaths, configuration or revision require a fresh review.
The decision cannot override a neutral block or affect players outside its group.

Adjusted deaths reuse 030: Box 8 observations + max(applied revivals, used revive
purchases) + twice wipe revivals. B's visible Box 8 count remains a separate field.
Points sanctions retain exact decimal text and do not become another daily tie-break.
Existing Team Lock, identity and participant membership guards remain authoritative.

The existing service-only close RPC still locks and compares its database fingerprint
before atomically recording snapshot/history, rewards, movements, gift, event and
receipt. External decision reason/order and rule are frozen in snapshot inputs,
with the existing actor/time/revision. These are official historical records, not
private notes. API projection strips internal allocation and decision details.

## History, API and React

No old snapshot is rewritten. Controlled corrections retain the recorded rule:
`wins_adjusted_deaths_v1` for D snapshots and `legacy_pre_10_5d` for older snapshots.
Changed live external facts still close the correction window. Original V1 ranking
was isolated without behavior changes; its function AST equals the original.

Existing admin close/correct routes accept optional strict `tie_resolution`.
Absent/default null is omitted from canonical request bodies so pre-D receipts
remain replayable, while ordinary explicit null winners remain intact. Malformed
trusted reviews return sanitized 503; no unknown code or arbitrary metadata leaks.
Group transport order is canonical, but the human-selected member order is retained.

React shows shared positions as an explicit tie range. Close/correct exception forms
start with empty choices, require a reason, reset on stale inputs and preserve exact
body/key on unknown-outcome retry. Relevant 409 responses are never auto-retried.
No broad redesign, new network query loop or automatic tournament decision was added.
Desktop/mobile form and existing daily views were inspected/tested.
[Synthetic mobile decision form](evidence/phase10-5/daily-tie-review-mobile.png).

## SQL and local evidence

Additive 035 wraps existing context/commit helpers to retain rule and audit provenance.
Lifecycle completeness uses internal allocation slots only for explicitly modern
snapshots; archived sporting positions remain shared. Six new/replaced helper
functions are invoker, fixed search path and service-only. No table, RLS policy or
browser privilege added. Migrations 001?034 are unchanged.

| Gate | Result |
|---|---|
| Full Python, direct subprocess exit 0 | 623 PASS (578 inherited + 45 focused) |
| New sporting tests / new API-projection tests | 25 / 20 PASS |
| React transport/component | 11 PASS |
| Full Edge suite, direct subprocess exit 0 | 20 PASS, including three new D flows |
| D real PostgreSQL | Seven groups, four all-public rollback boundaries PASS |
| Existing SQL regressions | Matchdays 20, participants 24, lifecycle 19, trials 8, C results 6, B GENERAL PASS |
| 001?035 and independent bootstrap builds | Schema/RLS/catalog PASS; 10,834 identical normalized schema/grant/owner lines |
| TypeScript/Vite, Workers dry run, Ruff, compile, formatting/diff | PASS |

D and C runners each prove exact before/after content equality of all 46 public
tables; a final independent scan finds zero fixture prefixes. A comparison of data
between the two independently built databases is inapplicable: schema/RLS fixtures
have independently generated UUIDs/timestamps. No cross-database content equality is
claimed. Only random pg_dump restrict keys are removed for schema parity.

Concurrency includes same-key and competing external decisions, results versus
close, corrections, purchases, status and judicial changes. D checks stale human
review before writes, neutral final close/finish/archive, explicit gift/movement,
correction replay and real old-shaped snapshots. Four injected failures after
snapshot history, ledger, event and receipt restore every public row. No failure DDL
is sent to staging. All local processes finished and PG stopped cleanly.

Retained failed attempts: obsolete old-rule expectations, incorrect shared-label
expectation, initial build missing API URL, and a legacy fixture attempting correction
after changing live statistics. Each was fixed in the harness without weakening a
product guard. PowerShell also labels psql NOTICE/native stderr as shell failure;
regression logs finish all assertions, but their child exit was not separately
retained. Final Python/browser child exit codes are independently recorded as zero.

## Public delivery and owner safety

Pinned Supabase V2 `uwleqeuzsveqlugugzba`; migration **035=`20261001111600`**, applied
exactly once from committed SQL with the [supported migration API](https://supabase.com/docs/reference/api/v1-apply-a-migration).
All previous 26 history rows unchanged; 27 total. **Do not reapply 031?035.**
Fresh pinned project/history, 52-table full/scoped baseline, Advisor and immediate
state checks preceded that single write. Six helper catalog checks PASS; no fixture,
bootstrap/reset, table-data/role/Auth setting or Storage-byte mutation was performed.

| Hosting | Verified delivery, source `2c8ad42` |
|---|---|
| Existing Railway API | `32c10fee-a30a-4c1c-8b5b-4bec9951f637`, SUCCESS, one replica, 226-file committed bundle |
| Image | `sha256:7c8a7051a791cfef1a1e598fbbb6a04a5cecc0af0becf5e2a775d49c6b86a9e9` |
| Existing Cloudflare Worker | Version `fc5ae861-dfa9-43bc-87b9-d4871642d682`; deployment `3d92653c-9336-4dad-90eb-0e522482a418`, 100% |

URLs remain https://pokeapp-api-production.up.railway.app and
https://pokeapp-web.pokeapp-v2.workers.dev. Database migration precedes the compatible
backend and frontend; the old planner fails safely while 035 requires audit metadata.
Existing secrets/CORS/one-process configuration were preserved. Served build assets
match the final local hashes; deep SPA, MIME/CSP/nosniff and exact CORS PASS.
Final JS gzip 115.38 kB / CSS 6.36 kB. No new per-participant API reads or general
performance refactor; existing broad admin invalidation/overview latency remain M/14.

Real public run `phase10_5_public_reads_31caaaeee91b4177838879a89a1e06fe`, source
`2c8ad42`, **PASS, exit 0**. Actual PIN/JWT refresh, `/v1/me`, same enabled admin,
GENERAL/overview/participant state, exact amounts and all eight historical/current
participants PASS. New D DTO accepted on a freshly verified absent season (404);
injected plan rejected (422). Anonymous/invalid JWT denials preserved. The browser
uses real Cloudflare ? Railway ? V2 requests: **22 screen/viewport visits PASS**,
admin reads/visibility, logout, no API/page errors, no intercepted API, zero business
writes. The installed Kaspersky origin is separately classified as in Phase 10.

No positive close/correction was attempted on manual owner data. Anto remains trainer
`507d9c56-04d8-4801-a9da-f1e53674efb5`, Auth
`ac98932c-f713-43d1-8b20-600f0be3dadc`, enabled/admin; current temporary PIN remains
usable. Owner season `c6bcac5b-0b89-403f-8242-41ac58286ade` remains active, J2 scheduled.
No duplicate identity or other trainer mutation. Existing temporary onboarding/role
configuration still requires removal/reset/review before final release.

Runner and independent final comparison (11:23:29 UTC) both prove **52/52 table
contents equal**, including every public/manual row and Storage metadata. Only the
explicit owner's Auth activity is excluded; all other Auth rows remain compared.
Independent comparison also matches the pre-migration scoped baseline, preserves
**27/27 migration records**, and verifies the owner mapping/admin again.
Advisor remains **24 ERROR / 5 WARN / 122 INFO**, zero added or removed ERROR/WARN
by finding/object/severity. Existing findings remain inherited, not repaired.
[Public evidence](phase10-5d-public-evidence.json),
[Advisor inventory](phase10-5d-security-advisor.json).

All validation/deployment processes finished; no fixture operation or local PG
server remains. `main` source was pushed before remote delivery. Final documentation
and evidence are published in their own closure commit; obtain its hash from Git.
Only the protected untracked guide is excluded from a clean tracked tree.

## Limits and next step

D concerns daily sporting truth. The final championship still needs the F accumulated
points repair and the owner's final tie decision; D does not declare it fixed.
Initial A/B is E. The wipe counter UI is G. Broader overview latency, current integer
limits in other economy readers, Launcher, migration/cutover and release onboarding
remain their recorded future work. No V1 runtime change or Phase 11 start.

Current owner PIN/admin and manual seasons are preserved. The protected guide is
never read/inspected/hashed/staged or touched. Whole-project estimate remains ~80%;
Phase 10.5 remains in progress. D is complete; stop here. The next package is E, not started.
