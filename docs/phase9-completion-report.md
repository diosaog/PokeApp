# Phase 9 delivery evidence — in progress

Started 2026-09-28 at `30d670a`, main/remote 0/0, 511-test closed Phase 8 baseline.
Current execution state: [live handoff](work-in-progress/phase9-live-handoff.md).
Approved [contract](phase9-parser-launcher.md). No completion claimed yet.

Entry audit: `app/domain/saves.py`, `pokemon.py`, `pokemon_identity.py` and 023
provide reusable data/evidence rules. `ParsedSave` requires server-owned save and
trainer IDs, so the local parser needs a separate unbound observation DTO.
`conex_pkhex.py` / `Bridge/PKHeXBridge` are legacy/reference: process interop is
reusable as a pattern, but mutation dispatch, reflection and live-file caches are
not a safe new read boundary. Local ignored `desktop` is an Electron Streamlit
wrapper, not an existing sync engine. Existing Auth endpoints can be reused.
No cloud ingestion API provides trusted capture attestation; no reason to add
schema or claim local observations are current competitive state in this phase.

## Parser block — 2026-09-28

Portable .NET SDK 8.0.425 downloaded from official release metadata with SHA512
verification. Existing SDK directories were incomplete. New isolated worker build
passes with zero warnings/errors; NuGet exact version and lock hashes retained.
24 executable .NET checks pass on generated Gen3/4/5 saves (party, boxes, identity,
empty slots, checksum corruption, truncation and unsupported Gen6).
12 focused Python tests pass via the standard isolated runner. Python -> real
worker -> strict DTO -> live-file verification also passed for all three fixtures.
Initial synthetic Gen3/4 builders lacked serialization headers; fixed builders,
not parser checks. A real Windows stat/fstat ctime discrepancy initially rejected
stable files; removed ctime from the portable comparison while preserving inode,
device, size, nanosecond mtime and a second complete content hash.

## Launcher block — 2026-09-28

32 focused Python tests pass; `tools/validate_phase9_launcher.py --dotnet <SDK>`
passes the 24 .NET checks and real byte IPC/DTO, local sync/restart/watch/backups,
CLI and Windows sharing-violation recovery. An initial Windows check returned
ACCESS_DENIED because Python CRT open discarded native error 32; the bounded
reader now preserves CreateFileW errors and uses read-only shared handles.
This fixes error classification without hiding locked files or disabling hashes.

Implemented local config/discovery, content-verified polling/debounce, SQLite
observation receipts with CAS, atomic operation claims/recovery, prepared/verified
backups and explicit physical-write refusal. Single-profile OS lease is held by
the CLI. Auth uses existing PIN/refresh/me HTTP contracts, rejects redirects and
disabled/mismatched accounts, keeps tokens only in memory and sanitizes errors.
No backend path request exists. No server capture attestation is fabricated.
