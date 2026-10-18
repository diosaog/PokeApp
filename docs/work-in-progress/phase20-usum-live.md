# Phase 20 — Ultra Sun / Ultra Moon

Entry 2026-10-18: main/origin `d58222401f76e603e1ab3764c9846acd0728898d`,
0/0, clean tracked tree. Owner accepted 19. V2 has 38 migration records through
046=`20261018112548`; Railway `fa6ef08e-cabf-485f-ba17-936aa5802bab` SUCCESS,
Cloudflare `c46c2f7b-1621-4102-9b88-aa74ae1ef77c`, application `e29cb05`.

**STATUS: PHASE20 DONE.** The implementation checkpoint below is retained;
the final delivery record supersedes its pending steps.

Native SAV7USUM uses exact US/UM layout, original-byte signature at 0x6C100 and
0x150-byte checksum-table binding, distinct from SM. 32 boxes; USUM native
species/forms/types/moves/items/abilities; Spanish catalog and game labels.
Existing SM bounds and old serialized observations remain intact. Competitive
identity/progress stay UNKNOWN. No physical writes or new economy semantics.
Forward 047 extends only service-only registration allowlists; no new tables.

Public gameplay contributor evidence for US (Totter, one occupied slot) and UM
(TheWhiteDevil27, 595) passes native parse and local atomic import. Their declared
edits and exact provenance/hashes are in
`tests/fixtures/phase20-public-saves.json`; binaries remain private, outside Git.
No independent hardware/legality verification or hosted positive import claimed.

Validation: 145 bounded native assertions across all eight games; Python USUM3,
SM8, ORAS5, XY9, schema15; React42; Worker2; Edge SM2 and USUM2. Desktop/mobile
screenshots reviewed. TypeScript/build, schema export (unchanged), compile,
targeted Ruff, formatting and Wrangler dry-run pass. Two USUM browser attempts
had only incorrect test locators (nickname/species and box accessible name);
corrected final two cases pass. First PG attempt correctly rejected stale CAS;
the harness expected the wrong error text, then the corrected run passed.

Disposable PostgreSQL: full chain/bootstrap parity through047, all eight native
games and two real public saves; concurrency/replay/no rewind, stale CAS,
wrong-owner/game denial, rollback, browser privilege denial, no competitive
identity/reward/Team Lock effects. Each run restored 54 tables; disposable DBs
dropped and cluster stopped. Auth/object transport are local substitutes.
Launcher0.20.0 package audit PASS; packaged core/parser offline PASS for eight
games (real US/UM, synthetic earlier games). Installer remains unsigned; no clean
Windows install claim. Source bytes unchanged.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase20/20261018`.
Installer: `%LOCALAPPDATA%/PokeApp-releases/0.20.0`, 159087398 bytes,
SHA256 `1f581c2dcf479a1676ed3ccb65420007b8b12000be7d32b0235282e3095200e0`.
Fresh prewrite capture has 59 scoped tables, unchanged migration head and one
private inbox observation. Remote Phase20 writes at this checkpoint: ZERO.

Next: commit/push, apply committed047 exactly once, Railway build including
Linux production-runtime SM/USUM smoke, new versioned R2 installer, Cloudflare,
public read-only smoke and preservation comparison, final documentation closure.
Do not begin Phase 21. Protected/unrelated files remain untouched.

## Final delivery — 2026-10-18

Application `99b302e9823ad8ef123fdc37d0b524fefc9ebf07` committed/pushed before
all remote writes. 047 applied once as `20261018163946`, 39 migration records;
all 38 prior records unchanged. Railway `d869e493-1792-4bfe-a0fc-cc372ef6abf2`
SUCCESS,263 committed inputs,image
`sha256:8ded66f5dfd775a0c0f6b3c02c3f6fd42a587c20ff3bb5e5ef96346d1ea6a32b`.
Linux production-runtime SM/USUM parser smoke PASS before activation.
Cloudflare `f83b8161-0bb4-4d09-8111-6b1185990182`, version
`bfedf17f-df71-4d4e-9d42-bb7b85903ac1`, 100%, same application source.
Only new R2 key `windows/0.20.0/PokeApp-Launcher-Setup.exe` written.
Previous 0.19.0 downloaded/hash-verified unchanged.

Public 13-check proof PASS: health,SPA/assets/build-config,CSP/nosniff,CORS,
authentication denials and installer GET/HEAD with exact size/hash. No 5xx.
The initial default-resolver route to 188.114.96.5/97.5 timed out before HTTP.
The successful probe used 188.114.96.1, independently returned by Google's public
DNS, with the original hostname/SNI and normal TLS verification. No system DNS,
retry policy, application or infrastructure change. Default local-route issue
remains an explicitly recorded observation, not claimed fixed.

All 59 scoped table records (public/Auth/Storage), stable owner credentials/identity,
private inbox and security catalog are identical. Advisor 24 ERROR / 5 WARN / 171 INFO;
zero new/removed ERROR/WARN, only observed_at excluded. No hosted business writes,
owner fixture, V1/Shadow/Streamlit changes or physical save writes.
Prior real SN/MN observations also compare exactly unchanged.
Local disposable DBs absent, cluster stopped, no owned test process remains.
Private evidence and verified release intentionally retained outside Git.

[Report](../phase20-usum-report.md), [evidence](../phase20-usum-evidence.json).
Documentation closure is a separate subsequent commit; obtain exact HEAD from Git.
Explicit staging only; protected/unrelated files untouched. **Next: Antonio
acceptance. STOP. Phase 21 NOT STARTED.**
