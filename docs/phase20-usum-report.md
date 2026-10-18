# Phase 20 — Ultra Sun / Ultra Moon read and import

Closed 2026-10-18. **STATUS: PHASE20 DONE.**
[Evidence](phase20-usum-evidence.json),
[live record](work-in-progress/phase20-usum-live.md),
[fixture provenance](../tests/fixtures/phase20-public-saves.json).

Entry `d58222401f76e603e1ab3764c9846acd0728898d`, main/origin aligned, clean
tracked tree. Application `99b302e9823ad8ef123fdc37d0b524fefc9ebf07` was
committed and pushed before every remote write. Documentation closure follows
separately; use Git for its exact HEAD.

## Native read and import

The pinned PKHeX.Core 24.11.11 adapter now accepts native SAV7USUM with US/UM game
IDs, 445440 bytes and 32 boxes. It validates the original MemeCrypto signature at
0x6C100 against the 0x150-byte checksum table, then native block/Pokemon checksums.
SM retains its distinct 441856-byte layout, 0x6BB00 signature and 0x140-byte table.
PKHeX receives a clone so its in-memory signature clearing cannot modify source
bytes. Truncation, wrong game/layout, invalid signature/checksums, forms and native
data bounds fail closed. Native USUM ceilings are 807 species, 728 moves, 959 items
and 233 abilities; SM retains 802/719/920/232. These are format checks, not an
independent Pokemon legality attestation.

Native PersonalTable.USUM supplies form/type facts, including Necrozma Dusk Mane
and Dawn Wings, Dusk Lycanroc and Own Tempo Rockruff. Species through Zeraora and
new move/item/ability names use the pinned Spanish resources. Existing catalog
prefixes and real SN/MN serialized observations remain exactly unchanged.
The parser wire version is retained to preserve previous digests/receipts.

The established raw bytes -> server parser -> atomic registration -> current save
path is reused. Forward 047 only extends existing service-only registration
allowlists. No tables, rewards, identity allocation, extra ingestion authority or
historical rewrite. Trainer/game binding, CAS, concurrent registration, replay and
old-receipt no-rewind remain enforced. Gen6/7 competitive identity, progression,
badges and Champion status remain **UNKNOWN**; public flags are never invented
from unsupported identity evidence. Box8 is observed without changing frozen
competitive deaths, Team Locks or history.

## Real gameplay evidence and focused validation

Ultra Sun uses [Totter's public Checkpoint gameplay collection](https://projectpokemon.org/home/files/file/5724-ultra-sun-all-legendary-ultra-beast-shiny-wormhole-pok%C3%A9mon/),
selected at the Blacephalon encounter. The contributor declares Pokedex/shiny
charm, nature and item edits and removal of other Pokemon: this sample has one
occupied position. Ultra Moon uses [TheWhiteDevil27's personal backup](https://projectpokemon.org/home/files/file/5342-my-old-saves-for-alpha-sapphire-moon-and-ultra-moon/),
595 occupied positions, with declared removal of illegal Pokemon and box sorting.
Both pass native integrity and actual local import. Exact SHA256/archive hashes
are in the manifest. Neither is represented as unmodified or independently
hardware/legality verified. Binary copies stay private outside Git; no ROMs.

- **145 native assertions**, bounded to X/Y,ORAS,SM,USUM; USUM-specific forms,
  limits, invalid inputs, original-byte immutability and exact game identity.
- **40 focused Python tests**: USUM 3, SM 8, ORAS 5, XY 9, schema 15. HTTP authentication
  denials and server-observation ingestion covered for both US/UM.
- **42 React**, **2 Worker**, **4 Edge journeys**: SM desktop/mobile regression
  and USUM desktop/mobile. Browser data is synthetic/mock API, not real-save
  hosted acceptance. Own details retain private stats; public details omit them;
  box32, Spanish names/types/moves/items and explicit missing-form-art fallback pass.
- Real disposable PostgreSQL: full migration/bootstrap schema/grant/ownership
  parity, eight synthetic native games and both public gameplay saves; concurrent
  import, replay, stale CAS, wrong-owner/game denial, rollback, current save and
  public/private reads. Exact 54-table restoration per successful family, zero
  fabricated entities/rewards/coins/Team Locks. Databases dropped, cluster stopped.
  External Auth and object transport are local substitutes.
- API schema regenerated without a contract diff; TypeScript/Vite, compile,
  relevant Ruff/format/diff and Wrangler dry-run pass. Linux final-image SM/USUM
  parser smoke passes before activation. No unrelated historical/full matrices.

Initial PG failure was a harness expectation of a different stale-CAS error;
the actual SQL denial was correct and cleanup completed. Two browser attempts
used incorrect species/nickname and box accessible-name locators. Corrected final
gates pass without weakening assertions or changing product behavior.

## Launcher, delivery and preservation

Launcher **0.20.0** package audit and packaged parser/core offline checks pass for
all eight games, including the two real USUM saves. Existing local caches and
trusted sync are reused. Installer 159087398 bytes, SHA256
`1f581c2dcf479a1676ed3ccb65420007b8b12000be7d32b0235282e3095200e0`.
[Download Launcher](https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download).
It remains unsigned. No disposable clean Windows environment was available;
packaged execution is proven, a fresh clean-machine installation is not claimed.

047 applied once as **20261018163946**, 39 migration records; all 38 prior records
unchanged. Railway **d869e493-1792-4bfe-a0fc-cc372ef6abf2 SUCCESS**, 263 committed
inputs, image `sha256:8ded66f5dfd775a0c0f6b3c02c3f6fd42a587c20ff3bb5e5ef96346d1ea6a32b`.
Cloudflare **f83b8161-0bb4-4d09-8111-6b1185990182**, version
**bfedf17f-df71-4d4e-9d42-bb7b85903ac1**, 100%, same application source.
Only new R2 key `windows/0.20.0/PokeApp-Launcher-Setup.exe` written; 0.19.0 was
downloaded and hash-verified unchanged.

Public **13-check proof PASS**: health, SPA/security headers, exact live assets and
API build-config, auth denials, exact CORS and installer GET/HEAD with matching
bytes/hash. No unexpected 5xx or positive owner import. An initial transport
timeout occurred before HTTP on this machine's default Cloudflare DNS addresses
188.114.96.5/97.5. The successful probe used 188.114.96.1, independently returned
by Google's public DNS, retaining the original hostname/SNI and normal TLS
verification. No system DNS, application retry or infrastructure change. This
default-route connectivity issue is documented, not claimed fixed.

All **59/59 scoped public/Auth/Storage table records**, stable owner credentials
and identity, inbox and security catalog are identical before/after. Advisor
**24 ERROR / 5 WARN / 171 INFO**, zero new/removed ERROR/WARN; only observed_at excluded.
No hosted owner-season mutations, fixtures, V1/Shadow/Streamlit changes or physical
save writes. Private evidence and release are retained outside Git. No owned test
process remains. Protected guide and unrelated untracked files untouched.

Rollback is the prior compatible application/installer and 046 function through a
new forward migration if necessary; accepted source bytes and receipts must be
retained. No rollback performed or needed by the observed product gates.

**Remaining implementation/release blockers: none.** Limitations above remain
explicit: contributor provenance, local Auth/object substitutes, unsigned package,
no clean Windows install and this machine's default Cloudflare route timeout.
**STOP. Antonio acceptance next. Phase 21 NOT STARTED.**
