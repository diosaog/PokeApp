# Phase 9 delivery report - parser boundary / Launcher base (DONE)

Date: 2026-09-28. Entry `30d670a50a990b92d37620d90290463e594dcd78`, main,
fresh remote equal, 0/0, tracked clean. Protected guide was the only untracked
file and remains untouched. Phase 8/8L closure was preserved.

**DONE for the approved local parser/Launcher foundation.** Functional binary
inspection, local observed-state sync, auth client, queue and verified backups
are delivered. No installed end-user Launcher, cloud save ingestion, competitive
current-state promotion, physical mutation or public API deployment is claimed.
Phase 10 has not started. Weighted complete-project estimate **~70% -> ~73%**.

[Contract](phase9-parser-launcher.md), [usage](../companion/README.md),
[dependency/license](phase9-pkhex-dependency.md),
[sanitized evidence](phase9-validation-evidence.json).
The [live handoff](work-in-progress/phase9-live-handoff.md) is closed/superseded.
Follow the [MultiIA protocol](AI/PokeApp_Multi_AI_Continuity_Protocol.md).

## Entry audit and decisions

| Classification | Finding / disposition |
|---|---|
| Reusable | Pure PokemonIdentityEvidence/location/reconciliation from 023; Team Lock snapshot isolation; PIN login/refresh/me |
| Needs adaptation | Existing ParsedSave requires server-owned save/trainer IDs. Local parsing emits unbound ObservedSave, without invented app identity |
| Legacy/reference | conex_pkhex.py, mutation-capable bridge and mtime caches. Process interop is useful; legacy dispatch stays unchanged |
| Legacy/reference | Ignored desktop Electron wrapper opens Streamlit; it has no Companion sync engine and remains untouched |
| New | Read-only .NET worker, strict neutral IPC, snapshot reader, UI-free Python Launcher core |

No Phase 9 contract existed at entry. The reduced contract was written before
implementation. No unrelated Phase 8 audit/refactor. No trusted remote ingestion
boundary exists: local sequence/hash/mtime or HTTP arrival order cannot satisfy
023 CaptureOrder. Sync primitives therefore persist local observations without
adding speculative cloud tables/endpoints or silently promoting authority.

## Parser and identity

`app/save_parser` provides SaveParser, SaveSource, FileMetadata, SaveFingerprint,
ParseResult, strict schema-v1 models and explicit errors. DTOs contain game family,
generation, trainer, six party slots, complete boxes, numeric Pokemon data,
moves/PP, IVs/EVs, egg status and private typed 023 identity evidence. No PKHeX
classes, arbitrary metadata, raw PKM blobs, local paths or app-owner claims.

`companion/parser/PokeApp.Parser` takes bounded bytes on stdin and returns JSON.
No mutation flags, file paths, UI, network or legacy dispatcher. Exact NuGet
PKHeX.Core 24.11.11 and content-hash locks. Native main-series Gen3/4/5 families
recognized by the pinned parser are allowed. Save and occupied-Pokemon checksums
are checked; unsupported/ambiguous variants, insufficient identity and parser
errors reject explicitly. No legality, exhaustive emulator/ROM-hack support,
silent repair or successful empty fallback is claimed.

File identity is SHA256 + byte length, separate from game/player identity.
Device/inode, size and nanosecond mtime guard consistency. Read bounded snapshot,
parse immutable bytes, reread and compare metadata/hash before acceptance. Native
Windows read-only shared handles preserve sharing errors. This is optimistic
verification, not a promise an emulator cannot write after it; future physical
replacement needs its own guarded write/recovery boundary. Unchanged content is
hashed but not reparsed. No infinite retry.

Local comparison emits NEW/MOVED/CHANGED/MISSING/AMBIGUOUS/UNCHANGED hints. PID
collisions/core-evidence changes remain ambiguous. Pairwise hints are not a sticky
authoritative resolution ledger. Existing 023 owns persistent ambiguity/UUIDs;
local code allocates none. Tests feed exported inputs into existing reconciliation:
moves retain known entities; clones receive no guessed binding. Gen3-5 EC stays null.

## Launcher, sync and trust

`app/launcher` includes config, manual/configured-folder discovery, polling/debounce,
SaveSyncService, LocalJournal/LocalOperationQueue, BackendClient/LauncherSession,
BackupService, LauncherCore and CLI composition. Folder enumeration is flat and
bounded; multiple candidates are returned without arbitrary selection.

**SYNCED means a local observation was committed**, explicitly labelled
LOCAL_OBSERVATION_JOURNAL. NO_CHANGE reuses the current receipt without parsing.
Changed content is inspected and recorded with CAS; duplicate concurrent commits
converge on one receipt. Restart preserves receipts. Returning to old bytes is a
local transition, not evidence of newer gameplay. INVALID/UNSUPPORTED/CONFLICT/ERROR
do not advance the head. Polling detects changes without watcher events.

Private profile SQLite is independent of V1/V2. Queue states are PENDING/RUNNING/
SUCCESS/FAILED/CANCELLED, with atomic claim, idempotent IDs and no silent replay.
Interrupted RUNNING becomes FAILED/RECOVERY_REQUIRED only after obtaining the
single-profile OS lease. CLI holds the lease; future embedding UI callers must too.

BackendClient uses existing PIN login/refresh/me routes, fixed paths and HTTPS
(loopback HTTP for development). Redirects, disabled accounts and mismatched
subject/trainer are rejected. Tokens/PIN never enter config/journal/logs; tokens
stay in memory, cleared on logout. CLI login checks identity then discards session
on exit. No token vault or production login UI. Auth transport was validated with
controlled HTTP responses, not new real Supabase users or a deployed API.

Paths originate in local user selection/config. Canonicalization rejects UNC,
device/ADS paths, directories, unexpected extensions and retargeted sources;
folder discovery excludes links/out-of-root candidates. Backend DTOs supply no
paths. Logs contain IDs/status/version/error codes, not paths/tokens/save bytes or
Pokemon payload. Observations and backups are private local data, not encrypted
save storage; credential non-persistence is a separate guarantee.

## Backup and historical safety

Preparation validates snapshot/expected fingerprint, exclusively creates a UUID
backup with original bytes, flushes it, writes operation/time/source/fingerprint
metadata, verifies backup hash and rechecks the source before returning a ticket.
Failed preparation never marks an operation successful. Interrupted preparation
may leave a useful backup associated through metadata, with recovery required.
Existing saves/backups are never replaced by preparation.

BackupService.apply always raises PHYSICAL_WRITES_DISABLED, even with a valid
ticket. Future code must validate authorization/source, verify backup, serialize
and verify temporary output, recheck/replace the live file and verify or recover.
No in-place mutation or automatic restore runs in this phase.

Architecture tests prohibit parser/core imports of authoritative repositories,
application services, API, Supabase or legacy storage. Changed observations are
recorded while a frozen Team Lock snapshot stays identical. This proves the new
isolated flow, not a historical database rewrite. League/Hall/archive/Cup/sanctions/
Team Lock implementation remains byte-for-byte unchanged from entry.

## Validation ledger

Final tested source: **f2158ed2c4888857adb90ef5092a6e8a0af5feb0**, published and
fresh remote-matched. Windows, Python 3.14.3 API environment, official portable
.NET SDK **8.0.425** (download SHA512 verified), locked packages. Commands ran
2026-09-28. Final documentation changes do not change tested source.

| Command / check | Result |
|---|---|
| Standard unit runner, --pattern test_phase9*.py | **32 PASS**, exit 0 |
| .venv-api/Scripts/python.exe tools/run_unit_tests.py | **543 PASS** (511 + 32), no skips, exit 0, 29.223 seconds |
| tools/validate_phase9_launcher.py --dotnet <portable-dotnet.exe> | Locked restore/build, **24 .NET assertions + six integration groups PASS**, exit 0 |
| .venv-api/Scripts/python.exe -m compileall -q app tests tools | PASS, exit 0 |
| py -m ruff check and format --check on Phase 9 Python paths | PASS; 17 files, exit 0 |
| Entry diff on Supabase/API/domain/application/repositories/legacy bridge | Empty; historical SQL/backend/V1 unchanged |
| git diff --check | PASS |

Integration generates Gen3/4/5 saves, runs the actual worker and strict Python IPC,
tests manual/no-op/restart/watch/backups/error recovery, discovery, a real Windows
exclusive-handle lock/recovery and CLI with Unicode/space paths. Synthetic input
hashes remain identical and temporary profiles/fixtures are removed. No personal
saves, third-party save fixtures or cloud data. The executable .NET test harness
exits nonzero on failures; this is not a Python-only build claim.

Focused tests additionally cover malformed DTOs, timeouts/exceptions, same-mtime
changes, same-content replacement, read races, identity movement/ambiguity,
independent SQLite-session races, CAS, queue state/recovery, failed/tampered backups,
profile locks, auth rejection and log privacy.

Raw final logs: %TEMP%/phase9-final/{unit,integration}.log; focused log:
%TEMP%/phase9-focused.log. Durable JSON retains commands/results/commit/source and
log hashes, no personal rows or credentials. Completed validation commands leave
no background worker. Portable SDK/tagged source development downloads remain
under %TEMP%/pokeapp-phase9-tools; these are not versioned product artifacts.

## Failures found and corrected

1. Existing local SDK directory was incomplete: installed an isolated official SDK
   with published SHA512 verification, without replacing system runtimes.
2. Initial Gen3/4 synthetic builders lacked serialization headers: fixed builders,
   not parser checks. Unsupported Gen6 fixture also needed a recognizable header.
3. Windows path stat and handle fstat have different ctime semantics: compare file
   identity/size/mtime/hash instead; retain complete content verification.
4. CRT open collapsed sharing violation into EACCES: read-only CreateFileW preserves
   FILE_LOCKED, verified using an actual exclusive Windows handle.
5. Ruff absent from API venv: used installed system Ruff 0.15.14, formatted only
   Phase 9 Python and fixed its lint findings.

## API / database / Git

**No new endpoint, no 033, no staging operation, no infrastructure change.**
031=20260928110301 and 032=20260928111840 are historical verified 8L evidence,
not fresh remote observations. **DO NOT REAPPLY**. Schema/parity/Advisor reruns
are not applicable to isolated local code with no SQL change. Custom migration
layout remains supabase/v2/migrations.

- 5474460: parser/contract/DTO/read safety/focused tests; pushed.
- f2158ed: Launcher/sync/auth/queue/backup/CLI, Windows correction and integration
  runner; pushed. Final validation is tied to this exact source.
- Documentation closure: commit containing this report/evidence/closed handoff
  and checkpoint. Its hash comes from Git; ordinary push, no history rewrite.

Before closure main/remote matched f2158ed, 0/0, tracked clean. Protected guide
metadata remains **72,079 bytes**, UTC mtime **2026-09-22 10:13:27**. Not read,
modified, staged, moved, hidden or deleted; the only expected untracked file.

## Next and limits

Next roadmap phase: **10 - React / Cloudflare**, requiring its own instruction.
Not started. Later Launcher delivery includes UI/installer, bundled runtime,
credential persistence if needed, updater/signing and actual distribution license
compliance. PKHeX declares GPL-3.0-or-later; separate processes are not claimed to
settle obligations of a combined product. See linked primary-source dependency notes.

Cloud ingestion, trusted capture ordering/current-state promotion, physical
operations and restore/recovery need future explicit contracts. This local base
supports their later implementation; none is represented as shipped.
