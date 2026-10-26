# Phase25 — live execution record

2026-10-26 (26C). **26C PARTIAL (deploy-dependent only)** under the owner's 26B
exception: infinite Rare Candy/Heart Scale in every trainer inventory (virtual, no
migration), Launcher «PokeApp» tab hosting the real deployed web in an isolated
view, private 0.23.0-rc.2 built and audited. 26B stays PARTIAL/deferred.
**Next queued: 26D (save-engine hardening: `.displaced`/`.lock`, recovery,
cleanup), then 27A (authoritative robberies, verifier).** Not started here.
[26C report](../phase26c-launcher-web-report.md).

2026-10-26 (26B). **26A CLOSED: Pokémon Y inventory certified in isolated Lime3DS.
26B PARTIAL:** team robbery done locally (native 500/500, PG E2E 12/12, local 060);
server-authoritative completion without the victim and mandatory sync NOT done —
exact unit in [robbery-rules.md](../robbery-rules.md). 26C not started (gate FAIL).
[26B report](../phase26b-robbery-report.md).

2026-10-26 (correction). **26A in-game check #1 FAILED: the usual Lime3DS opened
the untouched original.** Isolated instance proven with the game; desktop shortcut
«PRUEBA PokeApp - Pokemon Y (copia aislada)» created; owner retry pending. Launcher:
public 0.20.0 in use; private 0.23.0-rc.1 only built (isolated preview .cmd on
desktop). No product code change.

2026-10-26 (continuation). **PHASE26A PARTIAL — owner in-game step pending.**
Owner authorized copies of the Pokémon Y save. On isolated copies: real read,
backup/restore, real lime3ds.exe blocking, Rare Candy 0→10 and Heart Scale 0→7
with readback, idempotency and recovery all PASS; original unchanged. Waiting for
the owner to open the isolated copy in Lime3DS, check the bag, save and reopen;
then re-read the copy to confirm persistence. Robbery rules in
[robbery-rules.md](../robbery-rules.md): team allowed (pending), cross-title
prohibited, no victim consent (API veto refused; full contract pending).
Release blocker: handoff leaves `.displaced`/`.lock` beside the save.

2026-10-26. **PHASE26A BLOCKED at the owner gate** (follows 25B). Lime3DS found
(portable `Desktop\Lime3DS\Lime3DS\lime3ds.exe`, `%APPDATA%\Lime3DS`); one Pokémon Y
save located by discovery, NOT opened/read/copied. Private pre-release
`0.23.0-rc.1` built with the official script and audited (unsigned, updates off,
not distributed). [26A report](../phase26a-lime3ds-acceptance-report.md). Next: the
owner confirms the save path and scope; then follow
[the procedure](../lime3ds-certification-procedure.md).

2026-10-26. **PHASE25B DONE LOCAL** on top of 25A. Robbery action UI, signed-update
build/signing integration, real installed update on Windows 11 (7/7), quick-item
free/unlimited policy recorded with a prepared public switch that stays OFF, Gen7
signature classified as a known safe blocker, Lime3DS acceptance procedure ready.
[25B report](../phase25b-launcher-report.md) · [25B evidence](../phase25b-launcher-evidence.json).
Pre-release CONDITIONAL on: Authenticode, release key/feed, Windows 10, 054–059 +
verifier deployment, Lime3DS certification (owner approval of the copy path) and
three robbery decisions. Incident during the first update attempt disclosed in the
report (owner's private test profile touched, no data effect).

## Phase25A record

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
