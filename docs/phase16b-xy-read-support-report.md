# Phase 16B - Pokemon X/Y read support

2026-10-13. **STATUS: PHASE 16B DONE. X/Y READ SUPPORT: COMPLETE.**
**LOCAL-FIRST: PRESERVED. CLOUD OBSERVATION: PRIVATE / UNVERIFIED.**
[Live record](work-in-progress/phase16b-xy-read-live.md),
[evidence](phase16b-xy-read-support-evidence.json).

## Entry and parser path

Entry main/origin `e78d0a8fca48c585e712ed981c8dad9372779f65`, fetched 0/0,
clean tracked tree. Phase16A DONE retained. Application source
`86b866847e0c3444f1a526295d3cfa3733024635` committed/pushed before deployment.

The pinned PKHeX.Core **24.11.11** already supplies
[SAV6XY](https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/Saves/SAV6XY.cs)
and its [31-box layout](https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/Saves/SAV6.cs).
No dependency upgrade or architecture change. The existing isolated bytes-in/JSON-out
worker now permits X/Y. It checks native size, content recognition, exact X/Y
trainer version, block checksums, party count and occupied Pokemon checksums/format.
Unsupported families, mismatched versions, truncation and corruption fail closed.
Encrypted cartridge containers are unsupported; use a decrypted native save.
Extensionless `main` is selectable/discoverable; its name is only a file-selection
hint and never determines the game. Unsupported/corrupt UI states are explicit.

## DTO, party and PC

The neutral observation adds generation 6, X/Y only, with six party positions and
31 sequential boxes of 30 positions. Empty slots and first/last box coordinates
survive round-trip. Existing trainer, species, Unicode nickname, level, held item,
moves/PP, nature, ability, IV/EV and other fields remain private neutral values.
Unlocalized names/types retain the existing honest ID fallback.

PK6's independent encryption constant is preserved in a separate read-only identity
type. Local comparison includes it and keeps same-PID duplicates/changes ambiguous.
The competitive 023 identity contract remains unchanged; conversion of X/Y into
that contract explicitly rejects. X/Y progress is **unknown**, never zero or inferred
from party strength. No medal/Champion mapping is claimed by this read-only packet.

## Local-first, cloud and privacy

The existing local journal, background worker, private outbox, scoped identifiers,
receipt-first delivery and retry rules are reused. Additive reader/3 envelope
support preserves old Gen3/4/5 receipts and avoids a migration or second ingestion
path. The API must receive the expanded DTO, so only Railway needs deployment.
No SQL, Cloudflare, public scouting or competitive mutation contract changed.

Observations remain **PRIVATE / UNVERIFIED / NON-COMPETITIVE**. No reward, official
progression, points, coins, Team Lock, current save head, physical ownership claim
or frozen history is created. No source-write API exists; serialization calls in
the checks project only generate disposable synthetic fixtures from blank objects.

## Tests and performance

One affected Python closure: **101 PASS**, covering parser/files, Launcher/cache,
private API/runtime, progress and existing competitive identity regressions.
Native closure: **111 PASS assertions**, including real X/Y binary parsing and the
existing Gen3/4/5 checks. Locked dependency unchanged; build has zero warnings/errors.
Compile, targeted Ruff, Python/JS formatting, JS syntax and diff checks pass.

Actual native IPC checks both X and Y, repeated deterministic reads, exact source
hash preservation, cache restart without network, immutable private serialization,
GET/PUT/lost-reply/GET recovery, corrupt-input non-enqueue, stable-file race rejection
and physical-write denial. A full 930-slot DTO fits the existing 2 MiB limit.
Malformed identity input returns sanitized 422 before repository access.

Headless X renderer uses the real Python/native path and a local fake HTTP server:
all six party positions, all 31 boxes, last-slot navigation, offline browsing,
proven in-flight three-second network delay, restart and unsupported rejection pass.
One PUT/two GETs, zero renderer network requests/page errors. No physical desktop
control. Early harness-only fixes concerned the discovery-provider label, disabled
write method signature, multi-Pokemon locator and Unicode canonical receipt digest;
the final affected checks pass. No production save used.

Small synthetic samples, not installer or large-save benchmarks:

| Measurement | Result |
|---|---:|
| X native process + DTO + stable read, 5 samples | median 154.5 ms |
| Y, same method, 5 samples | median 152.7 ms |
| X local useful UI | 2.507 s |
| Cached process restart | 667 ms |
| Box navigation offline / during 3-second network wait | about 6 ms / 6 ms |

No micro-optimization was needed. No historical phase matrix, unrelated full suite,
React/web suite, PostgreSQL, migration replay or cutover proof was repeated.

## Delivery, preservation and cleanup

Fresh pre-deployment baseline: 35 migration records through 043 (once as
`20261013112907`), 60 scoped tables including the empty private inbox; existing
Railway `0930ba0d-695f-47dc-89fa-0060d8498add` was SUCCESS.
New API deployment **b917132f-5624-40c4-afbc-bc043b007828 SUCCESS** uses 246
committed inputs; image
`sha256:80e776a42f8a4712894c9a320852291f786ca43fbf5756480b87b97eb6de10e8`.
Existing project/service retained; no Cloudflare deployment or migration.

Hosted proof passes health, existing owner login/me and season read. Real native
X/Y DTOs reach scope authorization and return 403 for an independently verified
absent season; anonymous sends return 401. No owner save read/uploaded, positive
remote mutation, inbox insertion or unexpected 5xx. Positive receipt/replay proof
is local only; the unchanged 043 database gates were not rerun.

After-deployment capture at 2026-10-13T12:08:31Z preserves all non-Auth records
across the 60 scoped tables, including Storage and the empty inbox. Owner stable
identity/credentials, Shadow, security catalog and all 35 migration rows equal the
fresh pre-deployment baseline. Only Auth-table hashes changed during validation
login/session activity. V1 was not accessed or changed by this packet.

Useful private evidence (23 files, hash-verified copy) is retained at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase16b/20261013/closure-86b8668/`.
No packet process remains and no PostgreSQL environment was created. Installed
dependencies and compiled local reader remain available for the Launcher.

**Small operator cleanup remains**, as explicitly permitted by the 16B instruction:
automatic execution review rejected deletion with `blocked by policy`. No bypass
or alternative deletion was attempted. The sole exact directory to remove is
`C:\Users\Antonio\AppData\Local\Temp\pokeapp-phase16b-20261013`.
Read-only verification at 2026-10-13T12:10:53Z confirms that it exists, has no root
or child links, and has zero matching processes. It contains only this packet's
synthetic fixtures, temporary profiles, deployment export and retained evidence
copies. This operator action does not block the implementation DONE status under
the owner's packet rule. Protected guide and unrelated untracked files are untouched.
Final documentation HEAD is obtained from Git, not embedded self-referentially.

## Limits and next packet

Only decrypted X/Y joins Gen3/4/5. ORAS, Sun/Moon, USUM, competitive X/Y progress/
identity promotion, installer/updater and physical save writes are not implemented.
**PHYSICAL SAVE WRITES: NOT STARTED.** Recommended next packet:
**LAUNCHER PACKAGING / WINDOWS INSTALLER / WEB DOWNLOAD**. Do not start it here.
