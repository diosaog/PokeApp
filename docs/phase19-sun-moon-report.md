# Phase 19 — Pokémon Sun / Moon read and import

Closed 2026-10-18. **STATUS: DONE.** Entry
`7617315640936b6efa7abaf6d5397bf04a5e23f4`; application source
`e29cb05c6a0c1965a7253c7b4169d84edbfa5f3d`, committed/pushed before remote writes.
[Evidence](phase19-sun-moon-evidence.json),
[live record](work-in-progress/phase19-sun-moon-live.md).

## Implementation and boundaries

The isolated pinned PKHeX adapter recognizes SAV7SM and exact SN/MN game IDs,
validates the original MemeCrypto signature and its checksum-table hash, native
checksums and Pokémon structure, then exposes 32 boxes and six party positions.
It clones the input before PKHeX clears its in-memory signature buffer. US/UM,
spoofed game IDs, corrupt signatures, truncated saves and incompatible forms fail
closed. No original save is written.

SM species/move/item/ability bounds, independent EC/PID identity evidence, forms
and native form types are preserved. Trainer IDs remain their observed native
components. Gender/egg evidence remains in the neutral local observation; the
existing web card contract does not display it. Unsupported progression, advanced
metadata and competitive identity stay unknown/unmapped. No Alola badge rule,
economy, bag inventory, physical writes or competitive identity allocation was
invented. Original raw bytes remain the retained evidence for unsupported fields.

Launcher → server native parse → existing transactional registration → current
save → web remains one flow. Existing ownership, game/trainer binding, CAS,
receipts, replay and reward hooks remain authoritative. Replaying an old receipt
cannot rewind the current save. Existing flags, Team Locks and closed history are
not synthesized or overwritten by Gen7 observations; no ambiguous identity is
bound to a competitive entity. Public projections continue to exclude IVs/EVs,
ability, nature, raw bytes and identity evidence.

The Spanish catalog extends through Sun/Moon; earlier entries are identical.
Home, own PC/profile and public collections reuse existing readers. Observed forms
and types stay visible, with the existing explicit artwork fallback where no
verified alternate-form asset exists. Team Preview keeps official Team Lock
semantics. Launcher0.19.0 uses the same local-first core and offline cache.

## Evidence

Both games have public contributor gameplay evidence, with private raw copies and
a committed [hash/provenance manifest](../tests/fixtures/phase19-public-saves.json):

- **Sun:** [Twitch Plays Pokémon compilation, Holla!](https://projectpokemon.org/home/files/file/2334-twitch-plays-pokemon-core-series-save-files/), 331 occupied positions.
- **Moon:** [TheWhiteDevil27's Checkpoint backup](https://projectpokemon.org/home/files/file/5342-my-old-saves-for-alpha-sapphire-moon-and-ultra-moon/), 68 occupied positions. The contributor documents later box sorting and removal of illegal Pokémon; it is not presented as unedited.

These are contributor provenance claims, not independent hardware or legality
attestations. Both files pass native integrity checks and contain Alolan forms.
No Gen5 save or constructed upstream collection substitutes for real SM evidence.

Final focused validation: **102 native checks**, **37 Python** (SM8, ORAS5, XY9,
schema15), **41 React**, **4 Edge desktop/mobile journeys**, **2 Worker tests**.
Build, generated API contract, compile, targeted Ruff, affected web formatting,
Launcher JS syntax and diff checks pass. No unrelated historical matrix was rerun.
The existing Launcher files retain their prior formatting style.

Real PostgreSQL proves full-chain/bootstrap parity through046, synthetic imports
for SN/MN/X/Y/OR/AS, real SN/MN imports, concurrency, replay, current-save binding,
rollback, browser RPC denial and no new competitive identities/rewards/locks.
Both families restore all54 public tables exactly. Auth and object transport are
local substitutes; application/native-parser/database reads are real. Browser
tests use presentation mocks and their desktop/mobile screenshots were reviewed.
The packaged Windows parser/core reads both public saves and reaches READY/OFFLINE;
package audit passes. Linux build checks and a smoke in the final .NET8 production
runtime also pass before service activation.

Temporary runtime, Unicode expectation/decoding and transient-status sampling
issues were corrected in the validation setup. Their initial failures remain in
private logs; no assertions were weakened to hide a product failure.

## Delivery, preservation and next step

Forward **046** changes only the service-only registration function; applied once
as **20261018112548**, with all37 previous migration records identical (38 total).
Fixed search_path, SECURITY INVOKER and anon/authenticated denial are verified.

Railway **fa6ef08e-cabf-485f-ba17-936aa5802bab SUCCESS**, source above,262 committed
inputs; image `sha256:69751c82672c3b9eb7a250791c7e1914af297b6cc939d999eca607a02df59b90`.
Cloudflare **c46c2f7b-1621-4102-9b88-aa74ae1ef77c**, version
**5547e5e6-2fec-454b-b580-5d8fe66f1046**,100%, same source.

[Launcher0.19.0](https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download)
is159086505 bytes; SHA-256
`5b3c783a138b53a9f2b0fe172ce5a8b8ab4df8b954db5f58dc4c6a102fb1460e`.
Only its new versioned R2 key was uploaded; earlier installers remain intact.
It remains unsigned; a fresh Windows installation matrix was not repeated.

**12 public checks PASS:** health, authentication denials, SPA/security headers,
exact CORS, deployed build/assets and installer GET/HEAD/checksum. No unexpected
5xx. Positive imports were local only; no hosted owner save or competitive data
was mutated. **59/59 baseline tables identical**, including Auth/Storage; stable
owner credentials, inbox and security catalog identical. Advisor remains
**24 ERROR / 5 WARN / 171 INFO**, no new/removed ERROR/WARN. V1, Shadow and legacy
Streamlit were not modified or used as fixture sources.

All Phase19 disposable databases were dropped; the local cluster is stopped and
no test listener remains. Evidence/fixtures and the audited release are retained
privately under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase19/20261018` and
`%LOCALAPPDATA%/PokeApp-releases/0.19.0`. The protected guide and unrelated files
remain untouched. Documentation closure is a subsequent commit; use Git for its
exact HEAD.

Rollback retains existing data/receipts: stop new SM imports first, then use a
reviewed forward function restoration and compatible prior deployment if needed.
Do not delete accepted saves or edit an applied migration. No rollback was needed.

**Remaining Phase19 blockers: none. NEXT: Antonio acceptance of Sun/Moon and
Launcher0.19.0. STOP; Phase20/USUM and physical writes NOT STARTED.**
