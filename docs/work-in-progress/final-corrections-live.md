# Final corrections — live execution record

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
