# Phase 9 — Parser boundary and Launcher core

Approved scope: user instruction, 2026-09-28. One Windows-first Launcher; UI,
installer/updater production delivery and physical save mutations are later work.
Operational state: [live handoff](work-in-progress/phase9-live-handoff.md).
Evidence: [delivery report](phase9-completion-report.md).

## Boundaries

Real save observations, competitive application state and frozen history are
separate. The parser observes bytes. Neither it nor the local sync core receives
repositories capable of changing Team Locks, identity heads, competition or Hall.
Existing [023 identity](phase8f0-pokemon-identity.md) remains authoritative:
client sequence, file time, hash and HTTP arrival order are NOT CaptureOrder.
No automatic current-state promotion, UUID allocation or identity resolution.

Python core calls a separate read-only .NET process with bounded save bytes on
stdin and a versioned neutral JSON response on stdout. No Pythonnet, PKHeX types,
reflection payload or caller-supplied executable/arguments. Existing legacy bridge
and Streamlit runtime stay unchanged. The worker cannot dispatch legacy mutations.
Pinned PKHeX.Core 24.11.11, matching the existing verified identity evidence API;
package lock and tagged-source provenance. License/distribution findings are in
[PKHeX dependency notes](phase9-pkhex-dependency.md).

Initial support: native main-series Gen 3/4/5 save formats recognized by the pinned
parser. Reject unsupported generations, unknown/ambiguous formats, invalid save
checksums and invalid occupied Pokemon. No ROM-hack promise, repair or fabricated
empty save. Generated fixtures only; no personal saves or third-party fixture data.

## Contracts and safety

- Neutral observation schema v1: game/version/generation, trainer, six party slots,
  full boxes including empty slots, numeric Pokemon data and private typed 023
  evidence. No app-owner claim or authoritative Pokemon ID; location is not identity.
- File fingerprint: SHA256 + byte length. Stat/file identity and modification time
  detect replacement/races; game trainer metadata is separate from file identity.
- Bounded stable snapshot/read, parse immutable bytes, verify live file again.
  Changes reject with SAVE_CHANGED_DURING_READ. No infinite retry or partial state.
- Explicit errors: SAVE_NOT_FOUND, ACCESS_DENIED, FILE_LOCKED, UNSUPPORTED_GAME,
  UNSUPPORTED_VERSION, CORRUPT_SAVE, TRUNCATED_SAVE, PARSER_FAILURE,
  AMBIGUOUS_IDENTITY, SAVE_CHANGED_DURING_READ; configuration/path/backend conflicts
  also fail explicitly. Errors never produce a successful empty observation.
- Local user owns paths: manual file enrollment and configured folder discovery.
  Candidates are returned, never arbitrarily selected. No backend-controlled paths,
  recursive drive scans or remote/local network/device paths. Canonicalize and
  recheck authorized roots/file identity; bound file sizes.

## Launcher services

Core has configuration, discovery, polling/debounce, inspection, sync, session,
backend auth client, durable local journal/operation queue and backup preparation.
Manual and automatic sync use the same pipeline. Polling verifies content even
when filesystem events are missing; duplicate events are coalesced. Parse only
changed content; configurable interval, no busy loop.

SYNCED means an observed snapshot committed to the configured local journal;
NO_CHANGE means that content is already current there. INVALID, UNSUPPORTED,
CONFLICT and ERROR are explicit outcomes. Restart/retry reuse stable local
receipts; reverting to an older hash is an observed transition, never evidence
that it is competitively newer. No cloud-upload success is claimed. A future
server-authorized ingestion/capture contract is required before remote sync.

BackendClient uses existing PIN login, refresh and /v1/me through HTTPS, without
redirects, service keys or a separate account system. Tokens stay in memory for
this base (login again after restart); no plaintext token vault. Locally chosen
backend URL is unrelated to the hosting provider. Config contains no credentials.

Queue records IDs/type/status/actor/time/expected fingerprint/payload/result/error
in local SQLite. Atomic claims; interrupted RUNNING becomes FAILED/recovery-needed,
never silently replayed as a write. No arbitrary executable or physical-write
operation is implemented. Backups persist original bytes + operation/time/hash
metadata and are verified before issuing a prepared-write ticket. The future seam
requires expected-source verification, backup, temporary serialization, validation,
controlled replacement and verification/recovery. Phase 9 refuses actual writes.

Logs contain IDs, status, error codes and parser version, never token/password,
raw save, parser stderr, full snapshot or unnecessary local path data.

## DONE

Working binary inspection and Python integration with generated fixtures; focused
error/race/discovery/sync/restart/auth/queue/backup/history-isolation tests; full
Python regression and .NET build/tests; documented limitations and reproducible
commands; clean tracked Git and push. No schema change is needed: 001–032 and
staging remain untouched; 031/032 must not be reapplied. Do not start Phase 10.
