# Phase 22 - verified save export integration

Closed for the verifiable export scope on 2026-10-21. **Phase 22 remains
PARTIAL; physical source replacement and public write activation remain blocked.**
The implementation is committed separately from the earlier native-write and
safety-resolution checkpoints.

## Implementation

The existing native prepare/verify engine now supports a separate export mode.
It records the intent, source hash, immutable original backup, prepared output,
destination and publication phase in the existing SQLite journal. A confirmed
export creates a new deterministic file (`export-{operation_id}.save`) in a
separate directory through an exclusive no-replace publication. The selected
source is opened with strict sharing, checked again before publication and never
written. A partial or uncertain stage is `RECOVERY_REQUIRED`; reconciliation is
read-only and never promotes a partial file or retries a publication silently.

The public result is explicit: `EXPORTED_VERIFIED` has
`applied_to_source=false`. `APPLIED_VERIFIED` remains reserved for the separate
physical replacement path, which is still unavailable to production. Replays
return the existing receipt, and a stale source, occupied destination, unsafe
path, missing closed-emulator confirmation or concurrent operation fails closed.
No purchase, robbery, redemption, reward, coin or competitive state can be
consumed by export.

The IPC and Spanish Launcher surface are capability-gated. The renderer cannot
invent an export intent; the production runtime registers no mutation
capability, so the export control remains disabled until a separately approved
local operation supplies one. The candidate includes the guarded export path,
status rendering and recovery controls without publishing automatic
replacement.

## Validation

The retained affected suite is **58 Python tests PASS**, covering the export
engine plus affected write, Launcher, IPC and sync regressions. The new
journaled validator passed on disposable copies of all eight real game formats:
X, Y, Omega Ruby, Alpha Sapphire, Sun, Moon, Ultra Sun and Ultra Moon. Every
copy ended `EXPORTED_VERIFIED`, every original hash remained unchanged, no
source was applied and no economic effect was generated.

The private packaged candidate passed its package audit and two isolated Electron
runs. The runs used a disposable X copy, no login, no developer runtimes, no
network mutation and a forged-write denial check. Packaged read state reached
`READY`; sandbox, context isolation and disabled production operations were
verified. Formatting, Python compilation, JavaScript syntax and `git diff
--check` pass. No unrelated historical matrices or PostgreSQL run were needed.

## Candidate and delivery

Private candidate **0.22.0-rc.2** is unsigned and unpublished:

- installer: `%LOCALAPPDATA%/PokeApp-releases/0.22.0-rc.2/PokeApp-Launcher-Setup.exe`
- size: `159253386` bytes
- SHA-256: `95b447f7fb787a2c5bb54a3b6110d6c0adbeb15c736b3a6a4f8e7cd41e18969e`

Railway, Cloudflare, Supabase, the public Launcher 0.20.0, the owner
installation, original saves and competitive data were not touched. No
migration or remote write occurred. The protected guide and unrelated files
remain unstaged.

## Remaining blocker and next step

This closes the export integration itself, not automatic application. Windows
pathname replacement still lacks the required compare-and-swap guarantee against
non-cooperative external writers, and arbitrary emulator shutdown/power-loss and
clean-machine installer gates remain uncertified. A future purchase must remain
pending until a separately authorized operation has produced a verified export,
the user has explicitly substituted it, the resulting save has been parsed and
reverified as the intended owner/game state, and a distinct post-apply receipt is
committed before any entitlement is consumed. Export alone must never consume
anything.

**STATUS: PHASE 22 PARTIAL.** No Phase 23.

[Structured evidence](phase22-export-integration-evidence.json)
