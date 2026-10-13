# Phase 16A - Launcher / V2 cloud foundation

2026-10-13. **STATUS: PHASE 16A DONE.**
**LAUNCHER CLOUD FOUNDATION: COMPLETE. LOCAL-FIRST: PROVEN.
PHYSICAL SAVE WRITES: NOT STARTED.**
Implementation, local validation, production delivery and cleanup are complete.
The owner manually resolved the previous cleanup-policy blocker; fresh read-only
verification confirms all eight temporary paths are absent. No further package
has started.
[Evidence](phase16-launcher-cloud-foundation-evidence.json),
[exact continuation](work-in-progress/phase16-launcher-live.md).

## Entry and implementation

Entry main/origin `ce4ef255424a5a0c99954974cd22ed95349c4ea4`, fetched 0/0 and
clean tracked tree. Phase15/V2 authority was retained. The existing Python core,
SQLite journal, read-only isolated PKHeX 24.11.11 process and Gen3/4/5 DTO remain.
The ignored legacy `desktop/` Streamlit wrapper is untouched. New
`companion/launcher` is an Electron 44.7.0 development shell with a lockfile,
sandbox, context isolation, no renderer Node/network access, and six allowlisted
IPC actions over a private Python stdio pipe. No local TCP listener is needed.

The shell selects and remembers a save, verifies stable reads using the existing
watch/debounce mechanism, and shows six party slots, one PC box with arrows and
local Pokemon details. Numbers identify species/items/moves where the neutral DTO
does not carry localized names; sprites/types are not invented. Selection, party,
box navigation and details do not await network requests. A missing/locked/invalid
save leaves the last local observation explicitly stale. Save bytes are never
modified; physical apply continues to reject, and no purchase is consumed.

## Auth, ingestion, cache and offline behavior

Existing PIN/login/refresh/me verify enabled immutable trainer identity; no admin
privilege is required. Current-user Windows DPAPI encrypts persisted tokens.
PINs never enter configuration, journals, replies or logs. Cached identity is
stale until reverified. A rejected session requires re-authentication; a transient
network failure retains recovery credentials. Local user-profile observation and
cloud caches contain private data and are not a shared-machine secret vault.

Additive **043_launcher_private_observations** supplies a private, unverified
inbox and service-only receipt RPC. The server validates strict neutral DTOs,
authenticated submitter, season membership and deterministic scoped identity.
Maximum intake is 2 MiB and 60 new receipts per trainer/hour. Duplicate receipts
are immutable and do not consume the intake limit. Browser table/column access
and RPC execution are denied; RLS is forced, the helper uses SECURITY INVOKER and
a fixed empty search_path, and service UPDATE/DELETE/TRUNCATE are denied.

**A private client-observed receipt is not competitive acceptance.** The existing
registered-save path requires raw-file/trusted-parser provenance and can trigger
rewards. A client DTO/hash cannot supply that proof. The new inbox therefore does
not change current-save pointers, identity streams, medals, deaths, points, coins,
Team Locks, public PC projections or frozen history. This preserves unknown versus
observed zero and avoids manufacturing file/Storage provenance. Submitter ownership
does not certify physical game ownership; trusted promotion remains future work.

Cloud sync is explicitly enabled in the shell. Only observations enter the scoped
durable outbox: at most 64 pending and 64 retained accepted local entries. Every
delivery checks its receipt before PUT, including after timeout/restart. Five
automatic attempts are bounded; manual retry reuses the same body/identity, and
rejected observations remain stopped. A received observation is shown only for
the selected local observation, and its receipt survives restart.

The cloud worker reads current trainer, season and own wallet, preserves the cache
across offline restart, and labels its age. Heartbeat uses `/health` every 30 seconds;
ordinary cloud reads refresh every 120 seconds or for pending/manual work. Requests
time out at 15 seconds; connectivity becomes stale after 90 seconds without proof.
Recovery is automatic within the retry window, then requires the visible retry
action. A partial season listing cannot falsely establish no active season.

## Validation and performance

One full Python execution: **821 tests**, initially 818 passing and three stale
schema-inventory expectations failing. Updating those expectations for 043 gives
**15/15** in the affected file; the final cloud-runtime change and added lightweight
heartbeat case pass **13/13** focused tests. Unchanged passing tests were retained,
not rerun; 19 cases in the full run were pre-existing unrelated untracked map tests.
Prior Launcher coverage includes selection, locks, debounce, stable-byte rejection,
journal CAS, restart, backup boundaries and physical-write denial.

Real local PostgreSQL17 rebuilt all 43 migrations and generated bootstrap with
**14,163 identical schema/grant/ownership lines**. Positive private intake, exact
replay, two concurrent connections, rollback after INSERT, scope/disabled/malformed
denials, closed-scope replay and browser/service privileges pass. All **54 public
tables** were restored exactly, with no competitive side effects. Two disposable
databases were dropped. An initial fixture omitted its required discard timestamp;
the harness was corrected and completed with exact cleanup. No applied SQL changed.

Headless Edge exercised the actual renderer, Python pipe and native synthetic Gen5
save. The shell main/preload/pipe also passed in Electron with a never-shown window.
No physical desktop control or visible browser was used. Measurements are small
local fixture samples, not installer startup or large-save production benchmarks:

| Measurement | Observed |
|---|---:|
| Launch test to useful local party/PC UI | 2.38 s |
| Native read/parse/validate, separately | 195 ms |
| Cached state after process restart | 624 ms |
| Box navigation, API unavailable | median ~6.1 ms |
| Box navigation during proven in-flight 3-second API delay | median ~6.1 ms |
| Background receipt with deliberately lost response | 534 ms; one PUT, two GETs |

Source save hash stayed identical; six party/30 visible box slots, private details,
offline restart and zero renderer network requests/page errors passed. Compile,
targeted Ruff, JS syntax, formatting, dependency audit and diff checks pass. No
React/web source or native parser source changed; old phase matrices were not rerun.

## Delivery and preservation

Application source **f87a986812e85d2d60d9888dacfaa5c2c0e8b9f5** was committed/pushed
before every remote write. Fresh V1/V2, data and Advisor baselines preceded 043,
applied once as **20261013112907**. All original 34 history records remain equal;
the resulting history has 35. No migration replay or existing migration edit.

Railway **0930ba0d-695f-47dc-89fa-0060d8498add SUCCESS**, image
`sha256:7a872b7f9f51dfe938525053e5e5f11e32c44e853243e0e69b7ee1fbcdb30b75`,
received only 245 committed API build inputs in the existing project/service.
Cloudflare was not redeployed. Previous compatible Railway artifacts remain.

Production Launcher proof passed existing PIN identity, refresh/me, health, current
season/own wallet, DPAPI cached restart, own absent receipt 404, wrong/absent season
403 and anonymous GET/PUT 401. No save was selected/uploaded; positive intake was
proved locally only. No unexpected 5xx occurred in this sample; the historical
intermittent READ503 cause remains unknown and is not claimed fixed.

All **55 original non-Auth tables** in the 59-table baseline are unchanged, including
Storage metadata. New inbox: **zero rows**. Stable owner credentials/identity remain
equal; full Auth changes are session/refresh/login activity, with non-owner Auth
also equal to the retained Phase15 baseline. V1's 13 hashes and private Shadow's
6 batches / 57 mappings / 135 rows are unchanged. Remote new-table/helper security
catalog checks pass. Advisor **24 ERROR / 5 WARN / 172 INFO**, zero changed ERROR/WARN
and two added INFO findings. Remote business writes/fixtures and Storage writes: zero.

## Cleanup, limits and next action

No temporary test processes remain; PostgreSQL is stopped and both disposable
databases are absent. Private captures/logs and useful proof are retained under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase16/20261013/closure-f87a986/`.
Production validation tokens were cleared. Automatic execution review previously
rejected temporary directory deletion (`blocked by policy`); the owner subsequently
completed it manually. At **2026-10-13T11:42:57.3053102Z**, read-only checks confirm
all eight exact paths listed in the live handoff are absent, with no matching
Phase16 processes and no listener on validation port 55446. The retained successful
database DROP proof and fresh absence of the cluster/processes/listener establish
cleanup without restarting PostgreSQL. **The cleanup gate is PASS.**

Cleanup resume entry was `d16186c27b43faed6cc8f93e0374f4a18b771b0d`, main/origin
0/0, clean tracked tree. This closure changes documentation only; tests, PostgreSQL,
migration 043 and deployments were not rerun. Earlier validation and remote results
remain retained evidence. Obtain the final documentation commit from Git rather
than a self-referential hash.

This is a Windows development shell, not a bundled installer/updater. Gen6/7,
trusted competitive observation promotion, public PC expansion and physical writes
remain outside this delivered foundation. No new package is started. Exactly one
recommended next packet: **GEN6/7 READ SUPPORT**, beginning with X/Y. Stop here;
do not start it automatically.
