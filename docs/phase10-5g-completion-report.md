# Phase 10.5G - Participant-owned revived-after-wipe counter

Closed 2026-10-05 (Europe/Madrid). **G DONE / STAGING_DONE_ZERO_RESIDUE.**
[Local closure](phase10-5g-closure-evidence.json),
[public evidence](phase10-5g-public-evidence.json),
[security comparison](phase10-5g-security-advisor.json).

## Entry and authority

Entry `b92b3dd26e182a288a4614e4bef61dade9fb8d43`, main/origin 0/0 and clean
tracked tree. F was closed and publicly delivered. Fresh G entry observed the
pinned Supabase V2 project `uwleqeuzsveqlugugzba`, 29 records through
037=`20261003121543` once, 55 scoped tables and unchanged enabled/admin owner
identity. Advisor: 24 ERROR / 5 WARN / 131 INFO. Existing Railway and Cloudflare
F deployments remained current until the G delivery below.

The normal participant now reads and sets their own absolute
`season_player_stats.revived_after_wipe` count. Verified enabled JWT identity
determines the trainer and season participant; the browser cannot supply either
as command authority. No admin counter editor or exceptional override existed,
so none was invented. Nonnegative integers use the existing int32 storage bound;
negative, fractional, string, boolean, overflow and spoofed-identity inputs fail.

The existing formula remains authoritative: visible dead facts plus the existing
purchased-revive contribution plus **2 per revived-after-wipe Pokemon**, equivalent
to **-0.4 points each**. The five-visible-plus-one-wipe example yields seven
adjusted deaths and -1.4 points. The existing expression is promoted to bigint
before multiplication so the entire stored integer range remains valid. Purchased
revive semantics and their unresolved extra-penalty decision are unchanged.

The counter is live competitive state, not a save observation or physical revive.
Unknown visible deaths remain unknown in GENERAL; E remains unready without its
required observed evidence. No replacement total is computed in React. Live
changes feed applicable future calculations without changing frozen initial A/B,
closed-day points/ranking/rewards, championship certificates or archived Hall.

## API, lifecycle and React

GET/PUT `/v1/seasons/{season_id}/wipe-revivals` returns a narrow typed own state.
PUT uses a stable idempotency key and expected revision; `metadata.wipe_revision`
defaults logically to zero only when absent. Existing rows are not backfilled.
Same key/body replays; changed body conflicts; stale revision fails. A real change
atomically updates the counter/revision, records `WIPE_REVIVALS_UPDATED` and stores
a receipt. An unchanged value stores only the receipt, preserving timestamps,
fingerprints and revision. Rollback leaves no partial effects. There are no
automatic mutation retries; an explicit uncertain-outcome retry retains key/body.

Existing season/participant/day locks serialize updates with close, initial split,
finish and participant exit. Only an active participant in an active, eligible
League context may change the counter, including modern first-segment gameplay
before initial A/B. Final-day close, finished/archived seasons and ineligible or
inactive participation are read-only. Discarded seasons are unavailable. Stable
receipts can replay after close without mutating history for the still-authorized
actor. No broader lifecycle policy is introduced.

GENERAL contains the personal **Revividos tras wipe** card, current count,
**Actualizar revividos**, the 0.4-point explanation and a pending-save notice when
death observation is unknown. Stale changes refresh for review with human wording.
Revision, RPC and database details are not product-facing. Invalidation is limited
to the owned counter, GENERAL, initial assignment and current admin day; no new
overview, PC, shop or Cup refresh chain.

## SQL and security

Forward **038_participant_wipe_revivals**, applied once as **20261004222029**, adds a
service-only RPC and replaces only the affected arithmetic helper. No new table,
column, default, row backfill or historical rewrite. All 37 preceding migration
files and all 29 preceding remote migration records are unchanged.

A read-only preflight found inherited authenticated TRUNCATE/REFERENCES/TRIGGER
privileges on stats, despite existing DML denial. Before any remote apply, 038 was
hardened to revoke all browser table/column write and schema capabilities while
preserving RLS reads, ownership and service permissions. The local security test
reproduces hosted default grants and proves their removal transactionally. Both
touched helpers use SECURITY INVOKER, fixed search_path and no PUBLIC/anon/
authenticated execution. No private save payload is returned.

## Complete closure and local PostgreSQL

**694 Python PASS / 0 FAIL / 0 ERROR / 0 SKIP, exit 0; 22 React PASS; 34 Edge PASS**,
including six G browser scenarios. Compile, touched Ruff, TypeScript, Prettier,
production Vite build, Workers dry-run and diff check pass. Browser evidence is
retained unchanged-source PASS: current source hashes match the saved full report;
desktop/mobile behavior and the mobile screenshot were reviewed.

Real PostgreSQL 17.11 G validation passes **nine groups, nine concurrent scenarios
and three rollback boundaries**, with exact restoration of all 49 public tables.
Full affected 026/027/028/029/030 and B/C/D/E/F families pass sequentially, each with
exact restoration. Four independent migration/bootstrap builds produce **12,175
identical schema/grant/ownership lines**, with catalog/RLS checks. Dedicated
Cup/shop reruns are not applicable: their code and purchased-revive semantics were
not changed; existing 029 compatibility cases pass. Local PostgreSQL is stopped
after zero remaining client sessions.

Interrupted attempts are preserved in the closure evidence, not relabelled PASS.
Earlier fixture cleanup/timestamp issues were corrected in the harness. Native
Python and PostgreSQL crashes required fresh successful reruns; affected inherited
databases were restored exactly from saved 49-table baselines and only known G
fixture scopes were cleaned. A later PostgreSQL Windows event identifies
`libcrypto-3-x64.dll` with `0xc0000005`. The final unchanged G suite passes using a
process-local `OPENSSL_ia32cap=:0` compatibility override, documented by
[OpenSSL](https://docs.openssl.org/3.5/man3/OPENSSL_ia32cap/). This mitigates the
local test environment; it does not establish a root cause or change production
cryptography. A transient Supabase CLI read failed before any write; a new full
preflight succeeded. Raw evidence remains under `%TEMP%/phase10-5g-*`.

## Delivery and preservation

Initial checkpoint `a53a9421f53c029e510d5b0996aacd14eb5796a7` and final application
source **848e7b0177d26230315424d7edef9a6a3ca466af** were committed/pushed before remote writes. Fresh target,
history, complete/scoped data and Advisor baselines preceded the single 038 apply.
History now contains 30 records. Supabase validation preceded Railway; healthy
backend/new-route authentication preceded Cloudflare.

Railway **f21954a8-7624-4aaf-ad76-890469355878 SUCCESS**, image `sha256:b28ea95501afbe722845c996b3a325667fa570813ce97fbb1d3e992be20e1e20`, uses the same source and only
232 committed API deployment inputs. Cloudflare deployment **7a7bdf65-0b40-4707-a199-2df331aff3e5**,
version **f356e801-af3e-452d-884b-0b133778c0dc**, serves that source at 100%. Live JS/CSS equal the local
build; HTTPS, deep SPA, MIME, CSP, nosniff and exact CORS pass.

Public run **phase10_5_public_reads_9a1a6007939d401299998b951ba432bb PASS**, exit 0: **37 API requests and 22 real
browser visits**, no API interception or browser errors. Existing owner PIN login,
JWT refresh and own-counter read pass. G denial commands target an independently
verified absent season; the real owner's counter is never submitted or changed.
The public mobile card was reviewed for legibility. Positive counter mutations,
races and rollbacks are proven locally only.

Independent final comparison: **55/55 scoped tables identical**, **30/30 migration
records unchanged** after apply, zero new tables and zero wipe revision metadata
rows. Owner identity/PIN/admin, seasons, results, divisions, Team Locks, save facts,
economy and frozen history are preserved. Full Auth baselines are captured;
only the owner's login/session activity is excluded from scoped equality, with
stable identity/credential hashes compared separately. Storage metadata is fully
included and no Storage bytes were touched. Remote business writes/fixtures: zero.
Advisor remains **24 ERROR / 5 WARN / 131 INFO**, with zero added or removed
ERROR/WARN. Both helper catalogs and stats ACL/RLS/ownership checks pass remotely.

## Remaining scope and next step

One hosted sample measured own-counter read **0.78 s**, GENERAL **1.48 s** and overview **4.80 s**. These are individual staging observations, not a production load
benchmark. Broad overview latency remains a Phase 14 candidate. No per-player
HTTP loop or second death formula was added.

The existing owner decisions remain: badge/completion economy, normal lifecycle
operator, residual/4+ championship ties, finalist, purchased-revive extra penalty,
Team Lock cutoff, scouting scope, League DQ/Cup and future game milestones. None
blocks G. Physical saves, full cloud ingestion, shop repairs and wider Admin or
Team Preview changes remain outside this package.

The documentation closure is a subsequent commit; obtain its exact final HEAD
from Git. Explicit staging only; the protected guide remains untouched/untracked.
Phase 10.5 **IN PROGRESS**; Phase 11 **NOT READY / NOT STARTED**.
**STOP after G.** H is the next remaining package and requires the next explicit
owner continuation. No H or Phase 11 work has started.
