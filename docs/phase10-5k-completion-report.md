# Phase 10.5K - Safe public competitive scouting

ENTRY CHECK: **J DONE VERIFIED**, entry main/origin
`37ac03294df8bac095e335abfe66098dcaa97b03`, clean tracked tree, 0/0.
The separate queued owner instruction authorized K after J closure.
Application source **23081e146a8c00a57142242369161bc2b7e0f2c8** was committed/pushed
before any deployment. [Local evidence](phase10-5k-closure-evidence.json),
[public evidence](phase10-5k-public-evidence.json).

## Implementation and public contract

**Entrenadores → Explorar equipos públicos**, or the named link on a trainer card,
opens `/entrenadores/scouting`. One trainer selector works independently of scheduled
matches. The new authenticated GET `/v1/read/seasons/{season_id}/scouting` reuses
H's Team Preview service with an internal single-public selection. It adds no second
Team Lock or private projection. Existing season roster and current-day semantics
remain authoritative, including frozen current-day locks in historical seasons.

Each Pokemon exposes exactly **species, nickname, level, types, item and moves**;
move entries expose **name only**. Envelope fields carry season, day, trainer names
and selected trainer for navigation. PP, shiny and timing details are omitted from
this deliberately narrower contract. Missing optional facts stay unpublished.
A missing lock is null; absent day/roster is explicit. No fake six-slot team and no
previous-day, live party/save, PC, dead-box or parser fallback.

Self and admin use the same public scouting contract. IVs, EVs, nature, ability,
raw metadata, original-trainer/private identity, provenance and linking evidence
cannot enter the response. Explicit nested DTO allowlists remove unapproved keys;
malformed approved data, invalid six-Pokemon snapshots, ambiguous roster/locks and
read failures return a sanitized failure. Viewer/private/self/admin/mode overrides
are rejected before repository access; JWT identity controls the viewer.

H's spectator/rival/private-self behavior is preserved. Scouting caches use a separate
endpoint and session/season/selection keys. Changed selections do not retain an old
team. A confirmed Team Lock invalidates this season's preview/scouting caches;
manual public refresh is available. Desktop/mobile reuse the existing visual system.
No mutation, parser/cloud, sporting, lifecycle, Cup or timing rule was changed.

## Validation and database

FRESH PASS: **13 focused K Python**, **745 full Python**, **57 React**, **21 affected
Edge** tests. Full Python includes 726 committed-scope tests and 19 pre-existing
untracked map tests; those files remain unstaged. Edge includes six K, six H and nine
shared-flow tests, with no skips/flakiness. Negative cases cover self/admin/rival,
authority spoofing, invalid/disabled JWT, wrong season/participant, malformed nested
facts, missing data, private-mode cache separation and absence of save reads.

PostgreSQL **17.11**, loopback disposable database through current 039: **six H/K
projection/security groups**, exact **50-table restoration**. Actual repository
column selections, RLS public/private reads, anonymous denial and service-only Team
Lock mutation grants pass. Frozen teams survive later save changes; malformed public
snapshots fail closed. PostgreSQL stopped after the runner. No remote fixtures.

TypeScript/public build, Python compile, targeted Ruff, full Prettier, Wrangler
dry-run and diff checks pass. **No migration/schema change**; rebuild/bootstrap and
unrelated economy/championship/Cup SQL matrices were **NOT RERUN / N/A**, rather than
claimed freshly green. Existing applied migrations are unchanged.

## Delivery and public evidence

Closed **2026-10-08: K DONE / STAGING_DONE_ZERO_RESIDUE**.
Railway **f11b0a8d-878e-49d6-923b-9df35dff8aef SUCCESS**, image
`sha256:fde4379004be1620cd3603832717779ecda5ece7d7b6c4d9c24bd66844ccfa1d`, committed source above. Only **236 committed API inputs**
were uploaded. Authenticated new-route checks passed before Cloudflare deployment
**7173a0cf-c746-46a8-b5ff-0a56e95cdc8b**, version **8cbde4f2-e51f-4c87-8056-61009d003538**,
100%, same source. Live JS/CSS match the local public build. HTTPS/deep SPA, MIME,
CSP/nosniff, exact CORS and authentication boundaries pass.

Public smoke: **12 API checks**, including 401/422/404 denials and H compatibility;
**six real Edge states** for three trainers at desktop/mobile sizes, eight successful
browser API responses, manual refresh and clean logout. No API interception, page
errors, PC/overview/private fallback reads or business writes. All three sampled
locks were absent: the missing-state result is positive hosted evidence; six-Pokemon
content is local proof only.

Fresh **56/56 scoped tables identical**, **31/31 migration records identical**,
039 once as `20261007121317`. Owner identity, PIN/credentials/admin and manual
seasons/results/economy/Team Locks preserved. Full Auth snapshots retained; only
this owner's login/session activity is excluded from scoped equality, with stable
credential checks separately equal. Storage metadata included; no Storage bytes
changed. Advisor **24 ERROR / 5 WARN / 138 INFO** before and after; zero new or
removed ERROR/WARN. No new migration, replay or remote business fixtures.


## Performance, limits and remaining work

Five bounded repository reads for a selected current-day team, independent of roster
size; no per-trainer HTTP loop or overview expansion. Direct scouting navigation
reads neither overview nor PC. Public samples: **3.51 s** initial, **2.27/2.23 s**
other selections. These are individual hosted samples, not a load benchmark. Shared
roster/current-day aggregation and reducing round trips remain M/Phase 14 candidates.

Public data currently lacks locks for the three sampled trainers, so positive
six-Pokemon display/privacy is proved by local API, real PG and browser fixtures;
it is not claimed as a positive hosted lock check. Local positive and public missing
state mobile screenshots were reviewed. No data was created just to improve proof.
The product scope is the permitted competitive Team Lock; broader PC/save publication
is neither enabled nor implied. J's documented lifecycle/championship/timing backend
extensions remain separate and do not reopen resolved owner rules.

Manual review for Antonio: open Entrenadores, choose Equipos públicos or a trainer's
named link, switch trainers, inspect the missing-lock message and repeat on mobile.
When a normal Team Lock exists, inspect species/mote/level/types/item/moves and confirm
that IV/EV/nature/ability are absent. No fixture creation is needed for this review.

Changed files: scouting DTO/service/route and minimal H reuse, React scouting/trainer
entry/shared Pokemon typing/cache refresh/generated types, focused API/React/Edge
and shared local PG checks, contract/checkpoint/handoff and evidence. Protected guide,
unrelated ZIP/AI-map/validator files and all owner data remain untouched.
Documentation closure is a subsequent commit; its exact HEAD is obtained from Git.

**NEXT: L, awaiting separate owner instruction. STOP after K.**
Phase 10.5 IN PROGRESS. **PHASE 11 READINESS: NOT READY / NOT STARTED.**
