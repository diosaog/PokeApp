# Phase 10.5E - Observed progress and initial A/B

Observation: 2026-10-01 Europe/Madrid. **Local gates PASS; public delivery pending.**
Entry `8e3d598205613d950e3c4851bd07fb0ffe15ba53`, main/origin 0/0, tracked clean.
[Contract](phase10-5-functional-alignment.md),
[operational record](work-in-progress/phase10-5-live-handoff.md),
[local evidence](phase10-5e-validation-evidence.json).

## Delivered behavior and boundaries

Normal progress comes only from reliable save/parser observations. There is no
participant or administrator medal attestation command. Missing/unsupported
evidence remains unknown; explicitly observed zero stays zero. React displays
"Progreso no observado / pendiente de sincronizar save".

The neutral optional `ObservedSave.progress` contract records versioned regional
badge flags. Reader `pokeapp-reader/2;pkhex/24.11.11` reads Gen 3/4/5 supported game
families, including separate Johto/Kanto flags in HGSS. First-leg readiness requires
the first two primary-region flags, not any two medals or a secondary-region total.
The existing parser-version fingerprint causes one reparse of unchanged bytes.
Old payloads remain readable with unknown progress. No dependency upgrade, cloud
ingestion, save write or distributed Launcher was built.

`progress_evidence()` defines the future trusted ingestion envelope under
`parsed_saves.payload.observed_progress`; the existing normalized parsed schema
remains 1. Source hash, reader version, same owner/season selected save, parsed
record and reconciled identity revision bind evidence. The envelope alone is not
an authentication mechanism. Only the existing service boundary may persist it;
there is no browser upload/promotion path. Without that future ingestion, ordinary
new public seasons correctly remain pending observation.

Only newly created seasons use `observed_deaths_v1`. Their first gameplay leg can
start with roster/configuration before divisions exist. All required participants
must reach Medal 2 and have complete authoritative death evidence before the split.
Configured `division_sizes.A/B` determines capacity. Fewer adjusted deaths ranks
better: Box 8 observations + max(applied revivals, used revive purchases) + twice
wipe revivals, matching 030/D. Unknown Box 8 is not zero, independently of badges.
Wins, point sanctions, names, UUIDs and transport order do not decide the split.

Only a tied block crossing the A/B cut requires external administrative resolution:
the full boundary-group order and reason, bound to the exact sporting fingerprint
and revisions. Neutral ties within a division need no decision. Existing setup
authority confirms the computed split; it cannot manually edit unambiguous places.
The transaction creates initial divisions/memberships, J1 and its matches, a private
immutable snapshot, current pointer, event and receipt. It gives no daily rewards,
movements or gifts. Snapshot inputs preserve rule, exact canonical badge evidence,
source hashes, deaths, capacities and the external decision. Later save changes do
not rewrite it. No new correction/reassignment authority is invented.

## API, React and integration

Enabled-JWT `GET /v1/seasons/{id}/initial-assignment` exposes a bounded whitelisted
review. Admin `POST /v1/admin/seasons/{id}/initial-assignment/finalize` uses strict
DTOs, CAS, stable idempotency and database fingerprint checking; replay precedes
replanning. SQL independently verifies the proposed allocation and boundary order.
All new/renamed helpers are fixed-search-path invokers and service-only. The new
snapshot table has RLS, no browser privileges, and no service UPDATE/TRUNCATE.

React adds one aggregate readiness read, suggested divisions/deaths, explicit
boundary ties, empty decision choices and required reason. A stale review resets
the form; unknown-outcome retries retain the same body/key. No polling or N+1 API
loop. Modern setup hides the old manual initial-division flow. Legacy setup stays
available only for pre-E seasons. Trainers reads use observed nullable progress for
modern seasons, without exposing private provenance. Existing overview latency is
not claimed fixed. [Synthetic mobile review](evidence/phase10-5/initial-boundary-mobile.png).

C participant result authority remains unchanged. Modern J1 checks current observed
cap before sporting progression, and refuses close if authoritative deaths have
become unknown. This last guard was found by independent review and tested with an
incomplete Box 8 after initial assignment. Restoring evidence permits real D close;
the initial snapshot stays unchanged and daily ranking retains its D rule. Team
Lock remains informational. Existing seasons, snapshots, Hall and archive are not
reinterpreted. F championship rules are documented only; F and Phase 11 have not
started.

## Local validation

| Gate | Result |
|---|---|
| Full Python | 663 PASS, direct exit 0; 623 baseline + 7 parser + 33 E domain/API/adapter tests |
| Parser | 54 .NET assertions; six binary/Launcher integration groups; 32 inherited and seven new focused Python PASS |
| React | 11 component/transport PASS; 24 complete Edge PASS; four focused E flows PASS after presentation follow-up |
| E PostgreSQL | Eight groups; twelve all-public rollback boundaries; exact 47-table cleanup PASS |
| Existing SQL | 026 setup, 027 matchdays, 028 participants, 029 lifecycle, 030 trials and B/C/D regressions PASS, direct parent exit 0 |
| Fresh migrations and independent bootstrap | Each built twice; schema/RLS/catalog PASS; 11,462 identical normalized schema/grant/owner lines |
| Static/build | TypeScript/Vite and Workers dry run, compile, formatting/diff PASS; zero new Ruff findings |

Separate sessions cover same-key replay, competing decisions, progress/selected
save/death mutations racing finalization, and participant results racing an
unknown-outcome initial replay. Exact rollback covers both divisions/memberships,
J1, each division's matches, snapshot, pointer, revision, event and receipt. New
snapshot state and unrelated public rows are included in every comparison.

Existing local competition fixtures explicitly use the retained pre-E creator so
they still test their historical contract; E fixtures use the current creator and
prove the modern manual bypass is denied. This is limited to loopback validation,
not a public compatibility switch. The config-reference assertion now includes the
initial snapshot FK. The local destructive reset also removes both old purchase
wrapper layers: repeated rebuilds otherwise retained a comment absent from a fresh
database. No historical migration was changed and no reset is sent remotely.

Retained failed attempts include stale bootstrap expectations during SQL edits,
the new config FK expectation, ambiguous SQL variable naming, one fixture using
the pre-open revision, and the reset comment-parity mismatch. All were fixed and
rerun. A broad Ruff run found 86 inherited issues; comparison to entry proves 86
unchanged, zero new findings. No broad formatting cleanup was made. Only random
pg_dump restrict keys are removed in schema comparisons, not comments or grants.

Raw evidence is under `%TEMP%/phase10-5e-*`, including `python-release.log`,
`sql-release.log`, `regressions.log`, `rebuild-release.log`, parser results, browser
and build logs. Durable evidence retains summaries, commands and source hashes.

## Public delivery and publication

Pending: commit/push, fresh pinned preflight, additive 036 once, existing Railway
and Cloudflare deployment, safe public authenticated/browser reads and independent
full-state/Advisor verification. No positive sporting mutation is permitted against
owner manual data. Existing Anto identity, PIN/admin and seasons must remain intact.
No remote E mutation or deployment is claimed by this local report.

Migrations 001-035 remain unchanged. The protected guide is unread/untouched and
excluded from Git. E remains in progress until public gates and documentation
closure pass. Whole-project estimate remains approximately 80%; stop after E.
