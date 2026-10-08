# Phase 10.5L - Observed badges and in-game Champion progress

Closed **2026-10-08: L DONE / STAGING_DONE_ZERO_RESIDUE**.

Entry **K DONE VERIFIED**, main/origin
`5f40737a02d209b6158b31f4598cf8b79c42080d`, fetched 0/0, clean tracked tree.
Application source **94386d6c2fdceb5ac8625dbcc83648f469e027fa** was committed and
pushed before remote writes. [Local evidence](phase10-5l-closure-evidence.json),
[public/security evidence](phase10-5l-public-evidence.json).

## Already satisfied by E/I

**ALREADY SATISFIED BY CURRENT SOURCE:** strict neutral regional badge flags;
unknown distinct from observed zero; E readiness from the first two primary-region
badges; reader/3 nullable in-game `champion_defeated`; I configurable default 4 coins
per newly proven badge and 12 once per season for proven Champion completion.
Replay/regression never repays those claims. L does not change the parser, sporting
readiness, reward engine or any historical snapshot.

Supported native families remain RS/E/FRLG, DP/Pt/HGSS and BW/B2W2. HGSS keeps Johto
and Kanto separate. BW completion uses Hall-of-Fame evidence, not the Ghetsis story
flag. Eight badges alone do not prove game completion. In-game Champion defeat is
separate from a PokeApp title, season finish/archive and competitive Hall.

## Actual gap closed

Trainers previously showed badge counts alone, with legacy default counters able
to masquerade as observations. No participant surface exposed reliable Champion
completion. Trainers and Saves now share a clear progress display: unknown/pending,
observed medal totals, regional earned/missing medal positions, observation time
and Champion true/false/unknown. Sparse medals remain sparse; a count without a
regional set never invents identities. Technical flags and parser/identity details
are not shown. A failed read does not become zero or a fresh negative observation.

GET `/v1/read/seasons/{season_id}/progress` selects self from verified JWT, rejects
override/attestation parameters and has no mutation method. The overview reuses one
aggregate progress read for all seasons. Its compatibility badge counter retains
primary-region meaning; the new total includes both observed HGSS regions.

Forward **040_observed_progress_read** adds one bounded STABLE SECURITY INVOKER
function with fixed search_path and service-only execution. One statement snapshot
joins the current save pointer, latest accepted identity revision, owned save and
matching parsed payload. It reuses I's source/progress validators. Missing, stale,
deleted, foreign, malformed or unsupported evidence is unknown or fails closed.
The public DTO validates the neutral contract and exposes an explicit allowlist.
No tables, reward mutations, row locks, per-player HTTP loops or broad invalidation
were added. Later observations describe current game state only.

Full Launcher/cloud upload and public installer remain unfinished; local journal
sync does not publish observations automatically. No physical save writes.

Changed files cover progress DTO/projection, read repository/routes/overview,
040 plus generated bootstrap/reset inventory, the shared React progress component,
Trainers/Saves integration, generated API types, focused API/React/Edge/PG proofs
and continuity/evidence documents. Existing parser and reward source files are
unchanged.

## Validation

FRESH PASS: focused L Python **11**, full Python **756** (737 committed-scope plus
19 pre-existing unrelated untracked map tests), React **63**, affected Edge **6**,
zero skipped/flaky. Native generated-save/parser/IPC/Launcher checks: **77 PASS**,
including BW completion and unsupported/corrupt evidence. Compile, targeted Ruff,
Prettier, TypeScript/public Vite build, Wrangler dry-run and diff checks pass.

Real PostgreSQL 17.11: **7 groups**, exact **50-table restoration**, concurrent
read replay with no reward/ledger/history effects, source/ownership/regression
checks and browser RPC denials. Four fresh migration/bootstrap builds produce
**12,639 identical schema/grant/ownership lines**, with catalog/RLS checks. The old
temporary installation was missing files; a fresh disposable local cluster using
[official EDB binaries](https://www.enterprisedb.com/download-postgresql-binaries) was
used and stopped. Initial rebuild exposed a missing reset entry, fixed before all
four green builds. Browser fixture updates account for the new projection/copy,
distinct status notices and mobile navigation/relogin; final six cases all pass.

I mutation/reward semantics are **RETAINED UNCHANGED-SOURCE**; read-only economic
preservation is freshly verified locally. Unrelated Shop purchase, Cup and title
mutation matrices were **NOT RERUN**. No owner data was fabricated for positive
evidence; positive progress/Champion proof is local/native only.

## Delivery

Fresh pinned Supabase V2 baseline preceded every remote write. 040 was applied
once as **20261008185548**; the original 31 migration records remain identical.
Railway **3a3ebb14-ba87-43e0-839a-639920d5f6bf SUCCESS**, image
`sha256:51726e531ade52deb7f42da196bb30fdd136cb33fa785cbf556c2015374dd6b0`,
uses 238 committed API inputs only. Authenticated progress checks passed before
Cloudflare deployment **54102a24-2e0e-4fac-9519-3bf380888c88**, version
**03e6250b-ee79-42bc-9aeb-e17363cf86d6**, 100%, same application source.

Live assets equal the local production build. HTTPS, `/saves` SPA fallback,
MIME/CSP/nosniff, exact CORS and authentication denials pass. Public smoke:
**10 API checks**, **4 real Edge desktop/mobile states**, **8 successful browser
API responses**, no interception or page errors. Existing owner login and clean
logout pass. All eight current participants have unknown progress; no default
counter is presented as an observation. Two mobile screenshots were reviewed.

Independent final comparison: **56/56 scoped tables identical**, **32/32 migration
records unchanged after apply**. Owner Auth identity, credentials/PIN, admin role,
manual seasons, results, memberships, Team Locks and economy are preserved. Full
Auth baselines were captured; only this owner's login/session/refresh activity is
excluded from row equality, with stable credential/identity hashes compared
separately. Storage metadata included; Storage bytes untouched. Business writes
and remote fixtures: **zero**. Advisor remains **24 ERROR / 5 WARN / 138 INFO**,
zero new or removed ERROR/WARN. New function catalog confirms private execution,
invoker security and fixed search_path.

Hosted single samples: self progress **1.424 s**, overview **4.195 s**. These are
not a load benchmark. Existing overview round trips remain an M/Phase 14 candidate;
L replaces its old progress RPC instead of adding a per-player HTTP loop. Saves
loads its small self-only progress query independently of the PC read.

## Manual checks and remaining work

Antonio can inspect **Saves y Launcher** and **Entrenadores** on desktop/mobile:
pending observation must not say zero; a reliable save must show its actual regional
medals and known/unknown in-game Champion status. The refresh button rereads PokeApp;
it does not upload a local save or grant rewards. Current owner data need not be
changed to inspect the unknown state.

J's resolved-but-unimplemented debts remain: normal participant OPEN/CLOSE/FINISH
authority, 4+ championship leaders/residual tie resolution and reliable first-lock
timing. They are implementation gaps, not new owner-decision requests. No M or
Phase 11 work belongs to L. The protected guide and unrelated untracked files remain
untouched. Documentation closure will be a subsequent commit; obtain its exact
HEAD from Git instead of a self-referential hash.

**STATUS: L DONE. NEXT: M, requiring its separate instruction. STOP after L.**
Phase 10.5 remains IN PROGRESS. Phase 11 **NOT READY / NOT STARTED**.
