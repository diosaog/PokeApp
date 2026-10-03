# Phase 10.5E - Observed progress and initial A/B

Observation: 2026-10-03 Europe/Madrid. **E DONE; STAGING_DONE_ZERO_RESIDUE.**
Final implementation `90a31fc3b4220cefbe7c160902158084aea2569e` is pushed and deployed.
This report's documentation closure is a separate commit identifiable in Git.
Entry `8e3d598205613d950e3c4851bd07fb0ffe15ba53`, main/origin 0/0, tracked clean.
Implementation `0215f73457b7c3245b29af41e0200fd590f2db59`; final diagnostic source and
resumed entry `d24b55152d7d8a29c3632a4f4feec710fb331040`. Fresh fetch at resumption:
main/origin 0/0, existing uncommitted E delivery notes in the live handoff preserved.
[Contract](phase10-5-functional-alignment.md),
[operational record](work-in-progress/phase10-5-live-handoff.md),
[historical local evidence](phase10-5e-validation-evidence.json),
[public evidence, including preserved earlier runs](phase10-5e-public-evidence.json),
[final closure evidence](phase10-5e-closure-evidence.json).

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

## Historical implementation validation - 2026-10-01, source 0215f73

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

## Fresh final-source closure - 2026-10-02, source d24b551

These are new runs on the final published application source, not the historical
counts above. This continuation has required no application-code change.

| Gate | Fresh result |
|---|---|
| Full Python | **664 PASS, 0 FAIL, 0 SKIP**, exit 0; includes diagnostic sanitization test |
| React | **11 PASS**, exit 0 |
| Complete Edge regression | **24 PASS**, exit 0, existing flows plus E; synthetic API, responsive coverage |
| Real parser/Launcher | **54 .NET assertions / six binary integration groups PASS**, exit 0; parser Python cases also in full suite |
| E PostgreSQL | **Eight groups / twelve exact rollback boundaries / 47-table cleanup PASS**, exit 0 |
| Inherited PostgreSQL | **026-030/B/C/D PASS**, parent exit 0; final logs and 47-table cleanup independently recovered and verified on 2026-10-03 |
| Independent migrations and bootstrap | Four builds in two fresh disposable databases, schema/RLS/catalog PASS; **11,462 identical normalized lines** |
| Build/static | Compile, TypeScript/Vite, Prettier, Workers dry run and diff check PASS; generated bootstrap unchanged |
| Ruff comparison | app/tools/tests: **1,010 inherited findings, zero new** versus 8e3d598; broader scope than the historical 86-finding subset |
| SQL immutability | 001-035 unchanged by E; all 001-036 unchanged since 0215f73; no new migration |

The first resumed PostgreSQL start omitted the port and listened on 5432. The
validator on 55439 could not connect and made no database changes. The owned
disposable server was stopped and restarted explicitly on loopback 55439; the
complete rebuild then passed. No product constraint or assertion was weakened.
Raw evidence: `%TEMP%/phase10-5e-resume-20261002`,
`phase10-5e-resume-rebuild-evidence.json` and `phase10-5e-resume-rebuild-second.log`.

## Public delivery, owner safety and security - 2026-10-02 checkpoint

Published source `0215f73` preceded migration **036=`20261001165951`** and the
original E deployments. That application preserved all 52 pre-existing tables;
the new private initial-snapshot table was empty. Fresh inspection now verifies
**28 migration records unchanged since that deployment**. **Do not reapply 031-036.**

The interrupted diagnostic deployment had actually completed before this session:
Railway **1ef649e7-1489-4f97-a4fa-ef08839f5021**, SUCCESS, source `d24b551`, image
`sha256:544a744caa62cf8b2101de5678d6e2e7f93e835b7680d50a2fa05ac7282f32cc`.
All **229 committed bundle files** match Git and the retained upload bundle.
One replica and existing service settings are preserved. Cloudflare retains the
compatible E source `0215f73`, version **0224318e-38d6-4178-ae3a-646384328eb8**,
deployment **3d829325-66fc-4da4-88f4-b7bd4967f8d7**, 100%.
No new migration or deployment was needed in this continuation.

Existing URLs: https://pokeapp-api-production.up.railway.app and
https://pokeapp-web.pokeapp-v2.workers.dev. Served JS/CSS match the fresh final build;
deep SPA, MIME, CSP, nosniff and allowed/rejected CORS PASS. Backend diagnostic
changes have not altered the frontend source or its compatible contract.

Public run **phase10_5_public_reads_11efa6eac0154745badf74fb3ee02abf**, exit 0,
**PASS**: existing owner PIN login/JWT refresh, identity/admin, 21 API requests with
expected successes/denials, real GENERAL/overview and typed E legacy review.
Valid-shaped mutations against freshly verified absent resources prove deployed
RPC paths without changing owner results. Injected progress/actor/plan fields are
rejected. **22 real browser visits**, eleven screens at 1440 and 390, admin reads
and logout; no interception, business write, page/API error or unexpected app
origin. Installed Kaspersky injection remains separately identified.
Inspected [GENERAL desktop](evidence/phase10-5/e-public-general-desktop.png) and
[current day mobile](evidence/phase10-5/e-public-current-day-mobile.png).

Runner and independent final comparison at **2026-10-02 00:34:24 Europe/Madrid**:
**53/53 complete scoped table contents identical**, all **28 migration records
unchanged**, same owner mapping/enabled/admin, zero fixture-prefix residue. The
existing owner's rows in the four compared Auth tables are excluded from equality;
identity/PIN continuity is verified by real login and mapping/admin by a separate
query. Every public/manual row and Storage metadata row is included. No Storage
bytes were read or written.
Twenty helper privilege/fixed-search-path/invoker checks and the private snapshot
table/column ACL checks PASS. Advisor **24 ERROR / 5 WARN / 125 INFO**, no added or
removed ERROR/WARN by finding/object identity. Existing findings remain recorded
in the [Advisor inventory](phase10-5e-security-advisor.json); no global-clean claim.

The first historical public browser run failed with four 503 reads; a subsequent
historical concurrent run failed six of twelve. These failures remain evidence.
The fresh public run passed separately. The two concurrent batches returned **24/24
HTTP 200** reads without 503; diagnostic failure logs are empty in the inspected
deployment log sample. **Historical cause UNKNOWN; incident not reproduced in this
window.** No transport fix was made, and passing runs do not establish that logging
fixed the cause or guarantee permanent absence of intermittent failures.

## Final closure and response-recovery fix - 2026-10-03

Entry `d24b55152d7d8a29c3632a4f4feec710fb331040`, fresh fetch main/origin 0/0.
Pre-existing local E report/handoff/evidence changes were preserved. The supposedly
running SQL regressions had finished with exit 0: all eight inherited families,
E's eight groups/twelve rollback boundaries and exact 47-table cleanup are verified.
Four retained normalized schema dumps match their original hashes and contain
11,462 identical lines. SQL, parser, domain and frontend inputs remain unchanged;
their 2026-10-02 gates are retained evidence, not represented as new runs today.
`pg_ctl status` now confirms the disposable server is stopped. Its historical
shutdown mechanism is UNKNOWN; no claim of a verified graceful shutdown is made.

Fresh public reads reproduced **3/12 HTTP 503** at 11:06 UTC. Deployed sanitized
logs identify three simultaneous **ReadError** failures in the upstream read
transport. The prior clean window did not prove resolution. HTTPX classifies this
as failure receiving network data; its built-in connection retry does not cover
read errors ([exceptions](https://www.python-httpx.org/exceptions/),
[transport retry scope](https://www.python-httpx.org/advanced/transports/)).
The underlying network trigger remains UNKNOWN; no HTTP/2 root-cause claim is made.

Follow-up **90a31fc** adds one retry only for that error in the dedicated frontend
SELECT/read-only-RPC repository. It preserves query scope/body and lets a second
failure return the existing sanitized 503. HTTP denials, other status errors,
malformed data and other transport errors are not retried. Mutation repositories
and unknown-outcome command behavior are unchanged. No dependency, schema or UI
change was needed. Six real-PostgREST/MockTransport tests prove recovery, identical
scope, bounded persistent failure, non-retryable errors, concurrent independent
budgets and no automatic initial-finalization retry. Full Python **670 PASS,
0 failures/0 skips**, compile and touched-file Ruff/format/diff PASS.

Source was committed/pushed before deployment. Existing Railway deployment
**6aa70f72-f0cb-41a1-86d6-7b4227803392** is SUCCESS, source `90a31fc`, image
`sha256:f7a8efe77db345305ddda1c6cd398f06cd58d48779edade104b750d05404ee7d`.
The committed-only bundle contains 229 files; the service manifest, single replica,
healthcheck, origins and secrets were not changed. Cloudflare retains the compatible
`0215f73` version/deployment above; live assets and security headers match. No new
migration or frontend deployment; **036 remains applied once as 20261001165951**.

Final public run **phase10_5_public_reads_d5d933292db242288543d89f52fb847a**, exit 0:
**21 API checks, 22 real browser visits PASS**, no interception or business write.
Two post-deploy concurrent batches returned **24/24 HTTP 200**. The inspected new
deployment diagnostic sample contains no read failure or retry entries: recovery
is proven by injected local transport failures; it was not observed firing during
this hosted window. Passing samples do not guarantee permanent network reliability.

Independent comparison at **2026-10-03 13:18:42 Europe/Madrid** confirms **53/53
scoped complete table contents identical**, all **28 migration records unchanged**,
same owner identity/enabled/admin, zero fixtures, 20 helper checks and private
snapshot ACL PASS. Owner Auth activity is the sole equality exception described
above; all public/manual data and Storage metadata are compared. No Storage-byte
access. Advisor remains **24 ERROR / 5 WARN / 125 INFO**, zero added or removed
ERROR/WARN. Existing PIN continuity is verified by real login, without resetting it.

## Limits, remaining decisions and next package

Positive modern initial assignment, non-admin sporting success, concurrency and
rollback are proven locally. The public owner season remains legacy initialization;
no division/result/history was changed to demonstrate a positive modern mutation.
Full Launcher-to-cloud ingestion remains future work; ordinary missing observations
correctly remain pending. No physical save write, installer/updater or F code.

A final HTTPS sample measured GENERAL ~0.85 s, overview ~3.36 s and initial
review ~0.91 s. Earlier concurrent overview samples reached ~7.1 s; these are observations,
not a benchmark/SLA. Aggregate E readiness introduces no per-player HTTP loop.
The inherited overview query chain and broader invalidation remain Phase 14 work.

No unresolved owner decision blocks E. Reward policy, later milestones, lifecycle
triggers, revive semantics, Team Lock cutoff, scouting and Cup eligibility remain
in the approved contract. Future F uses final accumulated points, external Bo3 for
two tied leaders, adjusted deaths for three; unresolved exceptions/finalist rules
must not be invented. Phase 10.5 remains IN PROGRESS and Phase 11 NOT READY/NOT STARTED.
Whole-project estimate remains approximately 80%; this atomic delivery closes E.
F is authorized next, but remains unstarted. Begin with authoritative accumulated
points and existing finish/archive/Hall contracts; then implement the approved
two-player BO3 and three-player adjusted-deaths rules without inventing finalist
or residual tie policy. Phase 11 remains prohibited.
Documentation closure has its own Git commit; obtain its exact hash from Git rather
than embedding a self-referential hash here. Protected guide remains unread/untouched.
