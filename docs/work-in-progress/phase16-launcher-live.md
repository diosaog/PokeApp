# Phase 16A — Launcher / cloud foundation

PHASE: 16A. STATUS: LOCAL VALIDATION GREEN / delivery pending.
ENTRY HEAD / HEAD: `ce4ef255424a5a0c99954974cd22ed95349c4ea4`, main/origin 0/0,
tracked clean at entry. Phase 15 is closed; do not reopen cutover.

CURRENT LAUNCHER ARCHITECTURE: Python `app/launcher` UI-free development core;
isolated .NET 8 `companion/parser/PokeApp.Parser`, pinned PKHeX.Core 24.11.11,
neutral `ObservedSave` (Gen3/4/5). `desktop/` is a legacy Electron 31 wrapper
loading Streamlit; it is not wired to the modern local core.

ALREADY IMPLEMENTED: safe read-only save selection/discovery; snapshot stability;
poll/debounce; SQLite observation journal and backup operation seam; profile lease;
PIN/refresh/me V2 auth in memory. Physical writes reject. Local `SYNCED` means
journaled only, not cloud. Existing journal/config must be reused.

MISSING FOR 16A: useful local party/one-box UI; persistent protected auth;
background cloud/cache/queue/status; authenticated observation receipt and
reconciliation API. Existing identity RPC assumes trusted registered parsed
saves; a client DTO/hash is not proof of trustworthy competitive facts.

CURRENT STEP: closure/delivery of new local Electron 44.7.0/stdio UI, independent local
and network workers, DPAPI session persistence, scoped cache and bounded persistent
outbox. Receipt lookup always precedes PUT, including unknown-outcome recovery.
Migration 043 adds one private unverified inbox with service-only RPC: existing
save_files/parsed_saves require raw-file provenance and drive competitive rewards;
client DTOs cannot safely become trusted registered saves. Inbox does not change
save/identity heads, rewards or public projections. Unknown remains unknown.
NEXT STEP: commit/push validated source, then 043 once and API-only deployment;
authenticated read-only proof, preservation comparison, exact cleanup and docs.
TESTS ALREADY VALID: Python full 821 executed (includes 19 pre-existing untracked
map tests); 3 stale schema inventory expectations corrected, all affected 15 PASS.
Other 818 PASS unchanged, including 12 new foundation tests and existing Launcher.
Real PG17: 43 migrations/bootstrap equal (14,163 lines), 54 tables restored exactly,
concurrency/replay/rollback/privacy/security PASS. Headless native Gen5/UI PASS:
2.47 s useful UI, 195 ms parse, 686 ms cached restart, ~6 ms box navigation during
a proven in-flight 3-second network wait. Lost response: one PUT, two receipt GETs.
Actual Electron main/preload/stdio passes with hidden window, sandbox and isolation.
Compile/Ruff/JS syntax/diff PASS. No web UI or native parser source changed.
LOCAL STATE: two owned PG databases dropped; fresh cluster still running at
127.0.0.1:55446, data %TEMP%/phase16-pg-20261013. Remove owned fixtures/profile
directories after delivery; evidence in %TEMP%/phase16-evidence. No UI visible.
REMOTE STATE: fresh 2026-10-13 baseline confirms 34 migrations through 042,
59 scoped tables, V1 unchanged; Advisor 24 ERROR / 5 WARN / 170 INFO. Captures
private in %TEMP%/phase16-evidence/before. No 16A remote writes yet. Existing
Railway project/service and SUCCESS 9b75a24f verified. Cloudflare unchanged.
DO NOT REPEAT: historical phases, cutover QA, broad discovery. Never touch the
protected guide or unrelated untracked files. CLI/headless only.
IF QUOTA ENDS: inspect Git diff and this checkpoint, resume first incomplete unit;
do not represent foundation or ingestion as complete without tests and delivery.
