# Phase 10.5M - Performance guard

Closed 2026-10-08. **STATUS: M DONE / STAGING_DONE_ZERO_RESIDUE.**
**ENTRY CHECK: L DONE VERIFIED.** Entry main/origin
`4a7537438ad19cdd6152d339b07caad4bd94de93`, fetched 0/0, clean tracked tree.
[Local evidence](phase10-5m-closure-evidence.json),
[public comparison](phase10-5m-public-evidence.json),
[ranked candidates and exact follow-up locations](phase10-5m-performance-candidates.md).

## Implementation and structural comparison

Inventory previously loaded the whole overview solely to name redemption targets.
It now requests the existing public trainer-name list only while a redemption is
open. The authenticated query remains keyed by viewer; no per-target requests,
new cache infrastructure or client authority. Loading/missing/failed names retain
the existing fallback. Target identity, ownership, eligibility, exact wallets,
mutation bodies, idempotency, uncertain retries and invalidations are unchanged.

| Cold Shop, fresh browser context | Before | After |
| --- | ---: | ---: |
| Business API reads, excluding login/me/season selection | 3 | 2 |
| Decoded business response bytes | 30,060 | 12,535 |
| Overview reads | 1 | 0 |
| Eager name-list reads | 0 | 0 |

This removes **17,525 bytes (58.3%)** and one unnecessary request. The omitted
overview composes 12 bounded row requests plus one progress RPC for a participant.
Opening redemption instead adds one names query, selecting only `id,display_name`.
The new Python guard verifies 1/100-player budgets; these are business repository
round trips, not SQL statements inside RPCs or JWT/principal resolution.

## Measured flows and timing caveats

Same method before/after: three sequential authenticated GET rounds, same order,
one fresh HTTP client per phase, unchanged manual season. All 54 measured GETs
returned 200 with exact CORS and `no-store`. Values below are median seconds of
only three observations; individual samples remain in the public evidence.

| Flow | Before | After | Decoded bytes, both phases |
| --- | ---: | ---: | ---: |
| GENERAL | 0.786 | 0.838 | 3,062 |
| Overview / Trainers | 3.529 | 3.616 | 17,525 |
| Public scouting | 2.081 | 1.861 | 1,107 |
| Shop | 1.734 | 1.601 | 12,506 |
| Inventory | 2.123 | 1.826 | 29 |
| Self progress | 0.786 | 0.801 | 132 |
| Admin setup | 0.827 | 1.158 | 6,980 |
| Championship review | 1.094 | 1.155 | 282 |
| Public trainer names | 0.909 | 0.773 | 692 |

The API was not optimized or redeployed. These fluctuations are **not evidence of
backend speed improvement**. Final cold browser login-to-settled-API observations
were desktop 11.202 → 6.713 s and mobile 10.307 → 6.943 s, one sample each. They
include authentication, season selection and the harness quiet period; they are not
render-time benchmarks. Removing the unused request is the proven improvement.

Initial public harness attempts timed out on whole-page network idle or an exact
intermediate response count. The final comparison waits for application API
completion, excluding recurring environmental Kaspersky traffic. Two actual 503s
occurred in the first post-deploy mobile attempt; recent unchanged-API logs also
contained overview 503s. The fresh final desktop/mobile run passed without API or
page errors. **The transient failure's cause remains UNKNOWN; M does not claim it
is fixed.** Raw failed evidence is preserved alongside the final passing run.

## Tests, scope and delivery

FRESH PASS: **757 Python** (738 committed-scope plus 19 untouched pre-existing
untracked tests), **23 focused read tests**, **63 React**, **5 affected Edge tests**.
The five Edge cases include reward/promotion behavior, original-key/body uncertain
retry and two new cold Shop/name-read guards. Their first count included cancelled
development StrictMode requests; the corrected guard counts completed responses.
No product change was needed for that correction. TypeScript/public build, full
Prettier, targeted Ruff, compile, Wrangler dry-run and diff checks pass.

Backend/API/repository/SQL/parser source is **RETAINED UNCHANGED-SOURCE**.
No migration. Real PostgreSQL, rebuild/bootstrap, native parser and unrelated
mutation concurrency matrices are **NOT RERUN / N/A** for this frontend read change.
Supabase history remains 32 rows; 040=`20261008185548` still applied exactly once.

Application source **`60367135c514ad0b8423c3051981137e2db420bf`** was committed/pushed
before deployment. Cloudflare deployment **`d9751374-7b4d-4468-aaf6-aaa7bdc50f04`**,
version **`7e501a60-7fac-4fb0-a1f0-4a5181496a7f`**, 100%, that exact source. Live
JS/CSS bytes equal the production build. HTTPS, `/tienda` SPA fallback, MIME/CSP/
nosniff, exact CORS and unauthenticated denial pass.
Railway remains L deployment **`3a3ebb14-ba87-43e0-839a-639920d5f6bf SUCCESS`**,
source `94386d6c2fdceb5ac8625dbcc83648f469e027fa`; no API or DB deployment.

Final real Edge smoke covers fresh desktop/mobile Shop contexts, verified existing
owner login, two business reads, no overview/name preload, responsive width and
clean logout. No API interception or business commands. Desktop layout and mobile
top viewport were reviewed. Owner inventory is empty: positive redemption/name
interaction is local evidence only, without creating public fixtures.

Independent final comparison: **56/56 scoped tables and 32/32 migration records
identical**. Owner identity, credentials/PIN, enabled/admin role and all manual
competitive data remain intact. Full Auth baselines are retained privately; only
expected owner's session/refresh/login activity is excluded from scoped equality,
with stable credential facts compared separately. Storage metadata included; no
Storage bytes touched. Remote business writes/fixtures: **zero**. Advisor remains
**24 ERROR / 5 WARN / 138 INFO**, zero new or removed ERROR/WARN.

## Deferred work and closure

**Phase 14:** HIGH — broad overview/Trainers and inventory rival identity N+1;
MEDIUM — Shop/scouting aggregation, Admin refetch breadth and intermittent hosted
availability; LOW — speculative changes to already aggregated General/progress/
Admin reads. Each candidate records evidence, proposed approach, risk and reason
for deferral in the linked candidate document.

**FINAL 10.5 PRODUCT ALIGNMENT:** simple prospective Admin rule editing; immediate
cross-view refresh; clickable visual trainer profiles with correct privacy;
Comodines/Bayas/Competitivos/Crianza organization; concise visual product. Exact
current invalidation sites are recorded without widening this package.

**Known implementation debts:** participant normal League lifecycle authority,
championship 4+ / residual tie backend support and reliable first-Team-Lock timing.
These are approved-but-unimplemented rules, not new owner-decision requests.

Files changed: Inventory, its economy test, new browser performance guards, read
budget test, candidate/report/evidence docs, alignment contract, checkpoint and
live handoff. Protected guide and unrelated untracked files untouched; explicit
staging only. Entry/application HEADs are above; documentation closure is the
subsequent commit carrying this report, whose exact HEAD is obtained from Git.

**NEXT: FINAL 10.5 PRODUCT ALIGNMENT. STOP after M.**
Phase 10.5 IN PROGRESS. **Phase 11 NOT READY / NOT STARTED.**
Neither final alignment nor Phase 11 has started under this package.
