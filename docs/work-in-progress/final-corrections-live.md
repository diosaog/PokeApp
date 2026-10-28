# Final corrections — live execution record

2026-10-28 19:06 UTC. **PARTIALLY PUBLISHED. BACKEND RELEASE BLOCKED BY RAILWAY.**
This is the current operational handoff. No full completion claim.
Entry main/origin `392866c8ba2bd86f1ea8ffa120cbd10e3da61fc5`, aligned.
Application source `c0dd5619c1ffef311154a6994624572ec4526d62` and release pointer
`d2d2832860229854a94779839be42a6764f969a9` are committed and pushed.
The subsequent documentation commit carries this record; obtain HEAD from Git.

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
- Pending 068 reuses owned, accepted native Gen6 gym progress for readiness;
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
  tolerates the old API; active cancellation stays unavailable until backend+068.
- **Launcher 0.26.4 published:** stable Ed25519-signed feed, existing stable key,
  minimum 0.26.0. Installer 159313550 bytes, SHA-256
  `8e5af40992b63b0f07530cb32996e0a338cfaa369625f34f32e963e1368d60d6`.
  R2 readback verified before feed publication. Authenticode remains unsigned
  under the existing approved private-distribution policy. No owner installation.
- **Railway NOT updated:** one attempt from the 321-file committed API export was
  rejected with `Deploys have been paused temporarily`, before any deployment ID.
  Reconciliation still shows `6ded28f4-731e-4e7d-bda8-5dd2508b5bc3 SUCCESS`.
  The official [Railway incident](https://status.railway.com/) remained identified
  at 19:06 UTC (deployments stuck initializing, since 17:49 UTC). No blind retry.
- **Database remains 066 / 58 migration records. 067/068 NOT applied.** Applying 068
  before the new API would break the old strict setup model; leave SQL unchanged.
- Owner supplied webhook configured privately as `POKEAPP_DISCORD_WEBHOOK_URL`
  using stdin and skip-deploy. Exactly **one authorized test delivered**, message
  `1565077343641542747`. No URL in source, evidence or logs. **Automatic competitive
  announcements are NOT live** until API and 067 are published. Do not retest-post.
- **9 public checks PASS**, including health 200, authentication denial 401, asset
  equality, build config, feed and installer. Public desktop 1440/mobile 390 browser
  checks PASS; screenshots reviewed, no overflow or JS errors. No PIN/login or
  owner business mutation. API remains healthy despite the deployment incident.
- Final preservation: **116/116 captured tables unchanged**, migration history
  unchanged. Ephemeral Auth session/refresh rows are excluded by capture policy.
  Owner identity, seasons, saves, economy, Team Locks, history, Storage and Shadow
  were not mutated. No physical save write, V1 access or unrelated cleanup.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/final-corrections/20261028/`.
Backup `pre-release-20261028T184219Z.dump`, captured 18:42:46 UTC, SHA-256
`792993f94e095e772ca9277b7c3c45ccfcf7f2fe38a8f2d9229c211747539f98`;
`rehearsal.json`, `preservation.json`, `public-smoke.json`, `public-browser.json`,
`discord-test.json`, package/build/publication logs. API export `api-c0dd561/`.
Installer/package evidence under `%LOCALAPPDATA%/PokeApp-releases/0.26.4/`.

## Exact next action — resume, do not restart

1. Check Railway incident resolution and actual deployments before any retry.
   Intended target remains PokeApp V2 / production / pokeapp-api only. Deploy the
   verified committed API export once when accepted; reconcile unknown outcomes.
   No new webhook test, credential change or Launcher/web redeployment is needed.
2. Reconcile history and fresh preservation baseline. If backup exceeds the two-hour
   gate, recapture and rehearse the same 067/068 against that archive. Keep the guard.
   Use the existing `phase30_backup_rehearsal` and `phase30_apply_migrations` tools.
3. Verify new API healthy, then apply 067 and 068 once in order. New API accepts
   old setup SQL while waiting. Confirm history 60/head 068 and worker health;
   never replay historical Discord events or an uncertain send.
4. Verify public reads/auth, Admin availability and source classification without
   cancelling Prueba. Compare preservation again. Observe real automatic Y sync
   only through normal owner use; never invent an accepted import or rewards.
5. Update this handoff with actual final outcomes and commit/push. No new packet.

Protected guide and unrelated untracked files remain untouched. Explicit staging
only. Production writes by this task are limited to authorized deployment assets,
the secret configuration and one Discord message; no database/business mutation.
