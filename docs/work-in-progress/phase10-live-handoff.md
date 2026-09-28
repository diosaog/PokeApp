# Phase 10 - live handoff

## Public delivery continuation - 2026-09-28

**IN PROGRESS: both public deployments healthy; authenticated fixture validation
continues.** This section supersedes the earlier local-only checkpoint below.
Railway project `PokeApp V2` / service `pokeapp-api`, deployment
`03e8c858-e036-44b9-8b46-ee659db175f1`, source `6d2c66a`, SUCCESS.
API: https://pokeapp-api-production.up.railway.app.
Cloudflare `pokeapp-web`, version `c3ce7902-8c42-4301-b27e-829d7f507e53`:
https://pokeapp-web.pokeapp-v2.workers.dev. Exact CORS allow/reject PASS.
Reuse these resources; [deployment runbook](../../deploy/README.md).

First public validation `phase10_hosted_3e8cf25b3d614a1981849b5165299f7f` ended
FAIL at day close: the synthetic save setup lacked required identity revisions.
Four real PIN/refresh/JWT flows and admin setup/Team Locks had passed.
Runner exited; independent full comparison restored all 52 tables, no migration
change or new Advisor ERROR/WARN. Evidence `%TEMP%/phase10-hosted-run1`.
The fixture now uses the existing identity reconciliation boundary before close.
No product rule or migration change was needed.

**OWNER_TEMP_STAGING_AUTH**: the unique existing enabled trainer Anto
`507d9c56-04d8-4801-a9da-f1e53674efb5` was provisioned through the supported bridge;
Auth `ac98932c-f713-43d1-8b20-600f0be3dadc`. Public login/JWT/me/refresh and real
React login/logout PASS. Other trainers, competition and Storage unchanged.
Keep this owner access usable for manual inspection; it is not a cleanup fixture.
Credential is deliberately absent from Git, logs and evidence.
Release blocker: **TEMP_STAGING_AUTH_MUST_BE_REMOVED_OR_RESET_BEFORE_RELEASE**.
No universal/default production credential or onboarding policy is introduced.
Evidence `%TEMP%/phase10-owner-access`. Subsequent comparisons must retain all
public rows and exclude only this explicit owner's Auth rows/session activity.

Next: execute corrected `tools.validate_phase10_hosted` against the existing
deployment with a fresh baseline and explicit owner Auth exception; inspect its
result/active process before any repeat, then independent cleanup, docs/Git and
Phase 10 DONE decision. Do not start Phase 11.

## Historical local-only checkpoint (superseded above)

2026-09-28. **IN PROGRESS: local delivery validated; public deployment blocked.**
Implementation published on main through `7a827ee`; preceding commits `512d239`
and `c940b33`. The documentation/evidence commit containing this handoff follows
that implementation; obtain the current HEAD and remote divergence from Git.
Only the protected guide is expected untracked. Never read/stage/move/delete it.
Follow [continuity](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[contract](../phase10-react-cloudflare.md), [report](../phase10-completion-report.md),
[evidence](../phase10-validation-evidence.json), [runbook](../../web/README.md)
and [checkpoint](../project-checkpoint.md).

Phase 9 DONE verified: 25 durable source hashes still match, report/evidence tied
to f2158ed, 543 unit / 24 .NET / six integration groups PASS. No repair or redundant
test rerun needed. Closed report/head ee7ff53 contains no implementation drift.
No pending parser/test process found.

Delivered: seven typed JWT-protected reads, explicit CORS and no-store responses;
React auth/navigation, eleven connected screens, modern Cup/doubles Hall,
inventory/redemption, manual Discord verdicts and six admin areas. Critical
commands preserve CAS/idempotency. Exact numeric transport retains decimal
sanctions. Workers assets build, SPA routing and security headers are validated
locally. Legacy Streamlit and ignored Electron remain intact; no cutover.

Verified evidence: 565 Python tests at `c940b33`; 22 focused tests after the final
decimal follow-up at `7a827ee`; 11 React unit/component tests (subjects unchanged
by follow-up); eight browser tests at `7a827ee`, covering eleven screens at four
breakpoints. Build, Workers dry run/local runtime, lint/compile and formatting
PASS. Browser API responses are synthetic intercepted fixtures, not a live JWT/
PostgREST validation. Edge ran in isolated test contexts after the integrated
Browser was unavailable and Chromium download timed out. See report for commands,
provenance, limits and durable captures; do not repeat green gates without reason.

Real pinned V2 read-only preflight: 24 schema selections and typed lists PASS;
zero seasons/Hall entries, ten public trainers. No remote fixture, mutation,
migration or Storage operation. Historical 031=`20260928110301` and
032=`20260928111840`: DO NOT REAPPLY. No 033. No fresh Advisor claim.

Blocker: Wrangler is not authenticated and no intended public FastAPI URL or
Cloudflare account/domain is available. The owner was asked while implementation
continued; no answer is recorded. No public deployment was attempted. `/health`
is liveness only. Current local build targets localhost and deployment guard
correctly refuses to publish it.

Next action: verify current Git/tool/account state, obtain the intended deployment
configuration, configure backend secrets and exact CORS origins, rebuild against
the public HTTPS API, dry-run/deploy and verify real authenticated flows. Follow
the master staging baseline/Advisor/cleanup procedure if remote fixtures are
needed. Do not invent credentials, reuse old fixtures or skip cleanup.

Known limits: tokens/pending intents are in memory; after reload inspect history
before repeating an uncertain operation. Rival targets expose only already-public
Team Locks, not private boxes. Complete read sets cap at 500; unsupported legacy
PC payloads fail explicitly. Final sprites/audio/polish, Launcher distribution,
cloud ingestion and physical save operations remain outside this delivery.
No Phase 10 DONE decision or automatic Phase 11 start.

Session cleanup verified: local Workers was stopped; ports 8787/5173 have no
listeners and no workspace web Node/Workers/browser process remains. Test/build
commands completed. No remote fixtures or incomplete remote operation to clean up.
