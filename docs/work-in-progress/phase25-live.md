# Phase25 — live execution record

2026-10-27 (art pass 2 + release). **Published.** Scene backdrops for every
area (`web/scripts/build-scenes.mjs`, `web/src/design/scenes.css`), reviewed
in real pages at 1920/1440/1366/1104/390/360; CLS 0; full suite 92/10/11 with
only inherited failures. Web Cloudflare `a7e33476` (`3910926`); public Launcher
0.25.0 in R2 `windows/0.25.0/…` (sha256 `f02eccd0…3fa`), 0.20.0 kept. API and
database unchanged. Rollback: `npx wrangler rollback 4a8fffed-a912-47d8-aa7e-dfaea7b7bce3`.
[Report](../artpass2-report.md). Release gates still open (unchanged): 054–061,
hosted verifier, Docker worker, two-player Lime3DS, Windows 10, Authenticode,
update channel, physical certification.

2026-10-26 (Artistic Evolution). **DONE LOCAL, not deployed.** Entry 2ffdb29.
"Liga Nocturna" over Arena: stadium Home, rival scouting, Pokédex dialogs,
themed Shop/League/Hall/PC (box arrows untouched), Rubik everywhere, sounds
and preferences, CLS fix. [Report](../artistic-evolution-report.md).
Owner review: `npm run preview:design` in `web/` (http://127.0.0.1:4173, any
name and PIN, synthetic data) and the before/after gallery
`%LOCALAPPDATA%\PokeApp-migration-evidence\artistic\index.html`.
**Next (needs owner approval)**: deploy the web with the 27C procedure
(build with the Railway API URL, `npm run deploy`, verify bytes); Launcher
release items unchanged from 27C.

2026-10-26 (27C). **27C DONE LOCAL — resumed validation and closure.**
Entry c3835b6, main ahead4/behind0; existing edits preserved. Application source
remains c3835b6; validation/build-preparation commit228569d. The documentation
commit carrying this entry supplies final HEAD (read Git). Normal push includes
the four interrupted commits; eight unrelated untracked files and release
worktree retained. No Phase28 started.

**Production already updated by prior session, freshly verified without deploy:**
Railway501a399 / deployment22d96f80-9d99-498f-b3f6-d90b3ec39da9, health200,
88 routes plus optional unlimited inventory. Cloudflare4a8fffed-a912-47d8-aa7e-dfaea7b7bce3
at100%, source98de687, assets equal retained build;12 read-only checks PASS.
Public authenticated inventory acceptance remains PARTIAL (no owner PIN/use).
Public Launcher0.20.0 preserved. No remote SQL;054–061 NOT APPLIED per retained
checkpoint, not a fresh remote migration-history assertion.

**Fresh local proof:** SQL28 checks PASS,64 prior tables unchanged,7 private new
tables, upgrade053→061/bootstrap schema+grants+ownership parity. Historical055
replay rolls back058's identity function: validator corrected, no migration edited.
Private rc.2 packaged24 checks PASS incl. all5 panels/race/logout/offline/session
separation/IPC. Eight packaged files match c3835b6. Worker startup/restricted PG8
PASS; manifest/integrity6 PASS with destroyed ephemeral test key, no release feed.
Targeted lint/format/compile/diff PASS. Disposable PG dropped/stopped; new test
listeners gone. Retain earlier Node17/Electron28/dev18/offline2/React161/browser33
and27A16+8 evidence, no historical matrices repeated.

**Release boundary:** rc.2 installer159254332 bytes,
SHA25627760cc8cedb8609c2cd8a482a35dd88d5230cf2ded6ce2aed67856b30891df3,
unsigned/private/updaterOFF; no install over owner and no rebuild/publication.
Worker Docker context repaired; digest/capability/default-off guards prepared.
Docker absent, image PENDING. Public501a399 is not a061-capable worker base.
Hosted verifier/least-privilege Storage, actual release key/feed, fresh rc.2 install,
Win10, Authenticode, two-real-player test, revive/power-loss and Gen7/foreign-OT
gates stay PENDING. Public physical writes DISABLED. No saves/economy/V1/Shadow writes.

**NEXT EXACT ACTION:** return to owner with [27C report](../phase27c-report.md)
and [evidence](../phase27c-evidence.json); await a specifically authorized next
packet. Do not auto-deploy migrations/worker or publish stable Launcher.
Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase27c/`.
The earlier entries below are historical, superseded where27C records a result.

2026-10-26 (27B). **27B DONE LOCAL — visual redesign** (owner reassigned the 27B
slot from hosted acceptance to the redesign). Resumed after the first instance
hit its quota with everything uncommitted; its work was audited and kept.
PokeApp Arena tokens + layer over the 15 routes, login and registration; 11
distinct area signals; 3 × 3 Home menu; trainer-card stats; ∞ holographic items;
Launcher on the same palette. Private preview `npm run preview:design` (from
`web/`): 127.0.0.1:4173/4174, synthetic fixture, production CSP, Host/Origin
guards. Private Launcher `0.24.0-preview.2` built, audited, driven over CDP 11/11
(not distributed). Gates: tsc, Vitest 159/159, gallery 4/4 (`gallery-v6`),
Launcher 15/15 + 28/28; inherited E2E failures proven on a clean `7c00486`
worktree, Kaspersky script interference identified. Nothing deployed.
[27B report](../phase27b-report.md), [design system](../design-system.md).
**Next (needs owner authorization)**: deploy the redesigned web; release items
unchanged (two-player Lime3DS, hosted verifier, Docker worker, Windows 10,
Authenticode, update channel, physical certification, production 054–061).
Left running at hand-off: the design preview (`node preview/run.mjs`,
127.0.0.1:4173/4174, synthetic data) for the owner to browse; stopping it loses
nothing. Restart any time with `npm run preview:design` from `web/`.

2026-10-26 (27A). **27A DONE LOCAL**: PokeApp decides a valid robbery from the
accepted saves without the victim (local 061); each save then has its own
physical obligation; the victim's removal is a mandatory sync in the Launcher;
the robber receives the victim's canonical bytes; re-planning on current bytes,
verified absence, restart and incidents covered. Disposable E2E 16/16 (PG +
FastAPI + two Launchers + verifier + parity). Not applied to production, worker
not deployed (image build needs Docker), public writes OFF.
[27A report](../phase27a-report.md), [backend](../robbery-backend.md).
**Next: 27B** — owner-approved restricted hosted acceptance (procedure steps
1–18), real two-player robbery on Lime3DS, worker image, packaged Launcher.

2026-10-26 (daily backups). Owner decision implemented on the 26D engine: one
ordinary restore point per save and local date (state before the day's first
write), kept 30 days, listed in the Launcher with date and game and exportable;
transactional backups still made before every write, older ones retired only
when provably redundant; pending/failed/restored/robbery/pre-policy backups and
unrecognized files never touched. Tests 8/8, UI smoke 26/26, regression 138 OK.
[Rules](../save-engine-recovery-procedure.md#daily-retention-owner-decision-2026-10-26).

2026-10-26 (26D). **26D DONE LOCAL**: no `.displaced`/`.lock` left beside saves
after verified writes; identity-bound, journaled retirement; Windows 11 PASS;
power-loss and Windows 10 PENDING. [26D report](../phase26d-save-engine-report.md),
[recovery procedure](../save-engine-recovery-procedure.md).
**Next: 27A** — server-authoritative robberies without victim cooperation,
mandatory sync, verifier build, local migrations (054–060 pending production).

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
