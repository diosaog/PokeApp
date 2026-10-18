# Phase 18 — Omega Ruby / Alpha Sapphire read and import

2026-10-18. **STATUS: DONE for ORAS read/import, including the public gameplay
fixture follow-up below.** At the initial delivery, only synthetic evidence was
available and the status was PARTIAL. The owner subsequently required a search of
legitimate public fixtures and blocked future unverified ingestion deployments.
That search found contributor gameplay saves for both OR and AS. A Black/White
save is not Gen6/7 evidence; nothing synthetic is represented as gameplay proof.
[Evidence](phase18-oras-read-evidence.json),
[live checkpoint](work-in-progress/phase18-oras-live.md).

## Behavior and boundaries

Pinned PKHeX.Core 24.11.11 accepts native decrypted Omega Ruby (`OR`) and Alpha
Sapphire (`AS`) bytes, with game/size/checksum validation and malformed form/move
rejection. Trainer, party, 31 boxes, Box 8 deaths, forms, level, moves, items and
permitted private metadata use the existing neutral model. ORAS types come from
the pinned form-specific personal table. X/Y and older serialization/digest
compatibility are preserved; filenames and client DTOs are not trusted authority.

Existing raw-save registration remains the only cloud path. Original bytes are
immutable; same-file replay, concurrent registration, receipt recovery, CAS and
game/trainer ownership rejection are reused. A different game cannot silently
replace the current registered trainer/save. Form/type facts remain attached to
the accepted current save. Closed snapshots, Team Locks and flags are not created
or rewritten. Gen6 competitive identity/progress remain UNKNOWN, as in X/Y:
no guessed permanent identities, badge/champion evidence or new reward effects.
Local observation evidence is retained without promoting it to competitive truth.

Home, own/public trainer collections, PC and details display the game and ORAS
form/type/item/move data through existing components. Private IVs, EVs, nature,
ability and identity metadata remain excluded from rivals. Existing supported
flag projection remains authoritative; no flags are inferred for unsupported
Gen6 entity identities. Team Preview keeps its official Team Lock semantics.
Alternate form sprites are not present in the existing assets: their numeric form
is preserved and the unavailable-image treatment avoids showing an incorrect base
form. Base-form animation behavior is unchanged. The current model does not
import the save's bag inventory. Full desktop Spanish labels are still deferred.

## Evidence actually run

- **68 native assertions** using explicitly synthetic OR/AS/X/Y bytes: trainer,
  party, boxes, forms/types, deterministic observation, bad checksums/truncation,
  incompatible formats/game IDs and invalid form rejection.
- **51 focused Python tests:** ORAS 5, X/Y 9, trusted ingestion 13, frontend reads
  24. The pinned pre-change X/Y digest still matches. No full historical suite.
- **Real local PostgreSQL 17.11:** chain/bootstrap parity through 045, OR/AS/X/Y
  imports through the real parser/service/RPC/read repository; concurrency/replay,
  stale CAS, no old-replay rewind, cross-owner/game denial, transactional rollback,
  privacy and browser RPC denial. No Gen6 reward/entity/lock effect; exact 54-table
  restoration and both disposable databases dropped. External Auth/object storage
  are substitutes; this is not a real hosted authentication/import proof.
- **33 focused React tests; two desktop/mobile browser journeys** with fixture
  API interception. Screenshots reviewed for own/private and rival/public forms,
  latest moves/items/types and 31-box navigation. No positive hosted mutations.
- TypeScript/Vite, formatting, compile, targeted critical Ruff, diff and Worker
  dry-run pass. Launcher audit plus packaged parser/core stdio/offline smoke pass
  for all four games. The first smoke sampled an in-flight network attempt; final
  bounded polling proved OFFLINE while local reads remained READY, no code change.

The first synthetic native run found byte-array types serializing as base64;
native integer arrays fixed it before the final green checks. A local harness
import-order issue was corrected before PostgreSQL execution. These are recorded
as development failures, not hidden passes. At that initial checkpoint no authentic
OR/AS files, fresh clean Windows install or hosted positive save registration were
tested. The follow-up below supersedes only the missing ORAS fixture evidence.

## Public fixture follow-up — 2026-10-18

Entry `6a219a4176048102588aae25172c71fdcd98bffc`, tracked tree clean and main/origin
0/0 after fetch. The product source remains `e783344`; no application, migration,
installer, Railway or Cloudflare change was needed or published in this follow-up.
The earlier deployment predates this follow-up and had synthetic evidence only;
the new tests do not retroactively change that delivery sequence.

No tracked ORAS/Sun/Moon binary existed in the repository's authorized test/parser
scope. The pinned PKHeX tree was searched too. Public files were then downloaded
directly from their contributor pages, without an account or access bypass:

- [Minay's Omega Ruby gameplay save](https://projectpokemon.org/home/forums/topic/58103-sharing-pokemon-omega-ruby-save-completed/):
  two party slots, 415 occupied party/box slots, 31 boxes, forms 0 and 3.
- [Melampus's Alpha Sapphire gameplay saves](https://projectpokemon.org/home/files/file/5447-alpha-sapphire-sectionslegendary-save-files/):
  starting point with no Pokemon, and current save with six party slots and 30
  occupied slots. Their trainer identity is consistent across both captures.

All three are 483328-byte native ORAS saves. Exact SHA-256, contributor, page and
attachment IDs are pinned in
[fixture manifest](../tests/fixtures/phase18-public-saves.json). They are shared as
gameplay saves by their authors, not fixtures constructed by PokeApp. Hardware
origin, absence of external edits and individual Pokemon legality are not
independently attested. This is read/import compatibility evidence, not a legality
certification. Binary files and full observations stay outside Git; no ROMs or
owner saves were accessed or downloaded.

**PASS:** packaged native parser and packaged core offline reads for all three;
real local PostgreSQL registration/replay/concurrency, complete 415-slot public
projection, privacy, wrong-owner/game denial, rollback and no competitive effects.
AS start -> current preserves the authoritative pointer; replaying the older file
does not rewind it. All source hashes remain unchanged. All 54 public test tables
were restored, disposable DBs dropped and local PG stopped. Prior chain/bootstrap,
React/browser and other regression evidence was retained without rerunning it.
External Auth and Storage remain local substitutes; no positive hosted import.

Only the fixture runner changed: `--public-fixtures` verifies the pinned hashes
and uses one fresh bootstrap DB. Its local object substitute now serializes file
publication, matching atomic object visibility while DB calls remain concurrent.
Initial follow-up attempts exposed a wrong local port, a partial local-file race,
an unsupported fixture filename suffix and a test-source encoding error. Those
harness/setup issues were fixed without relaxing product validation. The final
public-fixture gate passed; compile, critical Ruff and diff checks pass.

Sun/Moon: pinned upstream includes
[SM Project 802.main](https://github.com/kwsch/PKHeX/blob/b60c6e5f1427263260061d3f8c5540b924063572/Tests/PKHeX.Core.Tests/TestData/SM%20Project%20802.main),
a useful test resource, **not independently established gameplay provenance for
both Sun and Moon**. The Project Pokemon base-save download list contains Ultra
Moon, which is not interchangeable with Sun/Moon. Real Sun and real Moon gameplay
validation and dependent ingestion deployment gates remain **BLOCKED** until
appropriate evidence and implementation are available. Ordinary development is
not blocked by fixture absence. Gen7 implementation has not started.

The latest rule is durable: search authorized local fixtures and legitimate public
resources first; continue safe development and automated testing when real saves
are missing; block only their validation/dependent release gates. Never substitute
Gen5 or synthetic files for Gen6/7 gameplay proof, or deploy unverified ingestion.
No new deployment or remote write occurred in this follow-up.

## Delivery and preservation

Entry `08f00acd3a06a579e899c3e19454ea5be896c222`. Application source
**`e7833440f0c77579a82a9f00a030ab6cdd27619c`** pushed before every remote write.
Migration **045_oras_save_registration**, once as **20261018105158**, only expands
two game allowlists in the existing invoker RPC. No new table, privilege, progress
policy or data rewrite. All 36 older migration records remain identical; 37 now.
Remote function body matches committed source with fixed search_path and browser
denials. The generated bootstrap matches the complete migration chain locally.

Railway **2253b885-dc35-43b4-8b93-773fd628656f SUCCESS**, committed 256-file export,
image `sha256:73681da8e8128d35fb5c05fed85585cbb38f682d61c84fee5dc4bb52749fac98`.
Cloudflare **411aeb3d-a68a-4d8c-8327-22430a97ba95**, version
**e48fd707-900b-4597-a181-ca3eca114caa**, 100%, same source. API health and auth
denial passed before web publication. Twelve final read-only HTTP checks pass:
HTTPS/SPA/security headers, build-config, exact CORS, three matching JS/CSS assets
and installer GET/HEAD; no unexpected 5xx.

[Launcher 0.18.0](https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download)
is published only at the new R2 key
`windows/0.18.0/PokeApp-Launcher-Setup.exe`. Download size **159086220 bytes**,
SHA-256 **63c3c1373f6cdb32871f8101350d88e9b89da190cf774a7407960f40c0819fbb**.
Installer remains unsigned; its local audit and packaged offline checks pass.
Existing release keys were not replaced or deleted.

Immediate preapply/final comparison: **59/59 scoped tables identical**. Relative
to initial entry: **56/59 identical**, with owner Auth activity only in users,
sessions and refresh tokens before the final preapply capture. One Auth user and
stable credentials/identity/admin facts remain unchanged. Results, economy, Team
Locks, private inbox, Storage metadata and security catalog are preserved. Advisor
**24 ERROR / 5 WARN / 171 INFO**, zero new/removed ERROR/WARN. No production test
save, owner competitive mutation, V1/Shadow business write or physical save write.

Rollback: use the previous API/web deployments recorded in the live checkpoint;
if necessary restore the 044 function definition, retaining accepted ORAS saves
and receipts. Do not delete data to revert admission. No rollback was needed.
Dedicated PG port 55468 is stopped, both disposable databases removed and no
packaged process remains. The stopped synthetic cluster directory is retained;
private evidence and release paths are in the handoff.

Documentation closure is a later commit carrying these documents; exact final
HEAD comes from Git. Explicit staging only; protected/unrelated files untouched.
**Next:** owner acceptance of the published ORAS feature when personal saves are
available. Public-fixture read/import acceptance is complete; owner-hosted use is
not claimed. No Phase 19 or Sun/Moon implementation started.
