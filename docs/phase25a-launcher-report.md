# Phase25A — Launcher integration, updater and quick items

2026-10-25. **PHASE25A PARTIAL (updater activation only). Production UNCHANGED;
no release published; physical writes in production DISABLED.**
Entry `92d20d2` (Phase24 DONE LOCAL; 24B gate PASS), main/origin 0/0, no other
active agent, eight unrelated untracked files preserved.
[Evidence](phase25a-launcher-evidence.json) · [Live handoff](work-in-progress/phase25-live.md).

## Quick items — Rare Candy and Heart Scale

- **Native** `NativeItems` (PKHeX.Core 24.11.11) behind the existing writer
  protocol: kind `add_item`, items 50/93 only, X/Y/OR/AS/SN/MN/US/UM. It binds
  exact source hash, game, trainer and the current count; the title's real pouch
  maximum and free slots are enforced (`INVENTORY_LIMIT`, `INVENTORY_FULL`). The
  output is re-derived and re-parsed: every other inventory entry, every box and
  party Pokémon, party count and money must be identical, and changed bytes may
  only be the bag block, its checksum and the Gen7 signature. A read-only
  `--inventory-items` mode reports count, maximum and addable amount.
- **Launcher**: the same journal, verified backup, explicit `write_confirm`,
  readback and restart reconciliation as every other write. The operation id is
  derived from the intent, so a lost reply or re-offer can never add twice.
  Runtime commands `quick_items_refresh` (read-only, also in production) and
  `quick_item_offer` (engineering capability only).
- **Economy decision (missing, not invented)**: no approved League rule grants
  these items, so adding is disabled in every production build ("Operación
  bloqueada … falta una regla aprobada de la Liga"); counts remain visible.
- **UI**: icon, name, count/maximum, editable field with −/+ and Añadir, one
  shared state for keyboard and buttons; empty, negative, decimal, non-numeric
  and above-limit values cannot be confirmed. States: ready, waiting for the
  emulator to close, preparing/applying/verifying, applied (only after readback),
  recoverable error, recovery required, blocked.

## Updater

`updater.cjs` (Node built-ins only, no new dependency): the authority is an
**Ed25519-signed manifest under a public key pinned in the build**. The
installer's SHA-512 and size are bound by that signature, so a hash served by the
same origin is never trusted alone. HTTPS only, separate stable/private channels
(existing distinct app ids), downgrade and incompatible-version rejection,
`.partial` download deleted on interruption or mismatch, re-hash immediately
before launch, and `pending.json` reconciliation after restart (incomplete install
keeps the verified file; success cleans up). Installation is user-initiated and
**deferred** while the runtime reports a write in progress or pending, recovery,
an active robbery or a sync in transition; after confirmation no new local
command is accepted. NSIS keeps AppData (`deleteAppDataOnUninstall: false`).

**Blocked by external dependencies — activation disabled** (`pokeappUpdate`:
no public key, no feed): release key generation and offline custody, a signing
step in the release pipeline, an HTTPS feed, an Authenticode certificate for
Windows trust, and a real two-installer upgrade on Windows 10/11. No release
was published and no secret is in the Launcher.

## Integration and Lime3DS

The Launcher now shows its installed version/channel, the primary emulator
(Lime3DS, pending certification), robbery/item-use status, quick items and update
state. Bounded discovery of `sdmc` saves for Lime3DS, Azahar and Citra (eight
title ids, fixed depth, no drive scan); a discovered path is selectable only if it
was in the latest result. Running lime3ds/azahar/citra processes block writes.

## Validation

- Native: **281 quick-item checks PASS across 8 titles** (limits, exact maximum,
  zero/negative, stale count, replay on applied save, stale source, wrong trainer/
  game, tampered output, unapproved item, full pouch on all 8). Shared entry
  point regression: write 225, revive 192, transfer 168 + 8 cross-title PASS.
  Build: 0 warnings/errors (local SDK 9.0.318).
- Real native + journal on disposable copies, **8 titles**: verified backup,
  explicit confirm, native readback, lost reply/re-offer/restart without
  duplication; open Lime3DS process blocked; incompatible saves and invalid
  quantities refused; runtime production build read-only, engineering build
  prepare → confirm → re-read.
- Updater 7 + quantity 3 Node tests PASS; **Electron 44 headless UI smoke on the
  real page: 14/14 PASS** (editable field, ±, limits, confirmation, disabled
  state, update banner, version, Lime3DS discovery).
- Python: 336 focused tests OK; Ruff no new findings; compile/diff PASS.

**Native limitation found:** PKHeX's Gen7 re-signing is content-dependent; for
some exact outputs (1 of 20 tried on Moon) the signature does not verify. The
writer fails closed (`CORRUPT_SAVE`, no output, no change) and the UI asks for
another quantity. Revive/transfer outputs share this property.

| Gate | Result |
| --- | --- |
| PHASE24B GATE | PASS |
| LAUNCHER INTEGRATION | DONE LOCAL |
| AUTO-UPDATER | PARTIAL — circuit done locally, activation blocked by release key/feed/Authenticode |
| UPDATE SIGNATURE/INTEGRITY | PASS (local Ed25519 + SHA-512; Authenticode pending) |
| RARE CANDY / HEART SCALE | DONE LOCAL (engineering capability; League policy pending) |
| EDITABLE QUANTITY INPUT | PASS |
| BACKUP/RECOVERY | PASS |
| LIME3DS INTEGRATION | DONE LOCAL |
| LIME3DS REAL CERTIFICATION | PENDING |
| PHYSICAL WRITES IN PRODUCTION | DISABLED |
| PHASE25A | PARTIAL (updater activation only) |

## Next unit (25B)

Release-key ceremony and signing step in `tools/build_launcher_windows.ps1`,
HTTPS feed, Authenticode, and a real two-private-installer upgrade/rollback on
Windows 10 and 11; League decision on who may add quick items and how many;
Electron action dialogs for robbery; then Lime3DS certification with in-game
readback (owner's randomized Y reserved for that step).
