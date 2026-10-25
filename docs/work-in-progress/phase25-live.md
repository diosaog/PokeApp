# Phase25 — live execution record

2026-10-25. **PHASE25A PARTIAL (updater activation only). Local engineering;
production unchanged; no Launcher release published.** Entry `92d20d2`
(Phase24 DONE LOCAL, 24B gate PASS). Use Git for the exact final HEAD.
[Report](../phase25a-launcher-report.md) · [Evidence](../phase25a-launcher-evidence.json).

## Completed (local)

- Rare Candy / Heart Scale: native `add_item` + read-only inventory mode,
  existing journal/backup/confirm/readback; editable quantity with −/+.
  Adding requires the in-process engineering capability (no League policy yet).
- Signed-manifest updater (Ed25519 pinned key, SHA-512, channels, downgrade,
  deferral during active work, restart reconciliation), disabled by config.
- Launcher shows version/channel, Lime3DS primary status, robbery/item status;
  bounded Lime3DS/Azahar/Citra save discovery.

## Evidence

Native quick items 281/8 titles; entry regression write 225, revive 192,
transfer 168+8; real native+journal 8 titles; updater 7 + quantity 3 Node tests;
Electron headless UI smoke 14/14; 336 Python tests OK.

## Blockers / next action

Updater activation: release key custody, signing step, HTTPS feed,
Authenticode, real two-installer upgrade on Win10/11. League policy for quick
items. Robbery Electron action dialogs. Lime3DS real certification with in-game
readback (randomized Y reserved; never accessed here). Gen7 re-sign may reject
some exact outputs (fails closed).

Next: Phase25B, only when explicitly requested. Private evidence:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase25a/20261025/`. Eight unrelated
untracked files preserved. STOP.
