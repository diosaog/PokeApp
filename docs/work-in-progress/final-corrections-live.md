# Final corrections — live execution record

## Compact trainer cards / Box7 count - 2026-11-02

**TESTED; PUBLICATION IN PROGRESS.** Owner clarification supersedes the previous
card presentation: show **Puntos / Monedas / Muertos**, remove the new explanatory
paragraphs, and count the configured dead box (empty complete box is zero).

- Cards/profile/GENERAL now display the same current-box count. Personal-only
  participants receive a public numeric count from their own server-parsed,
  hash/owner/game-bound complete30-slot box; this never credits coins, creates
  League identity, changes Team Locks or manufactures sporting evidence.
- Owner explicitly confirmed the initial Box7 totals. Existing075 audited RPC
  confirmed Anto0 and Aaron1 against their exact accepted sources/revision, after
  rollback rehearsal on the verified123-table backup. Replay returns the same
  resolution. Official reads now show Anto0points/8coins and Aaron-0.1points/4coins.
  Iker's visible count3 and ByVisan02/Samu0 require no manual League linkage.
- 78 Python /47 React checks PASS; malformed/partial/foreign boxes remain unknown,
  linked sources take precedence, personal counts do not change points/claims.
  No new migration or native/save-write changes. Launcher0.26.11 loads the updated
  hosted web directly; another binary rebuild is unnecessary.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/trainer-078/`.

## Trainer evidence / Launcher 0.26.11 - 2026-11-02

**PUBLISHED / VERIFIED. NO PUBLICATION BLOCKERS.** Branch `codex/trainer-evidence-077`, base
`c4cff18`. Task077 does not require a database migration: production remains076.

- Read-only production checks: Anto has two authoritative League badges, exactly
  two4-coin claims and8coins; Aaron one badge/claim and4coins. No deductions or
  unpaid eligible rewards were found. Their historical baselines are unconfirmed:
  current dead-box occupancy0/1 is not an all-time death total.
- Iker has two personal-save badges and three Pokémon in Box7, but no League
  upload, pointer or identity revision. His own Launcher must upload the original
  save into the active League; personal payloads cannot fabricate that evidence.
  ByVisan02/Samu also have personal-only saves, with no observed badges.
- Cards/profiles now use075 historical deaths and exact pending prerequisites,
  expose personal progress scope, and retain ledger balances/NET totals. A bounded,
  authenticated API read adds linkage status without exposing save identifiers.
  GENERAL alone removes the Victories/Penalties columns; day views stay unchanged.
- 84 focused Python checks PASS;20 React checks/TypeScript PASS. Isolated001-076
  SQL proves high-water claims, valid linking, deductions, concurrency, configured
  Box7/Box4, audited3deaths=-0.3NET, repeated/moved Pokémon and frozen snapshots.
  No scoring, reward, identity, native-write or Launcher-sync logic was changed.
- Launcher0.26.11 was explicitly requested by the owner. Its version-only rebuild
  retains40 identical Python modules and474 identical native method bodies; the
  prior native/transaction matrices remain valid. Packaged startup/recovery9/9,
  package audit and compatibility with the shipped02610 updater PASS.
- Fresh backup SHA256 `d53a6bbb451c5fe2ba0ab455f52e654665fd63251690105aae2abb0bfa8a5ea2`:
  123 tables, catalog and migration history restored exactly; copy retained/stopped.
- API/Launcher source **3eea9f5**, web source **7eca61c**. Railway
  **46969e2a-78f3-4dee-b648-ebf4541ed09f SUCCESS**,307 Python files match the committed
  bundle; final-image8-game parse/24 training gates PASS; health200 and anonymous
  League401. Image `sha256:a32a54399d02fa3d1ef82035dd4f559797f56e5124d3d0204043a57f91d081ab`.
- Cloudflare **975c2dde-5dbe-44a1-a780-37c751179471 active100%**;18 public files match
  the tested build. Installer159462974 bytes; SHA256
  `606a3651acf150c09ea4cb6d75b386ed20f6ff3fdfaa6481d9b768ded83ca608`.
  Full public download SHA512 matches the signed manifest; existing stable Ed25519
  key verifies the exact served02611 feed. Installer published before feed, then
  public download/web card updated. Only own ephemeral readback key/files removed.
  Existing release keys remain intact. No real save or purchase was used for tests.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/trainer-077/`.
No production data repair has been performed. Historical baseline confirmation
and Iker's original League upload remain factual prerequisites, not release gates.
All five participants' pointers, claims, balances and death evidence were compared
before/after and remain unchanged. Evidence: `docs/evidence/trainer-evidence-077.json`.

## Final championship tiebreak popup / 076 - 2026-11-02

**PUBLISHED / VERIFIED. NO REMAINING PUBLICATION BLOCKERS.**
Branch `codex/championship-tiebreak-076`, based on `4244ca8` (not the older owner
reference01164f5). Baseline production: DB075, API9fb35778, webe9a8967b,
Launcher0.26.10. No Launcher rebuild is required.

- Final overall NET title only. Admin popup has exactly two methods: actual
  total Locke deaths (initial default) or recorded extra1v1 results. Explicit
  confirmation/reason required. Ordinary trainers only see read-only status.
- Historical counts come exclusively from final075 frozen actual-death evidence
  and matching frozen inputs, including normal/comodin/wipe deaths once. No
  adjusted units/current box proxy. Equal NET/deaths persist an audited pending
  choice and require battle results; the champion remains null until resolved.
- Reused championship resolution table with additive decision/outcome fields,
  preserving old methods/final titles. One final winner per fingerprint; actor,
  original contenders, sources, method, evidence and result retained. Existing
  auth/CAS/hash/receipt/season locks provide idempotency and concurrency safety.
- Multiway results are entered manually, never auto-scheduled/ranked. Evidence
  must establish one undefeated winner covering all eligible contenders through
  recorded victories; incomplete, cyclic/disconnected or foreign results fail.
  No normal points, victories, death snapshots, coins or rewards are changed.
- **78 backend /54 React checks PASS**, web build PASS; six SQL rollback groups,
  explicit/admin permissions, actual-vs-adjusted/comodin/wipe evidence, source
  changes, multiway/loser-cycle cases, repeated confirmation/frozen results and
  two concurrent confirmations PASS. Existing075 scoring/legacy guards PASS.
- Fresh backup **123 tables** restored exactly; **101 existing application tables**
  keep byte-identical rows and browser privileges unchanged. Upgraded copy equals
  fresh001-076. Fixture initialization handles an already active season only
  inside the isolated transaction, whose rollback/fingerprints are verified.
  Migration LF SHA256 `b153e3a44c34929ec9910cce6862e1c0a1626ccecd48dbcde29d615af6f112fb`.

Machine-readable evidence: `docs/evidence/championship-tiebreak-076.json`;
private evidence `%LOCALAPPDATA%/PokeApp-migration-evidence/championship-076/`.
The previously undefined title rule is now implemented. Historical releases below
remain dated records. Published DB -> API -> web from committed source **`45ef745`**.
Production migration **076 / `20261102180220`** applied once; RPC execute remains
backend-only and the unique final-winner guard is present.
Railway **`4f1ad76c-2c57-459f-9d70-84fbae3d2416` SUCCESS**, **307** deployed Python
files match committed source; final image/runtime gates and health PASS;
126 OpenAPI paths include the new two-method authenticated admin contract,
anonymous review returns401. Image digest
`sha256:8688a2de3f4c60498d84699438e42042f12d9704adcffddbaed8ab1089079f55`.
Cloudflare **`e4243599-45e4-49e1-9f78-435145a69517` active100%**; all **18** public
asset hashes match the tested build. Launcher **0.26.10** installer/feed unchanged,
no rebuild or native change. Temporary readback registration/generated keys removed;
fixture clusters stopped/retained. No real save, purchase or title was used for tests.


## Launcher 0.26.10 and requested inventory correction - 2026-11-02

**PUBLISHED / VERIFIED. NO RELEASE BLOCKERS.** Branch
`codex/launcher-02610-inventory`, build source `9faaf3b` (only Launcher version
metadata changed). The League075 API/database changes remain deployed unchanged.

- Owner requested removal of the cap shown on Anto's ChampionsLocke profile.
  It was **Chapa Plateada**, not Gold: a pending paid record from discarded
  **Prueba2**, dated 2026-10-29, carried by the existing virtual-item rule.
  Scoped preimage/ledger checks found its original -6 debit and no save/training
  reservation or applied redemption. Used the existing audited/idempotent
  `admin_purchase_resolve` cancellation once, preserving the record/history;
  one +6 compensation in Prueba2 only (2 ->8), ChampionsLocke stays **0**.
  No pending Silver/Gold remains for the owner. No inventory rules changed.
  Private operation/preimage/receipt are under `launcher-02610/` evidence.
- Launcher **0.26.10**: package audit PASS, actual packaged startup/recovery
  **9/9 PASS** isolated. All **40** shipped Python modules match the commit and
  0.26.9. All **474** native method bodies/IL/signatures/runtime attributes match;
  changes are only Git build provenance in ProductVersion/InformationalVersion
  and derived build IDs. PKHeX/CoreCLR/hostfxr identical. Existing native,
  transactional and NSIS matrices are valid and reused, without repeating them.
- Old actual shipped 0.26.9 updater/key accepts the new canonical signed manifest,
  SHA512/size and numeric 0.26.9 ->0.26.10 ordering. Final installer
  **159464261 bytes**, SHA256
  `ff9a35fef144859150a4994176522a51b2703dca7deb8393212595a9f7038514`.
  Uploaded immutable installer first, complete public HTTPS SHA512 readback PASS,
  then Ed25519 stable feed; final public feed equals the signed build exactly.
- Web download card/worker then published **0.26.10**:
  **`e9a8967b-7ca6-4b0a-b710-78c4b96e18c7` active100%**, **18** public hashes PASS.
  API **9fb35778** and DB **075** unchanged; no new migration or native changes.
  Temporary readback registration/generated keys removed, other keys preserved.

Machine-readable closure: `docs/evidence/launcher-release-02610.json`.
Build/provenance: `%LOCALAPPDATA%/PokeApp-releases/0.26.10-league-net/`;
private acceptance and publication: `%LOCALAPPDATA%/PokeApp-migration-evidence/launcher-02610/`.
No real save modified, no new real purchase executed. The cap cancellation was
an explicitly owner-authorized data correction, not deployment testing.


## Final League NET / death history - 2026-11-02

**PUBLISHED / VERIFIED. NO PUBLICATION BLOCKERS.**
Branch `codex/league-net-deaths-075`, based on `0327291`. Production verified
before release: Supabase074, Railway657dcd97, Cloudflare6664ab72, Launcher0.26.9;
no closed snapshots and no active season. Only DB/API/web were published.

- New prospective `league_net_v1`: every matchday global round robin, +1 per
  normal win; no position points. Decimal-exact accumulated NET subtracts only
  the latest cumulative death/sanction deductions. Day contribution uses deltas.
  Divisions/movements and existing reward purchase/voucher pipeline retained.
- Every day pays the configured common coins, first Blindar / last Robar once.
  Daily ranking is wins then actual frozen segment deaths. Consequential ties
  require explicit played 1v1 results, time and evidence; no extra win points.
- Four private structures retain event identity/cycles, audited baseline and
  reconciliation, and immutable per-player opening snapshots. Actual history
  is separate from wipe adjustments: penalty tenths = actual deaths + applicable
  wipe deaths. Ordinary revivals never erase/count another death. Box settings,
  accepted source hashes, chain gaps, counter revisions and phase boundaries
  are checked; unknown evidence blocks opening instead of becoming zero.
- Existing closed scoring contracts/corrections stay frozen. Mixed legacy/new
  continuation requires an explicit rule migration, never automatic rewriting.
  Exact final NET ties deliberately require an owner rule; old BO3/death fallback
  cannot decide a new title. Initial history confirmation is an audited admin
  action in Entrenadores, never inferred from current dead-box occupancy alone.
- PASS: **181 Python checks**, **68 React checks** and web build; actual SQL
  five players/four days, two divisions, J1=1/J2=6/GENERAL=7, normal/wipe
  revivals, source replay, missing data, corrections, failure atomicity, 1v1
  evidence, old history and simultaneous closes. 12-2.0 loses to 11-0.5.
- Fresh production backup **119 tables** restored exactly; 075 applies once as
  non-superuser, **97 existing application tables** keep byte-identical rows,
  compatible reads/privileges unchanged and upgraded catalog equals 001-075.
  Migration SHA256 `ea43eb035a1ea1e082ca342db2988960b59ce1c5056bf3f56ae35d9ba432d167`.
  Machine-readable evidence: `docs/evidence/league-net-075.json`; detailed
  private evidence at `%LOCALAPPDATA%/PokeApp-migration-evidence/league-075/`.

No real save or purchase was used. Launcher/native writer, migration074 and
hosting/update distribution are unchanged. Published in safe order DB -> API -> web from committed source **`440c1d3`**
(implementation `f57f6dd`; canonical LF migration bytes pinned by `440c1d3`).
The exact committed LF bytes were re-rehearsed before release; no source check
was waived. Production migration **075 / `20261102171453`** applied once.
Railway **`9fb35778-200a-444d-b754-d496dc58f350` SUCCESS**; all **307** deployed
Python files match the committed bundle; final Debian image gates PASS,
health/API contract present, anonymous history access returns 401.
Cloudflare **`552a8512-e79e-4187-8600-923ff5806fe9` active100%**; all **18** public
HTML/config/JS/CSS hashes match the tested build. Launcher0.26.9 installer and
Ed25519 feed unchanged. Four new history tables force RLS/no browser access
and remain empty in production: no historical backfill or real test actions.
Temporary readback SSH registration/generated keys removed; other keys preserved.
Fixture clusters stopped. Release evidence is under `production-release/`.
The undefined equal-final-NET title rule is an intentional conditional finish
block, not a publication blocker; the owner must define it before that case.


## PokeApp 0.26.9 - published and verified, 2026-11-01

**RELEASE CLOSED / NO REMAINING RELEASE BLOCKERS.** This entry supersedes the
historical publication holds below. Product source: `6408a41`; release closure
continues on `codex/virtual-training-native-gate`.

- Refreshed production backup at **18:15:22 UTC**, SHA256 `99659df3...c1df9`:
  restored 118 tables with exact row fingerprints/catalog; 074 rehearsal and
  preflight PASS. Production migration **074_virtual_training** applied once,
  version `20261101181732`; forced RLS / browser isolation verified.
- API Railway **`657dcd97-677d-45b6-9a7f-d38aff8ff2ed` SUCCESS**. All 338 bundled
  inputs match committed source; 306 deployed Python files match byte-for-byte.
  Final Debian/Python3.14.3 image passed its mandatory native runtime gates,
  including all **24 training cases**. Image digest
  `sha256:2328fc80cedfb0ff4237c0f05986d236842827af013f6bfc1f34b6bf7afca43a`.
  Public health PASS, 124 OpenAPI paths and training contract present; anonymous
  training GET returns 401. Existing verifier service unchanged.
- Safe order completed: DB -> API -> preparatory web `663b5a46` (download card
  still 0.26.8) -> immutable installer -> full public readback -> signed feed ->
  final web **`6664ab72-a87c-4cd8-9d01-db89069b135b`**, card **0.26.9**.
  Final public HTML/config/JS/CSS: **18 exact hashes PASS**, correct API target.
- Launcher **0.26.9** final tested installer: **159464245 bytes**, SHA256
  `7739047e0e795848a727739327605ef0b95d8e6f0b1a4f999ceddea42a285c2e`.
  Complete public HTTPS download matched signed SHA512 before feed activation.
  Published feed equals signed build, Ed25519 verifies with the shipped key,
  updater accepts current version 0.26.8; download routes return the new size.
  Existing private unsigned-Authenticode distribution policy retained.
- Reused the valid native, transactional, packaged, Linux and NSIS evidence
  recorded below; no completed acceptance matrix was manually repeated.
  Public web readback used the established pinned Railway SSH transport;
  temporary registration and generated keys removed, other keys preserved.
  No real save writes or purchases. No additional development or migration.

Machine-readable closure: `docs/evidence/virtual-training-release-0269.json`.
Private detailed release evidence: `release-6408a41/` under the evidence root
below, including source/image/API/DB/web/feed proofs, backup and rehearsal.


## Virtual training: randomized-save policy correction — 2026-11-01

**NATIVE / TRANSACTIONAL ACCEPTANCE PASS; NOT PUBLISHED.** Continue on
`codex/virtual-training-native-gate`. The owner's explicit clarification
supersedes the earlier official-legality requirement and the historical
diagnostic-only stop below. Production remains unchanged.

PokeApp uses randomized ROMs and privately modified saves. Official encounter,
learnset, ability, provenance or event legality is not authority for training.
`NativeTraining` no longer invokes `LegalityAnalysis`, including its `Parsed`
result: that is a legality-engine result, not native save parsing. All native
format/integrity parsing, target identity, requested prior values, bounded
Nature/IV input, exact PKM/save byte differences, serialization, CRC/signature,
independent backups and readback remain mandatory. Unsupported species/forms
and malformed Nature/PKM structures fail closed. No Pokémon is regenerated,
legalized, replaced or normalized; unrelated fields/PID/EC/HT are preserved.

**Demonstrated causes and limits:**

- **UM:** the old DLL rejects a structurally intact modified UM fixture solely
  because Gold makes an official HT/IV finding invalid. New native applies and
  independently verifies the exact actual-IV change, keeping its existing HT
  flags/PID/EC. Both old possible `TRAINING_LEGALITY_UNSUPPORTED` paths were
  inappropriate authority under the clarified policy and have been removed.
  The exact historical call's sub-branch remains uncaptured; this is a proven
  policy correction, not a claim to have reproduced its suppressed exception.
- **AS:** native verification previously re-ran the same official analysis;
  Python additionally required exact equality of its warning lists. A real
  before/after regression proves the old writer rejects the historical receipt
  after successful native byte verification when those informational lists
  change, while the corrected writer accepts identical `9cb09e…` bytes. Only
  `legality_warnings_before/after` are excluded from training proof comparison;
  their wire bounds and every authoritative field/type remain checked. Other
  mutations are unchanged; no journal migration. The exact original AS inner
  error was never captured, so its unique historical cause is not asserted.

**Focused and complete evidence, isolated only:**

- Old-reject/new-accept randomized/event regression, AS+UM first, then all8.
  Native matrix once: **496 transformations +40 policy regressions PASS**,
  including exact unrelated bytes, PID/EC, HP/status, noops, stale data,
  corruption, unsupported structures, forged valid-checksum outputs and native
  signatures. `policy-native/full-native-matrix/` (144896 byte/assertion checks).
- AS historical receipt: **15 checks PASS**. Old writer fails/new writer passes;
  hashes/contract/IV/Nature/PID/EC/PKM hashes/integrity-flag tampering still fails.
  `as-legacy-proof-compat/run-1/`. Native bridge/protocol **16 tests PASS** and
  portable API import PASS.
- Actual service/native/atomic SQL: AS+UM **6/6**, then **24/24** across8 games,
  purchase consumption/replay/corruption refusal/identity preserved. Foreign-OT
  two-training/ordinary-sync proof PASS, preserving original UUID, flags and
  transfer provenance. `policy-service-*.json`, `policy-foreign.json`.
  SQL074 SHA `2398c53b…c606b` unchanged. Disposable PG55674 stopped/retained,
  restart metadata `policy-074-pg-stopped.json` (never initdb).
- Rebuilt **0.26.9** at `%LOCALAPPDATA%/PokeApp-releases/0.26.9-randomized-policy/`:
  audit and signed manifest PASS; final packaged bytecode + native NTFS full
  **81 checks PASS** (all8, independent backups, readback, answer loss, crash
  recovery and exactly-once spending); exact historical AS/UM source copies,
  three fresh handoffs each, **18 checks PASS**. Isolated packaged core/startup
  recovery **9 checks PASS** with built frontend fixture at the expected origin.
  `policy-packaged-{full,focused,startup}/`.
- Real Linux execution: **24 cases /120 native calls PASS**, independent whole
  PKM oracle, actual Nature/IV, unchanged PID/EC/HT, source, CRC and signatures.
  `policy-linux/run-2/report.json`; self-contained .NET8.0.29, pinned PKHeX24.11.11,
  WSL Ubuntu26.04 x86_64/Python3.14.4. This is **not** a final Debian Docker image
  execution. Source/build provenance and logs retained; no packages installed.

All evidence remains under
`%LOCALAPPDATA%/PokeApp-migration-evidence/virtual-training/20261101/`.
No owner save, real purchase, production data, hosting setting or update feed
was changed. No SQL migration added/edited. No unrelated UI or billing work.

**Release decision:** the corrected randomized-save policy passes the native,
Windows packaged and transactional gates; no current failure was observed.
Publication remains held by the owner's instruction. Before any later release:
run the final production-image build gates, refresh backup/rehearsal/preflight
as required, use the committed-source bundle and obtain deployment instruction.
Keep the historical AS attribution limit explicit; do not call it proven flaky
or claim a reproduced process-lifecycle fault. Prior NSIS8/8 evidence is retained;
installer/update logic was unchanged and not broadly rerun in this correction.

## Historical pre-clarification: virtual Mints and Bottle Caps — 2026-11-01

**BLOCKED / NOT PUBLISHED. Implementation is committed and pushed on
`codex/virtual-training-native-gate` (`9597c62`). Final native acceptance blocks
release; do not merge or activate this feature yet.**
The four preceding fixes (`662c3ea`, `f1d147c`) remain deployed and were not
repeated. Production still uses API `c70f9bd9`, web `754550f9`, Supabase 073 and
Launcher 0.26.8. No production migration, purchase or save has been changed for
this feature.

- Mint changes actual Nature; Silver changes one actual IV to 31; Gold changes
  all six actual IVs. Identical custom mechanics for X/Y/OR/AS/SN/MN/US/UM,
  without bag delivery, Hyper Training flags or a level-100 restriction.
- Native wizard binds the final confirmation to purchase/entity/save hash and
  chosen change. The API derives the slot, exact PKM hash, current values and
  identity revision from trusted stored bytes. Existing owned paid purchases,
  including discarded-season caps, remain redeemable against an authorized
  current bound save; their purchase season and original payment stay intact.
- Independent verified backups, the existing NTFS write journal and a durable
  training binding hold synchronization until reconciliation. Atomic SQL
  completion registers the verified save, preserves entity UUID/provenance and
  consumes one purchase. Uncertain writes cannot release the purchase.
- Migration 074 is frozen at SHA-256
  `2398c53bfcbded60a90da4ffe6e91c39b83d403ff5b69d2f94e8ab5079dc606b`.
  Fresh 001–074, restored-backup rehearsal, concurrent reservation guards and
  foreign-OT two-IV-change/ordinary-sync proof pass. Backend 77 tests plus two
  strict native-protocol tests pass. UI: 39 Node, 20 native-wizard, 53 React
  tests and TypeScript pass; screenshots reviewed.
- Native matrix: 496 isolated changes across eight games, party and boxes,
  with unrelated-field, checksum, signature and tamper assertions pass. The
  pinned PKHeX RSA short-result padding defect is narrowly corrected without
  disabling signature verification. Packaged startup/recovery passes with the
  built frontend served at its expected origin in an isolated test profile.
- **Unresolved:** an earlier package completed all eight-game journal cases,
  but the final immutable candidate fails intermittently: AS/Gold enters
  `RECOVERY_REQUIRED` at local readback; real service/SQL reaches 23/24 then
  UM/Gold refuses `TRAINING_LEGALITY_UNSUPPORTED` during completion preparation.
  Identical retained requests subsequently verify, so retries are not accepted
  as a fix. Original failures and raw inputs remain retained. Failure-only
  Release diagnostics are being exercised through actual service and NTFS
  workloads; legality rules have not been relaxed. Do not publish this candidate.
- Subsequent diagnostics did **not** establish a fix: modified-diagnostic CLI
  service 24/24 and journal 81 checks completed; the **unchanged original final
  CLI** also completed service 24/24 and journal 81 checks under startup
  EventPipe, with zero managed exceptions captured. A bounded replay of the
  exact failed UM request completed 512 processes without rejection (509 traces;
  three PID filenames were reused). These are marked diagnostic-only and do
  not supersede the original failures. No functional legality correction has
  been identified. Current source adds opt-in failure diagnostics which are
  absent from the original `0.26.9-final` DLL `739ab360…`; rebuild after fixing.
- Exact-payload disposable NSIS install/update **0.26.8 → 0.26.9: 8/8 PASS**
  (`installed-update-final-2/`). Session marker, synthetic save, backups and
  Electron state remain byte-identical. Updated runtime was started by the
  isolated harness; this is not an owner's real-PC acceptance. First run's
  harness failure is retained separately: CDP attachment took about 45 seconds,
  exceeding its original deadline; core startup itself took about one second.
  The harness now bounds/retries attachment and passes `/currentuser` to its
  disposable uninstaller. Zero UpdateTest processes/registrations remain.
- The Docker build now contains a final-image 24-case native-training gate with
  an independent complete-PKM oracle. Its Windows replay passes; **Linux has
  not run**, since no Railway build/deployment was started. All disposable
  PostgreSQL clusters are stopped. Port 55674 can be resumed using
  `074-pg-stopped.json` and `pg_ctl start`, never `initdb`.
- Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/virtual-training/20261101/`.
  Backup `database/pre-release-20261101T144128Z.dump`, captured 14:41:51 UTC,
  SHA-256 `0d4980c6f40abd6b111d14686dee927e3e1a285beddebf2895dd173a4ce5829a`;
  refresh if older than two hours before applying 074. Candidate build roots
  `PokeApp-releases/0.26.9-final` and `0.26.9-final-rehearsal` are outside Git.
- Release ordering after all gates pass: committed-source API bundle; apply
  rehearsed 074; API image with final Linux 24-case training gate; web with
  download card still 0.26.8 (missing versioned binaries now return 404); then
  immutable 0.26.9 installer, full public size/SHA-512 readback, signed feed last;
  finally web download card 0.26.9. The public readback can use the guarded
  Railway SSH transport because direct workers.dev access times out here.
  Private config/proofs are in `railway-public-readback/`; host pin is initial
  TOFU. The temporary Railway SSH registration and newly generated key files
  were removed and absence verified (`cleanup.json`); preexisting keys remain.
  A new temporary transport must be prepared if publication later needs it.

### Focused blocker follow-up (same review branch, no deployment)

No functional correction or release clearance. Only the native diagnostic
harness changed. It now supports `--case AS:gold --case UM:gold --repeat 8`,
records verification preflight / native-process / response-contract /
semantic-proof failures separately, and binds EventPipe files to unique call
numbers instead of reusable process IDs. Focused runs cannot claim full-matrix
acceptance. All real validation and consumption checks still execute.

- Exact historical source copies were reconstructed at `exact-blocker-fixtures/`:
  AS `d3fa62cc…c29c43`, UM `ff57f58e…bf15b`. Original evidence was not modified.
- One finite targeted run (`blockers-focused-8/`) completed eight fresh AS/Gold
  and eight fresh UM/Gold handoffs: 48 assertions, verified independent backups,
  native readback and exactly-once spending; 192 native calls / 192 unique
  EventPipe traces, zero managed exceptions. Every AS output equals the
  original retained output `9cb09e02…35dd3`; every UM output is `b2a81134…def`.
  `findings.json` explicitly says `NO_RECAPTURE_NOT_RESOLVED`, release_ready=false.
- **AS narrowed:** the old `NATIVE_VERIFICATION_FAILED` occurred inside
  `native.verify` after hash gates, not in the filesystem read/identity gates.
  Exact journal recipe and bytes pass a fresh packaged handoff. Original child
  response/inner exception was never captured, so process/transport, native
  rejection, response-contract and semantic-proof branches remain unresolved.
  Details: `as-boundary-probe-2/{assessment,result,calls}.json`.
- **UM narrowed:** original rejection occurs after source integrity and target
  checks, in legality analysis/new-invalid comparison, before output-save
  serialization. Original-DLL reflection shows Parsed=true on both normal
  targets and identical Encounter/Geography invalid findings. Gold preserves
  EXP/level/Nature/met data and HT flags0. Controlled disposable cases prove
  that !Parsed (suppressed NRE in NicknameVerifier) and a genuine new HT/IV
  violation produce the same public error, but different managed stacks.
  Neither control establishes the original cause. Details:
  `um-semantic-discriminator/report.json`. No settings-init cycle was found.

No full eight-game matrix was repeated: neither historical cause has been
demonstrated or corrected. Next genuine failure must be captured with the
focused harness, `--trace-native`, `POKEAPP_NATIVE_DIAGNOSTICS=1` and startup
EventPipe on the diagnostic CLI. Inspect the matching raw response/stderr and
`native-process-failure-*.json` / `verification-failure-*.json` stage, then decode
that call's `.nettrace` with the retained eventpipe-stack-decoder. Do not repeat
the prior 512 passing requests as a substitute for this missing discriminator.

Next: identify and fix the captured native intermittent rejection using its
retained failing raw inputs; do not substitute another passing retry or repeat
the preceding four fixes. Then rebuild and pass final package/journal,
real-service, Linux and installed-update gates, refresh the two-hour backup if
needed, publish and replace this blocked entry with verified release IDs.

## League, trainer profiles, navigation and held items — 2026-11-01

**PUBLISHED. Focused acceptance PASS; direct hosted-web visual acceptance remains
limited by the current network.** Source `662c3ea` supersedes the API/web versions
below. Railway `c70f9bd9-9c87-4a02-9310-1866b1140465` is SUCCESS, health OK,
**120 routes**, new collection source/reason and scouting item context verified
in the live OpenAPI. Cloudflare `754550f9-fc37-47e5-b112-91afacae5dd9` is active
at **100%**, with all 16 changed assets uploaded successfully. Supabase remains
001–073 (latest history entries 073 `20261029221703`, 072 `20261029221701`).
Launcher remains **0.26.8** and loads the published web; no native update needed.

- **League:** coin editing was coupled to the number of days, so a common amount
  could revert to the earlier positional map. Saving one day also replaced the
  stored positional points with zeros. Common/positional coins are now chosen
  independently for multiple days; the configured common amount survives day
  changes, while a valid positional point map is retained in one-day saves.
  The form uses the current/latest saved version, never obsolete default maps.
  Viewing another matchday does not change configuration. 073 still owns the
  effective scoring: one division + one day = 2/win, equal configured coins and
  Blindar/Robar prizes; multiple days = configured positional points and coins
  (including a uniform coin map). No scoring/default migration was introduced.
- **Profiles:** genuine Iker Y observations existed only in the personal sync
  record; the draft had no League-bound saves, while its collection read required
  that link. An enabled, active participant in a draft/active season with **no
  competitive pointer** can now show their synced observation through the same
  public Pokémon allowlist. It is labelled personal, never an official Team Lock
  or competitive identity/death evidence. Nonparticipants, inactive/disabled
  targets, historical seasons and broken/foreign pointers do not gain a personal
  fallback. Owner/hash/game/generation checks fail closed. IVs, abilities, private
  identities, raw metadata and storage details remain private. Explicit absence,
  processing and unsupported-data reasons replace the misleading generic text.
  The own profile also shows its save outside a season and prefers a newer
  personal sync over an older same-game League copy.
- **Navigation:** removed Mi PC from desktop/mobile sidebar, home tiles and
  internal links; `/pc/*` bookmarks and Launcher links redirect to the signed-in
  trainer's own profile. Existing save endpoints/data and native tools remain.
- **Held items:** X/Y ingestion omitted `item_generation`; older saved payloads
  also lost this display context. New ingestion includes it and reads recover it
  from the **same authoritative save game**, with conflict checks. No reupload
  is needed for old X/Y observations. Public scouting retains this harmless
  context; modal and battle rendering use it. IDs 158/217 resolve to Baya Zidra /
  Garra Rápida for Gen6/7, empty items stay empty, ambiguous missing-game IDs are
  not guessed from species or the viewer's game. Native parser/binary untouched.

### Focused evidence

- **75 React tests, 103 Python tests, 3 browser cases PASS**. Browser cases cover
  1440/390 px profiles and old-bookmark redirect, plus newer sync selection and
  held-item modal. TypeScript/Vite, affected Prettier, correctness Ruff, portable
  API/verifier imports and diff checks PASS. The final Linux image also passed
  its existing eight-game parser/native-progress smoke. Runtime log sample:
  zero tracebacks / HTTP 5xx.
- Fresh isolated 001–073 databases: five-player API create/save/read/switches
  1/2/3/4 days and A/A+B; **four actual close RPCs + four replays**, both positional
  coins and common 17-coin maps, no duplicate payouts or single-day prize leakage.
  Original 073 close/correction/prize/death/wipe/frozen-history regression PASS.
- Read-only projection against **genuine existing production observations**:
  Iker ready/personal/Y, 12 Pokémon including his six-member party; Aaron has no
  synced observation and returns `no_synced_save`; Anto ready/personal/Y, 20
  Pokémon with one actual ID158 and one ID217. Private fields absent in each
  public projection. No trainer, save, purchase, season, result or reward was
  modified in production during tests.
- Private evidence:
  `%LOCALAPPDATA%/PokeApp-migration-evidence/profile-league-hotfix/20261101/`
  (`acceptance.json`, `existing-observations.json`, `api-openapi.json`,
  `api-runtime.log`, `web-deploy.log`, committed API export `api-662c3ea/`).
- **Remaining verification limit:** public workers.dev requests time out from
  this connection, including before deployment. Provider activation is verified;
  a full public asset readback and authenticated visual check in the real
  web/Launcher session are **not claimed**. Recheck from a working connection.

Implementation and this MultiIA closure are committed/pushed; use Git for the
closure hash. The protected guide and unrelated initial untracked files remain
excluded. No database migration, native write, account alteration or installer
publication was needed.

## Multi-day League format hotfix — 2026-10-30

**PUBLISHED / VERIFIED.** Source commit `f5b68e9`; Cloudflare web version
`02916b5d-c903-4b1b-aaf6-ee3366accadc`. This entry supersedes the web version
below. API `3526625a`, Supabase 001–073 and Launcher 0.26.8 remain unchanged.

- Reproduced with five participants and a switch from one to four matchdays:
  React accepted `10,8,6,4`, but the existing SQL validator requires exactly
  positions 1 through participant count in **both** maps (also with divisions).
  The fixed four-number placeholder suggested values that were not saved.
  Conditional uncontrolled inputs also lost edited values when changing modes.
- Minimal web fix: show actual saved values, remove the misleading placeholder,
  explain the required count, reject missing/extra/blank/noninteger values before
  sending, keep explicit zero rewards, preserve separate positional/common-coin
  drafts across switches, and reload the saved shape/values together. Division
  capacity/movement validation now matches SQL. No reward amounts are invented.
- **23 React tests PASS**, including initial failing regressions, 1/2/3/4
  switches, valid five-position submission, invalid input and saved reread.
  **26 season-admin API tests + 6 League 073 tests PASS**. TypeScript/Vite,
  affected Prettier, correctness Ruff and diff checks PASS.
- `python -m tools.validate_league_format_hotfix --pg-bin <local PostgreSQL bin>`
  PASS on a disposable loopback database built from 001–073: actual FastAPI
  routes/repository/SQL create, replace and read one/four/two/three-day configs;
  A and A/B; rejected four-value update leaves stored setup unchanged. Synthetic
  native observations and actual initial-assignment RPC prepare five players;
  **four real close RPCs plus four replays** apply points `10,8,6,4,2` and coins
  `50,40,30,20,0` each day without duplicate payouts or one-day prizes.
  Existing 073 SQL regression also passes: 2 points/win, equal configured coins,
  Blindar/Robar, death 0.1 / wipe revival 0.2, corrections and frozen history.
- **18 public HTML/config/JS/CSS assets** match the final build byte for byte.
  Evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/league-format-hotfix/20261030/`
  (`acceptance.json`, `web-deploy.log`). No production season/configuration was
  edited during testing; no new migration, API or Launcher deployment.
- Implementation and this MultiIA closure are committed and pushed; use Git for
  the closure hash. The protected product guide and unrelated files were excluded.

## Shop delivery 072 and League rules — 2026-10-29, final publication

**PUBLISHED / VERIFIED.** Implementation and publication are complete. Acceptance
on friends' PCs and physical robbery/revive with real saves remains explicitly
pending. This entry supersedes the operational state below.

Entry HEAD was `9222cd4`, two commits ahead of fetched origin `3d59900`, with a
clean tracked tree. Claude's `74f9536` and `9222cd4` were retained and pushed.
Codex implementation `1166aa4`, package acceptance `3809621` and final tie-contract
fix `fcdda56` are committed and pushed. The documentation closure follows those
commits; use Git for its exact HEAD. Unrelated untracked files remain excluded.

### Final deployed components

- **Supabase 001–073**, 65 history records (001–009 predate the history table).
  Applied once: 072 `20261029221701`; 073 `20261029221703`. **Do not reapply.**
  SQL SHA-256: 072 `7535336d24f976dd1a71cceaf46ea3dee4d28fd732abafa91dbb592be02613ee`;
  073 `c43b1b91914f5e4dde43a20bf427d185407b7c0b35945df1328b8d04ee798432`.
- **Railway API** `3526625a-ec5c-411d-9f55-677b8fcb854a`, SUCCESS, from committed
  export `fcdda56` (328 files). Health 200, **120 routes**, deployed delivery
  identity field and `single_league_prize` enum checked. Claude's `9222cd4` removed
  the redundant refund route: 120 is correct, rather than the earlier draft's
  121. Refunds reuse audited 062. Verifier service/configuration unchanged.
- **Cloudflare** `f3c144a0-eefa-40c7-93a0-5305a11d27cb`, final `fcdda56` source;
  17 live JS/CSS/config assets byte-identical to the final build. The final deploy
  completed during the interruption; its completion was recovered, not repeated.
- **Launcher 0.26.8**, stable Ed25519 feed, minimum 0.26.0, existing stable key.
  Installer 159427247 bytes, SHA-256
  `3c8f54a96938b0a16d4e3b71176c2fc7cc97fbfa64011212d50c18a0c87cb233`.
  Immutable installer uploaded and read back before switching the feed; official
  download then checked in full after web deployment. The actual shipped 0.26.7
  updater accepts the remote 0.26.8 offer; 0.26.8 sees no further update.
  Authenticode remains unsigned under the established private-distribution policy.
  0.26.7 remains available at its immutable version URL.

### What was completed

- Claude had implemented the 072 table/RPCs, item contract, native delivery,
  Launcher journal flow and web/Electron panels. Recovered final evidence:
  web 246/246, TypeScript/Prettier PASS, Electron UI 80/80, native 1776 and free
  quick-item 281 checks. Those native matrices were retained, not rerun.
- Delivery now binds the reservation to the **server-accepted native trainer
  identity**, checked against the actual local bytes before preparation. An
  unbound or wrong same-game save cannot receive the object. Recovery completion
  now refreshes Inventory even when it finishes after the original action.
  Backups, emulator blocking, exact quantity, account isolation, idempotency,
  uncertain reservations and journal reconciliation remain enforced. Caramelos
  and Escamas retain their free independent flow. Chapa Plateada is refused in Y.
- **073**: one-division, one-day round robin earns 2 points per confirmed win,
  0 per loss, immediately in the League; closing does not add wins twice.
  Equal coins come from the configured reward map. A nonuniform map requires an
  explicit common amount during setup; no amount is invented or backfilled.
  First/last receive the existing Blindar/Robar items through audited reward
  purchases, once, after material ties are resolved. Multiple-day positional
  points/coins and Cup rules are preserved.
- New adjusted-death rate is 0.1; one wipe revival contributes two adjusted
  deaths (0.2), with the existing overlap protection and participant dead box.
  Three ordinary deaths plus one wipe revival deduct 0.5. One live total is
  shown; final closed totals and older corrections preserve their frozen rules.
- Final integration review caught a missing prize-tie value in the API model,
  browser parser and label. `fcdda56` fixes the full path; real planner tie →
  HTTP 409 → web parser → resolution form is tested. No SQL or Launcher rebuild
  was required for this API/web correction.

### Verification and preservation

- Fresh private backup captured 22:06 UTC:
  `pre-release-20261029T220554Z.dump`, SHA-256
  `1ce033a26b2221668066746307e2a7e93479831524acd3341b481a8700d73bc3`.
  Final committed-LF rehearsal **18/18 PASS**: 117 restored table fingerprints
  and catalog match; 95 business/Storage/Shadow tables and 104 reads unchanged;
  no new browser grants; fixtures rolled back; upgrade equals fresh 001–073.
  Migration hashes are fixed and checked throughout. The earlier CRLF-source
  rehearsal is retained separately; publication used the final LF hashes above.
- Focused tests PASS: delivery Python **96**, Launcher UI **81**, League Python
  **85**, Admin/League React **22**, final tie API **36** and React **21**;
  release gates **6**, Electron confirmation/supervisor **23**. Groups overlap
  and must not be added as unique tests. Final TypeScript/Vite build, affected
  Prettier, correctness Ruff and diff checks passed.
- Final package: audit PASS; actual executable startup/recovery **9/9**;
  packaged Python bytecode + real native writer + disposable NTFS saves **21/21**,
  including uncertain post-publish recovery without double delivery. Dependency
  audit: 71 core and 185 parser PE files use bundled or stock Windows libraries;
  parser is self-contained .NET 8.0.29. Fixture generation also uses a complete
  self-contained runtime, avoiding the host's incomplete shared runtime.
- Actual NSIS clean install/update **8/8**, using a disposable UpdateTest identity
  with byte-identical stable code/runtime payloads (15 app and 303 runtime files
  per version, except test package metadata). Encrypted session marker, selected
  synthetic save, backups and Electron storage survive 0.26.7 → 0.26.8. Test
  installation uninstalled; zero UpdateTest registrations remain. This proves
  isolated retention, not a login on an actual friend's PC or an owner install.
- Post-migration production preservation **8/8**: **116 previous tables remain
  byte-identical**; only the 117th, migration history, grows 63 → 65. New delivery
  table empty, FORCE RLS, no browser rights; 17 operational functions service-only.
  Existing policies/schema ACLs unchanged. Advisors add only two expected INFO
  entries (private table without policy, fresh unused index), no WARN/ERROR delta.
  Owner purchases (including Chapa Plateada), balances, saves and seasons unchanged.
- Final public acceptance **22/22**, including full installer hash/signature,
  tamper rejection, API authorization denial and CORS. Public Edge at 1440/390:
  both screenshots reviewed, zero overflow and JS/HTTP errors. Final API runtime
  log has no traceback or HTTP 5xx in the inspected window. No real account login
  or production business write was used to produce these checks.

### Next normal use and acceptance boundary

No remaining deployment or known reproducible technical blocker in this scope.
There are currently **no active seasons** (the three existing seasons were already
discarded on entry). Normal setup still belongs to the owner: create a season,
enrol players, select the format/common coins and set Anto's Y participation to
**Caja 7**, then prepare/open the matchday. Existing discarded seasons were not
changed or replaced by this work.

Friends should install/update to 0.26.8, confirm the correct account, reopen to
check retained session/save, and verify automatic sync after saving. Reuse
[the short installation/linking instructions](../launcher-amigos.md). If a PC
fails, collect its masked Launcher diagnostic. No acceptance on that PC is
claimed until it is observed. Physical robbery and physical revive remain
pending real-save acceptance; this release does not certify them.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/shop-delivery-league/20261029/`:
`recovered-claude-tests.json`, `rehearsal.json`, `apply/`,
`final-readonly-preservation.json`, `api-final-deployment.json`,
`final-assets-api.json`, `hosted-acceptance.json`, `hosted-final/`,
`package-delivery-final/`, `packaged/`, `installed-rehearsal-final/`,
`public0268updateproof.json`, build/deployment logs. Build root:
`%LOCALAPPDATA%/PokeApp-releases/0.26.8/`.

Protected guide was not opened, read, searched, copied, moved, hashed, modified
or staged. Unrelated untracked files remain untouched. Explicit staging only;
no forced push, destructive Git cleanup, owner installation, real-save write,
automatic refund, credential exposure or Discord message.

## Launcher 0.26.7: supervised core («Sin conexión» on a friend's PC) — 2026-10-29 17:40 UTC

**PUBLISHED / VERIFIED here; the friend's PC itself was not accessed.** Commits
`262a993` (fix), `1f972b5` (0.26.7), `f51dac0` (web card, acceptance stage).
API, DB (071) and verifier unchanged.

- **Symptom:** the hub stayed «● Sin conexión» and actions said «El núcleo del
  Launcher está tardando en responder» while the web showed the account signed
  in. **Reproduced exactly:** once the Python core exits, 0.26.6 never starts
  it again (`worker.killed` stays false, writes to the dead pipe fail
  silently) and every later request, forever, ends in that timeout; the hub
  never gets a state, so its initial «Sin conexión» stays.
- **Code-detectable causes found:** (1) no single-instance lock: a second
  window (double click while the first opens) starts a second core, which
  dies in 0.6 s on `LAUNCHER_ALREADY_RUNNING` (reproduced with the packaged
  0.26.6 core; its traceback went to an ignored stderr); a core outliving its
  window holds the profile 15 s with a request in flight (measured; up to
  90 s by the joins). In the packaged app libuv's kill-on-close job ends the
  core with Electron, so overlapping instances are the main path. (2) Any
  startup error ended it the same way (e.g. an unreadable `config.json`).
  (3) TLS: the core trusted only the bundled certifi roots; this PC's Windows
  store holds a Kaspersky interception root that does not intercept the core
  here, but an antivirus/proxy that scans HTTPS would leave the core offline
  while Chromium (Windows store) keeps the web signed in. (4) `state` waited
  behind backup re-verification (under the controller lock) and the emulator
  search (on the pipe thread). (5) Session sharing asked the core once at
  start: a core slower than 5 s left the web without the Launcher session.
  Packaged dependencies checked: 71 core + 185 parser PE files, no import
  outside the bundle or stock Windows.
- **0.26.7:** single instance; supervised core (`core-supervisor.cjs`:
  STARTING/WAITING_PREVIOUS/READY/FATAL events, restart with backoff, a silent
  core restarted only if no physical command was sent in 120 s and no state
  said `write.busy`; otherwise waited for and reported); core waits up to
  120 s for a held profile; FATAL codes + exit codes; bad `config.json` set
  aside (`config.invalid-*.json`); shutdown joins the write loop (90 s) but
  not a hung request (3 s); Windows store + certifi roots; failure kinds
  (`TLS_UNTRUSTED`…) in the state and the hub; an access token the server
  already expired is refreshed once before signing out; discovery beside the
  pipe; backups verified outside the lock; hub rows «Núcleo local»,
  «Conexión con PokeApp», «Cuenta» apart (the last account kept while the
  core restarts), «Reintentar ahora», «Copiar diagnóstico» (masked
  `logs/launcher.log` + `logs/core.log`, no token/PIN/save); update notices
  no longer depend on the core.
- **Validation:** Python **1294 OK** (18 new); Electron **45/45** (13 new);
  UI smoke **71/71** (9 new); dev and **packaged** end-to-end: core killed →
  READY again by itself ~1.8 s; second instance exits, no second core;
  Launcher killed → its core gone in 0.8 s; reopened → READY 1.3 s.
  Package audit PASS; packaged acceptance **7/7**; installed 0.26.6's own
  updater/key accept the 0.26.7 manifest, 0.26.7 sees no update. Installer
  159398331 bytes, sha256 `e884350a…919e11`, unsigned (private distribution);
  R2 read back, then `updates/stable.json` (min 0.26.0). Web `c4dd88e2`
  (card 0.26.7); hosted acceptance `--stage launcher_recovery` **19/19**.
- **Pending on the friend's PC (not claimed solved there):** update to 0.26.7
  (in-app offer, or the web download); if the hub still shows a core problem,
  «Saves y Launcher → Launcher → Copiar diagnóstico» and send the text.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/launcher-recovery/20261029/`
(`packaged/acceptance.json`, `packaged-recovery.txt`, `update-chain.json`,
`launcher-publication.log`, `web-deploy.log`, `hosted-acceptance.json`).
Build root `%LOCALAPPDATA%/PokeApp-releases/0.26.7/`.

## Shop in the preseason and selective animated sprites — 2026-10-29 15:50 UTC

**PUBLISHED / VERIFIED.** Commits `792ab48` (DB 071, API, Shop web), `ca2c513`
(sprites). Launcher unchanged (0.26.6: no packaged component changed).

- **Shop root cause (reproduced on a restored production backup):** every
  purchase in an active season resolved the current matchday, and
  `api_resolve_current_matchday` raises 409 `current_matchday_required` while
  J1 is not prepared (Prueba2's preseason). Production logs: six purchase
  attempts, all 409. The web showed the generic 409 text plus «Los datos
  cambiaron mientras editabas» for any 409.
- **071** (sha256 `82dfc27b…0ad621`): preseason purchases run with a NULL
  matchday (as after a finished League); price confirmation, promotions,
  Store Ban, balance, idempotency, ledger and audit unchanged. Shop proof on
  the backup (`tools.validate_phase071_shop`): owner's exact purchase refused
  before, accepted after (32 → 20 PK₽, once), all enabled catalog items
  purchasable within the balance, same key = same receipt, past the balance =
  `insufficient_funds`; rolled back. Rehearsal on a fresh backup
  `pre-release-20261029T153428Z` **14/14 PASS**; applied **once** as
  `20261029154136`.
- **Web:** Spanish reason per purchase refusal; «Los datos cambiaron» only for
  stale-data codes; «Saldo insuficiente» on the item before trying.
- **API** `002dd4dd-d682-4fcc-a9c8-fb11aca9acc5` (115 routes): Supabase Auth
  (the session check on every request) on a pooled HTTP/1.1 client, after
  bursts of `AUTH_UNAVAILABLE` across endpoints in the same millisecond.
- **Sprites:** `animated/v2` = Showdown battle-model clips (pinned PokeAPI
  mirror, same clips as the Gen7 stills' source), base forms, normal + shiny,
  **799** species. Frame 0 checked against each Gen7 still; 36 pose/scale
  differences reviewed by eye; 666 Vivillon and 716 Xerneas excluded (clip
  shows another form); 597 and 803-807 static. Attribution and licence files
  retained (same terms as the existing v1 set). Animate only in Home, a
  trainer's team (Entrenadores) and the Pokémon card; «Mi PC», boxes, Team
  Preview, selectors, Shop, Inventory and League static. Visible-only, on
  demand, stopped off-screen/hidden/unmounted, never with reduced motion.
- **Cloudflare** `20710365-a626-4a5b-9dd8-5865aaf8814b`; live GIFs and chunks
  byte-identical to the build; hosted acceptance `live_league` **19/19 PASS**;
  API logs clean.
- **Validation:** web **242/242**, TS, Prettier; Python focused **211 OK**
  (20 affected modules); new tests for purchase reasons, stale-only notice,
  funds hint, animation contexts, forms/exclusions, shiny, reduced motion.
- **Owner acceptance pending:** a real preseason purchase (balance and
  inventory refresh), and the three animated contexts in the Launcher.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/shop-sprites/20261029/`
(`shop-proof.json`, `rehearsal.json`, `apply/` with the 071 intent/result,
`hosted-acceptance.json`, `api-deploy.log`).

## Second real test (Objetos ∞, live data, Box 7, one total) — 2026-10-29 11:55 UTC

**PUBLISHED / VERIFIED.** Commits `a0b121e` (Launcher), `b0e4406` (API+DB 070),
`2041edd` (web), `c3d9f41` (0.26.6), `ea98192` (release card). Supersedes the
069/0.26.5 state below.

- **Objetos ∞ root cause (reproduced on the installed 0.26.5 core with a copy
  of the owner's Y save):** the build overlay copied one fixed domain module,
  so `app.domain.unlimited_items` was missing from `PokeApp.Core.exe`; every
  quick-item command raised ImportError outside its handler, the panel stayed
  on «Leyendo…» and the save was marked LOCAL_UNAVAILABLE. Second blocker found
  on the way: a write was refused whenever the cloud round held its read
  (seconds, every 30 s). Fixes: overlay by AST (transitive), audit requires
  every desktop module, quick steps always end with counts or a reason, writes
  wait up to 30 s with writer preference. «Cambios en tu partida» no longer
  says trades are disabled (that text was the idle state of the physical-write
  journal) and hides when idle.
- **Proof on disposable copies only:** source core and the packaged 0.26.6
  core both read the bag (0.25-0.5 s), add 3 Caramelos Raros and 2 Escamas
  Corazón (~2.3 s each, backup verified, native re-read 3/2), refuse an
  over-limit amount with the file untouched. The owner's real save hash
  (`1abf8fa2…`) is unchanged.
- **Restart needed for Liga: root cause in production logs.** After the owner's
  «Revividos» PUT (10:24:14, 200) every League/wipe read returned 503 for ~30 s
  (`frontend_read_retry … ReadError` then failed): supabase-py's single shared
  HTTP/2 connection dropped and took every multiplexed read and its retry with
  it; the web retried once and kept the old figures. PostgREST now runs on one
  pooled HTTP/1.1 client (reads retry once on a dropped connection); the web
  retries 5xx/network reads at 1/2/4 s, refreshes visible screens every 60 s
  and coalesces a sync's Launcher events. The tested invalidation map already
  refreshed the League after «Revividos»; it is unchanged.
- **Sync timing (measured before changing):** local stat 0.35 ms, read 2-8 ms,
  PKHeX parse ~0.19 s; a real sync took ~29 s from first request to
  «Sincronizado», ~6 s of it uploads, the rest ~10 sequential requests at
  ~1.2 s each. Now: 1 s poll, 0.75 s stability window, the season copy goes
  first and, with a fresh cached state, uploads start at once (no health probe,
  /v1/me, five season reads or two receipt re-reads); the web is told when each
  copy is accepted. Expected League refresh ~8 s after saving (estimate from
  the measured request times; owner-side measurement pending).
- **070** (sha256 `826ccd09…e89d3b`): `season_players.dead_box_number`
  (default 8) used by the League, closings (`matchday_context_v034`), revive
  overlap/redemption, initial divisions and robbery targets (never the dead
  box); audited admin command `PUT …/participants/{id}/dead-box`; the League
  read returns ONE total (active season: official points with the current
  cumulative deductions, the figures the next closing records, so nothing is
  subtracted twice; `official_points` kept). Owner request: Anto's active
  participation counts Box 7. Fresh 001-070 + focused validator PASS. Backup
  `pre-release-20261029T113052Z.dump` (sha256 `3def1caa…4f5b7c`) rehearsal
  **17/17 PASS** (94 tables byte-identical, `season_players` identical apart
  from the column and `updated_at` on the one row set, no privilege change,
  equals a fresh build). Applied **once** as `20261029113828`. Rehearsed
  result: Anto −0.6 (Box 7 holds 1, one wipe revival counts 2), others 0.
  The engineering-only physical revive (054, disabled) keeps its Box 8 contract.
- **Railway** `pokeapp-api` deployment `8e1f43ed-cf5c-4a5d-8312-9f2425b4318a`
  from export of `c3d9f41`; **115 routes**. Verifier worker unchanged (it uses
  direct Postgres repositories).
- **Web:** one «Puntos totales» (Spanish format, negatives), no provisional
  line, preseason box or death dates; «Revividos tras wipe» = Cantidad +
  Actualizar; «Mi PC»/profiles/revive targets use the participant's dead box;
  admin «Caja de muertos»; permanent explanatory paragraphs cut across the main
  screens. Cloudflare `a343b0cf-294c-459e-b203-c12a55f0e901`.
- **Launcher 0.26.6:** audit PASS (core lists `app.domain.unlimited_items`);
  packaged acceptance **6/6 PASS**; the installed 0.26.5's own updater and key
  accept the signed 0.26.6 manifest (size/SHA-512 bound), 0.26.6 sees no
  further update. Installer 159337184 bytes, sha256
  `4ae3962dfe625a44812a34da756a5acc690d5ad2c55a7bc2e52a767c79ac6be2`, unsigned
  under the private-distribution policy. R2 installer read back, then
  `updates/stable.json` (minimum 0.26.0). No install on the owner's profile.
- **Validation:** Python **1275 OK**; web **224/224**, TS, Prettier; Electron
  **32/32**; hosted acceptance `--stage live_league` **20/20 PASS**; API logs
  clean after the deploy.
- **Owner acceptance pending:** in-app update 0.26.5 → 0.26.6; «Objetos ∞» on
  the real save (emulator closed); a save with a Pokémon in Box 7 and the
  League total changing without restart; «Revividos» and a purchase refreshing
  at once.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/real-test-corrections-2/20261029/`
(`rehearsal.json`, `070-migration-*.json`, `update-chain.json`,
`packaged/acceptance.json`, `hosted-acceptance.json`, `api-deploy.log`,
`launcher-publication.log`). Build root `%LOCALAPPDATA%/PokeApp-releases/0.26.6/`.

## Real-test corrections (15 incidents) — 2026-10-29 03:00 UTC

**PUBLISHED / VERIFIED.** Commits `886f8de` (API+DB 069), `5c165d1` (Launcher),
`8a3b163` (web), `795673a` (0.26.5), `8200da8` (release card); main = origin/main.
Supersedes the 0.26.4/068 production state below.

- **Validation:** Python **1258 OK** (the interrupted run's 7 failures were 3
  runner artefacts without `PYTHONPATH=tests`, 3 stale route counts 108→114 /
  44→49 / 404→405, and one real Launcher bug: a non-dict season save context now
  reads as an older API). Web **222/222**, TS, Prettier; Electron **32/32**.
- **Preseason rule check:** existing rules give points only per matchday position;
  each closing subtracts cumulatively 0.2 per adjusted death (Box 8 + revivals −
  overlap + 2 per wipe revival) and resolved points sanctions. Nothing was lost
  before J1, but it was invisible. 069 §4 adds read-only provisional figures to the
  League (`provisional_points/dead_count/points_reduction/matchday_number`, active
  seasons, same inputs as `matchday_context`); the web shows them apart from the
  official total. Coin sanctions already hit the ledger at once; Gen6/7 medals and
  the champion now pay the existing coin rules once (Gen7 stamps pay nothing).
- **069** (sha256 `c5ddb335…754803`): fresh 001–069 validator PASS; production
  backup `pre-release-20261029T023853Z.dump` (sha256 `e3245e41…68f712`) restored,
  rehearsal **PASS** (93 tables identical, 78 reads identical apart from one paid
  balance, no new browser grant, replay pays 0, upgrade = fresh build). Applied
  **once** as `20261029024119`. Only data change: Anto (Prueba, Pokémon Y, 8
  observed badges, no champion) **8 claims / 32 coins**; Samuel (US) 0. The system
  cannot tell PKHeX-set badges from played ones — same standard as Gen3-5.
  Post-capture: **114/117 tables byte-identical**; only ledger 0→8, claims 0→8,
  history 60→61. New functions service-role only; no Discord row or activity event.
- **Railway** `pokeapp-api` deployment `5e537567-baa2-4021-ae64-0a7a1500f0ac`
  SUCCESS from export of `8a3b163` (321 files). 114 routes. Verifier worker not
  redeployed (its changed imports are API-only/Windows-only).
- **Launcher 0.26.5**: package audit PASS; isolated packaged executable **6/6 PASS**;
  0.26.4's embedded key and unchanged updater accept the signed 0.26.5 manifest
  (size/SHA-512 bound), 0.26.5 sees no further update. Installer 159332349 bytes,
  sha256 `975939d26c6def1ff9403ad75752e1f34e73f12ebf70a671099527ebe1ea4301`,
  unsigned under the private-distribution policy. R2 installer read back, then
  `updates/stable.json` (minimum 0.26.0). No install on the owner's profile.
- **Cloudflare** `166e044c-29ad-4cc4-953e-69f3d279855a`; hosted bundle equals local.
- **Hosted acceptance `--stage real_tests`: 20/20 PASS**; public Edge 1440/390 login
  and Gen6/Gen7 PNG assets PASS; API logs clean.
- **Owner acceptance pending (real saves/accounts, not simulated here):** 0.26.4 →
  0.26.5 in-app update on both PCs; emulator search and live sync with real
  saves; same active game in Launcher/Entrenadores/Mi PC/profile; Rare Candy /
  Heart Scale on a real save; account repair tools and season cancellation on
  real data; provisional League figures with real deaths.

- **Second packet (verification only, no new code):** real read-only emulator
  search on the owner PC finds the Lime3DS AppData Pokémon Y save
  (`real-discovery.json`). Production has **no personal-save rows yet** (0.26.4
  sent saves only to the season); 0.26.5 always syncs the selected save to the
  personal record and to the season only when it is the save that season
  accepts, so Entrenadores/Mi PC follow the selection after both players update.
  No player-facing coin movement list exists (balance in League/shop; claims and
  ledger traceable for the admin) — left as an owner decision, not built.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/real-test-corrections/20261029/`
(`rehearsal.json`, `069-migration-*.json`, `preservation.json`, `update-chain.json`,
`packaged/acceptance.json`, `hosted-acceptance.json`, `public-browser.json`, logs).
Build root `%LOCALAPPDATA%/PokeApp-releases/0.26.5/`.

## Sprite correction — 2026-10-28 19:46 UTC

**PUBLISHED / VERIFIED.** Entry `384d181bf8e6f20fd9ae0aabf425af7d6750647b`,
main/origin aligned; final web source `cf68afcc1c651c359b40937d3c39badc1ee3d967`,
committed/pushed before Cloudflare publication. Owner now confirms automatic Y
sync works. This supersedes the earlier awaiting-owner observation below.

- Exact read-only species/form/level inspection found legacy `PokÃ©mon #647`,
  `#718`, `#371` labels, with levels 6/5/10. The original sprite URLs already
  returned correct PNGs; shared display resolution rejected the encoded prefix.
  The resolver now accepts that precise numeric prefix without rewriting data,
  nicknames, ingestion or synchronization. All screens using PokemonSprite benefit.
- Existing local assets extended to base species 1–807 and 16 explicitly mapped
  forms (Keldeo, Zygarde, Raichu, Charizard, Deoxys, Rotom). Pinned source/hash
  manifest retained; 102 new PNGs, 87,428 bytes. Unknown forms remain explicitly
  unavailable, never silently depicted as another form. Network/image failures
  have a distinct accessible fallback and bounded diagnostic; failed animations
  retain the static sprite. No card CSS/layout or shiny-palette change.
- **51 focused React tests, 6 local Edge cases PASS** (one test-only strengthened
  GIF-failure assertion rerun separately). Coverage includes the three observed
  labels, generations, forms, detail, Home animations, reduced motion, static boxes
  and actual asset failure. All **823 static sprite hashes** verified. TS/Vite,
  focused formatting/Ruff/compile, diff and Wrangler dry-run PASS. No backend,
  PostgreSQL, synchronization or historical full suite rerun.
- Cloudflare version **f12d4c1f-589e-44ae-aa75-2811193c2104**, 100%, published
  19:40:56 UTC. **25 hosted asset byte comparisons + health 200/private-PC 401 PASS**.
  Two hosted Edge journeys at 1440/390 and their visual review PASS. Existing
  packaged **Launcher 0.26.4** also displays all three decoded hosted sprites;
  isolated profile, real native IPC, no selected save, no business commands or JS
  errors. Auth/PC browser responses are synthetic; no owner PIN/login used.
  Packaged harness locator/screenshot auto-waits stalled on Electron's intercepted
  session navigation; DOM polling and direct CDP capture resolved this test-only
  issue, with no product change. Failed harness reports retained separately.
- API/Railway, schema 068, R2 installer/feed and Launcher binary unchanged. No
  Pokémon, save, owner, economy or competitive write. Production changes are only
  Cloudflare web assets. No new phase. Refresh the web/reopen Launcher for visual
  owner acceptance; do not resync or reselect the save to fix an image.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/sprites/20261028/`:
`public-sprites.json`, `launcher-sprites.json`, local/hosted1440/390 and packaged
screenshots; isolated disposable profile retained with the evidence. Source and
test fixture updates are explicitly staged; unrelated files remain untouched.
The final documentation/test-harness commit follows the deployed source; use Git
for exact final HEAD. No pending publication remains.

## Earlier corrections publication — retained evidence

2026-10-28 19:19 UTC (20:19 Europe/Madrid). **CORRECTIONS PUBLISHED / VERIFIED.**
This is the current operational handoff. The deployment blocker is resolved for
this release; no claim that Railway's wider incident is resolved.
Entry main/origin `392866c8ba2bd86f1ea8ffa120cbd10e3da61fc5`, aligned.
Application source `c0dd5619c1ffef311154a6994624572ec4526d62` and release pointer
`d2d2832860229854a94779839be42a6764f969a9` are committed and pushed.
The subsequent documentation commit carries this record; obtain HEAD from Git.
Resume entry `721850b48ca7404969d1736b68e5b7e1833a627a`, main/origin aligned,
tracked tree clean. No implementation or historical test matrix was repeated.

## Implemented and validated

- Personal sync failed before HTTP: BackendClient did not allow `/v1/me/save/raw`.
  The exact route is now admitted. Technical failures retain automatic retries
  with bounded backoff instead of stopping after five attempts. Semantic blocks,
  receipt reconciliation, identity checks and stale-save protection remain.
  No manual sync/reselection is introduced. The owner's real Y acceptance after
  updating has **not** been observed; the published package fixes the demonstrated
  transport/retry defect, not a claimed positive hosted owner import.
- Removed the enormous initial-assignment card from player Liga. Admin retains
  a concise preparation explanation. One enrolled player may prepare; actual
  competition needs another enrolled player, not simultaneous online presence.
- Published 068 reuses owned, accepted native Gen6 gym progress for readiness;
  unknown remains unknown and Gen6/7 reward authorization is unchanged. It adds
  narrowly guarded active-precompetition cancellation with name/reason/revision,
  logical status, audit and idempotency, preserving saved rows and pointers.
  Official activity blocks cancellation. Before competition, championship reads
  report incomplete competition rather than fabricated historical corruption.
- Finished inherited 067 private Discord outbox and worker. Confirmed events only,
  public rendering, no historical backfill or provisional-result/save-sync spam.
  Claim fencing protects concurrent workers. Ambiguous POST outcomes become
  uncertain without replay; only proven safe failures retry, with a bounded budget.
  Webhook URLs are redacted from HTTP logs. Failures do not block competition.
- Login title is PokeApp; Liga Nocturna retained. Modern routes have no obsolete
  Normas screen. Legacy Discord modules still have legacy callers and were retained.

## Validation actually executed

Focused Python groups: **78 PASS**, affected Launcher regressions **46 PASS**;
final correction module **15 PASS**, announcement rendering **4 PASS**. These
overlap; do not sum them as unique tests. Affected React: initial 19 PASS, then
final Admin 16 PASS after adding active-cancellation coverage (20 affected cases
combined with retained recovery cases). Edge: **14 unique affected cases PASS**;
one Unicode fixture typo was fixed and only that case rerun. No historical matrix.

Fresh private production backup restored **116 table fingerprints and catalog**.
Disposable PostgreSQL: 067/068 apply once; 94 business/Storage/Shadow tables unchanged;
48 existing reads equivalent; no browser grants expanded; FORCE RLS checked;
native-readiness/unknown/reward denial, solo preparation, cancellation/replay and
outbox dedupe/privacy PASS. Fixtures rolled back; upgrade equals fresh 001–068.
The initial fixture visibility typo was a harness error, corrected before PASS.
Disposable clusters were removed/stopped. This is SQL native-envelope evidence,
not a repeated authentic-game parser matrix.

TypeScript/Vite, Wrangler dry-run, targeted Ruff correctness, formatting, syntax
and diff PASS. Full style Ruff had pre-existing/style findings; no full-clean claim.
Packaged 0.26.4: audit and **6 isolated real-executable checks PASS**, native worker,
startup, account isolation, official web and bridge restrictions. Modified packaged
Python modules match final source AST. Existing SDK 9.0.318 completed the locked
net8/runtime 8.0.29 build after the system dotnet lacked an SDK; locks were retained.

## Actual publication and preservation

- **Cloudflare published:** version `305cb813-ed83-4829-ad2d-188a95b733bc`, 100%,
  2026-10-28T19:01Z, from d2d2832. Live JS/CSS match local build. The new Admin UI
  consumes the deployed `can_discard` contract. Not redeployed during the resume.
- **Launcher 0.26.4 published:** stable Ed25519-signed feed, existing stable key,
  minimum 0.26.0. Installer 159313550 bytes, SHA-256
  `8e5af40992b63b0f07530cb32996e0a338cfaa369625f34f32e963e1368d60d6`.
  R2 readback verified before feed publication. Authenticode remains unsigned
  under the existing approved private-distribution policy. No owner installation.
- **Railway published:** `893d5345-0bf2-4ab8-9ce1-9da649270eb9 SUCCESS`, source
  c0dd561, image `sha256:f88032fac74486e51e3ad02ebbb5073be79d873aeca3f1eed88e6a707eb95b3b`.
  The earlier attempt was rejected before a deployment ID. On this explicitly
  authorized resume, CLI authentication/target and absence of an in-flight build
  were checked, all 321 export hashes matched, and one new upload was accepted at
  19:12:46 UTC despite the still-open status-page incident. Locked Linux parser
  publish and production-runtime eight-game smoke passed; no NU1004. No rebuild
  from a dirty tree, additional upload or changes to the verifier service.
- **Database 068 / 60 records:**067 applied once as `20261028191441`, 068 once as
  `20261028191443`, after new API health 200 and OpenAPI contract verification.
  The exact backup hash and PASS rehearsal were retained; backup age 31 minutes,
  116 fingerprints still identical, zero open days/pending purchases, preflight
  problems empty. No new backup/rehearsal was needed within the two-hour gate.
- Owner supplied webhook configured privately as `POKEAPP_DISCORD_WEBHOOK_URL`
  using stdin and skip-deploy. Exactly **one authorized test delivered**, message
  `1565077343641542747`. No URL in source, evidence or logs. **Automatic competitive
  announcements enabled:** deployed worker/configuration and three triggers checked;
  service delivery reads succeed, queue empty. The one pre067 worker error at
  19:14:01 is expected; no error/disabled warning after migration through 19:19.
  No second message, artificial event or historical replay. An actual competitive
  event delivered by the hosted worker remains observable only on normal future use.
- **9 public checks PASS**, including health 200, authentication denial 401, asset
  equality, build config, feed and installer. Public desktop 1440/mobile 390 browser
  checks PASS; screenshots reviewed, no overflow or JS errors. No PIN/login or
  owner business mutation. API remains healthy despite the deployment incident.
- Resume public verification: **11 checks PASS**, new OpenAPI contract, Admin/me
  auth denial, health, correct API build config, exact web assets and download.
  Live stable feed signature verifies against the key embedded in 0.26.4; version
  and minimum remain 0.26.4/0.26.0. No web or Launcher republish.
- Real service-scoped read RPCs + current API model validation confirm Prueba:
  active, one participant, `can_discard=true`; preparation blocked by
  `progress_unobserved`, `death_inputs_unobserved`, `opponent_missing`;
  championship `incomplete` / `competition_incomplete`. No cancellation invoked.
  This does not impersonate an owner JWT or claim a new authenticated browser login.
- Final preservation: **115/116 previous tables unchanged**; only migration history
  gained 067/068. New private outbox is empty. Ephemeral Auth session/refresh rows
  are excluded by capture policy. Catalog differences match 067/068 only: one table,
  three triggers and the expected functions/indexes/constraints; 108 existing RLS
  policies and schema ACLs unchanged. New outbox forces RLS, browser access and
  service INSERT denied; five read helpers remain service-only.
  Owner identity, seasons, saves, economy, Team Locks, history, Storage and Shadow
  were not mutated. No physical save write, V1 access or unrelated cleanup.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/final-corrections/20261028/`.
Backup `pre-release-20261028T184219Z.dump`, captured 18:42:46 UTC, SHA-256
`792993f94e095e772ca9277b7c3c45ccfcf7f2fe38a8f2d9229c211747539f98`;
`rehearsal.json`, `preservation.json`, `public-smoke.json`, `public-browser.json`,
`discord-test.json`, package/build/publication logs. API export `api-c0dd561/`.
Resume: `resume-premigration.json`, 067/068 intent/result files,
`hosted-domain-reads.json`, `resume-public-smoke.json`, `resume-update-feed.json`,
`resume-preservation.json`, `resume-catalog-diff.json`, `resume-final-state.json`.
Installer/package evidence under `%LOCALAPPDATA%/PokeApp-releases/0.26.4/`.

## Final boundary and next owner use

No pending deployment or migration remains for this correction package. Do not
reapply 067/068 or republish unchanged components. Owner can take the normal 0.26.4
update and let automatic synchronization process the existing selected Y save.
Actual owner save acceptance is not asserted before it happens. Preparation may
be inspected solo; starting competition requires another enrolled trainer. Prueba
can be cancelled only through the owner's deliberate confirmed Admin action.
Observe future genuine competitive notifications without replaying history or
posting another test. No new phase or task is started by this closure.

Protected guide and unrelated untracked files remain untouched. Explicit staging
only. Production writes by this task are limited to authorized deployment assets,
the secret configuration, 067/068 schema/history and one earlier Discord message;
no owner/business data mutation.
