# Phase27C — unified Launcher and release readiness

2026-10-26. **PHASE27C DONE LOCAL. No Phase28 started.**
Entry main `c3835b6eaf9f91250be1b7ec003e4a7b51c2081b` was four commits ahead of
origin, with no divergence. All interrupted work was preserved. The three web
paths reported modified had no content difference after Git's line-ending
normalization; explicit index refresh added no web changes. The eight unrelated
untracked files and the auxiliary release worktree remain untouched.
Validation/build-preparation commit: `228569d06857c7a999d915b0f7ea225cc49f6efe`.
The subsequent documentation commit carries this report; obtain final HEAD from
Git. [Evidence](phase27c-evidence.json), [live record](work-in-progress/phase25-live.md).

## Production already deployed — verified, not redeployed

Railway API source `501a39944096e858ff2214e3fb778adc79108f21`, branch
`release/27c-api` based on9129081, contains the minimal unlimited-inventory read.
Deployment `22d96f80-9d99-498f-b3f6-d90b3ec39da9`, image
`sha256:1ac8a52800959b9ec0faee7d1f02df2737a0cb8e840abcd011883a738aae087c`
remains current. CLI initially reported SLEEPING, with the service instance
RUNNING; fresh health returned200. No rebuild, restart or config change.

Cloudflare version `4a8fffed-a912-47d8-aa7e-dfaea7b7bce3` serves100%, frontend
98de687: Arena, infinite inventory and desktop routes. Both public JS/CSS bytes
match the retained production build. **12 read-only checks PASS:** health,
88-route OpenAPI with optional `InventoryRead.unlimited_items` and
`UnlimitedItemRead`, HTML/assets/API origin,401 on protected reads, exact CORS
and foreign-origin denial, stable installer HEAD. No unexpected5xx. Public
Launcher0.20.0 retained (159087398 bytes); no R2 upload/download mutation.

**Public inventory∞: PARTIAL hosted acceptance.** The deployed contract/assets
and synthetic authenticated UI pass; no fresh real-account inventory/login or
owner mutation was used. This does not claim a real account's inventory read.
Production054–061 remain NOT APPLIED under the retained operational checkpoint;
this resume issued no Supabase SQL and makes no fresh remote-history claim.
Production was updated in the preceding session, not left at the old27B state.

## Correct SQL upgrade/retry proof

The interrupted validator assumed arbitrary replay of055 after061 must be a
no-op. The actual object diff is only
`public.commit_pokemon_identity_v038(jsonb)`: replay restores055's definition,
removing the provenance checks added by058. No historical SQL was edited.

**28 checks PASS**, real disposable PostgreSQL17:001–053 plus representative
trainers/season/coins/purchases, then054–061 in sequence. All64 prior public/
Storage table fingerprints remain identical; no columns retyped/removed,
function signatures retired or grants revoked. Seven new tables force RLS and
deny anon/authenticated access. Schema, ownership and grants equal a separate
fresh001–061 bootstrap (digest in evidence).

Immediate replay at each migration's own version is an exact no-op for055/060;
054/056/057/058/059/061 refuse atomically without schema or data residue. The
historical055-after061 diagnostic runs inside a rollback-only transaction and
proves restoration of the latest function and all rows. It is evidence against
blind historical replay, not authorization to rerun an applied migration.
Both disposable databases were dropped and clusters stopped.

## Private packaged Launcher acceptance

Existing **0.24.0-rc.2 build/audit PASS retained**, no redundant rebuild.
**24 new packaged checks PASS** against the real unpacked private executable,
real core and official deployed web assets, with an isolated profile. After
the initial real signed-out page, authenticated browser APIs are intercepted
synthetic fixtures; no real PIN/account/save is used.

Verified all five native panels, inventory∞ links, return to web, logout,
30 rapid transitions with latest-close winning, route allowlist, offline fallback
and online return, separate web/native sessions, web without Node/preload/IPC,
official origin and ignored packaged origin override. Public physical capability
remains OFF. No JavaScript errors. Login, connection and offline captures reviewed.
Eight packaged UI/security files exactly match source c3835b6, including the race
fix. The initial acceptance ran all assertions but its CDP-close promise did not
settle; the bounded harness cleanup was corrected and final report is PASS.

Installer: `PokeApp-Launcher-Private-Setup.exe`, **159254332 bytes**,
SHA256 **27760cc8cedb8609c2cd8a482a35dd88d5230cf2ded6ce2aed67856b30891df3**.
Location: `%LOCALAPPDATA%/PokeApp-builds/0.24.0-rc.2-private-27c/release/`.
Authenticode freshly reports **NotSigned**. Private channel; updater unconfigured;
no public distribution or owner installation. This is unpacked packaged execution,
not a fresh rc.2 installer/upgrade certification. Previous Win11 installed-update
7/7 evidence is retained only for its tested versions.

## Restricted verifier and Docker

**8 new startup/security checks PASS** with fictional CLI settings and a real
disposable restricted PG login: default-off, transfer flag cannot enable master,
missing/insecure settings fail closed without secret output, item/transfer runner
idle and repeat, exactly two permitted security-definer RPCs, direct table access
and internal projection denied, privileged database identity refused. No artifact
or native access occurs for an empty queue. The initial harness referred to a
nonexistent test column; a valid zero-row DELETE proves denial in the final run.
Owned database dropped, cluster stopped. Prior27A16/16 integrated PG/native/API/
two-Launcher jobs, retry/reconciliation and8 unit/storage checks remain valid,
unchanged-source evidence; they were not rerun.

One build-context defect corrected: root `.dockerignore` excluded the worker
requirements and runner COPY inputs. The worker now has its own minimal
Dockerfile-specific ignore file, following the
[Docker context contract](https://docs.docker.com/build/concepts/context/#dockerignore-files).
Build guards require an immutable base digest,061-capable application modules and
default-off runner smoke. The capability guard was executed locally with a
fictional pinned reference; it rejects a mutable tag. **Docker CLI/engine absent:
image build and Linux container run PENDING**, not PASS.

The current public501a399 image lacks `transfer_verification.py` and is NOT a
suitable worker base. Build the full validated main application/parser source
as a separate private base, pin its registry digest, then follow the updated
[worker procedure](robbery-backend.md#private-verifier-procedure).
Hosted TLS/login roles, real private Storage authorization/transport and worker
deployment remain PENDING. A generic Supabase service-role/secret key is not
evidence of bucket-scoped least privilege; qualify a dedicated storage identity
before hosted acceptance. No worker or privileged credentials were deployed.

## Release checklist and remaining authorization

**6 current-artifact manifest checks PASS:** existing signer/verifier binds the
actual rc.2 SHA512/size; same-version no-op, downgrade/channel/tamper rejection,
and unsigned stable-manifest refusal. The private test envelope uses an ephemeral
test key and `updates.invalid`; the private key was destroyed. It is NOT a release
manifest or feed, no shipped Launcher trusts that key, and no production key was
created. Public test key/envelope retained privately for reproducibility.

- Release key custody, pinned public key, private HTTPS feed and actual signed
  release manifest: PENDING. Keep private/stable channels separate. Stable additionally
  needs a valid Authenticode certificate and verified signed installer hash.
- Install/rollback: use a fresh private profile, preserve the existing profile,
  journal and backups, close the emulator and reconcile pending operations first.
  Do not bypass downgrade protection; rollback needs a vetted compatible build
  delivered under an approved newer signed version, with recovery proof.
- Backup policy unchanged: daily/save restore point,30 days; transactional backup
  before writes; pending/failed/uncertain and last-known-good copies preserved.
  No existing backups were purged.
- Windows10, fresh rc.2 clean-install/upgrade, real two-player Lime3DS, hosted
  verifier, actual revive certification and power-loss evidence remain PENDING.
  PKHeX Gen7 signing limitation and additional foreign-OT support remain bounded
  failures; no bypass, certification or scope expansion claimed.
- Before a next packet: owner authorizes its exact scope; Docker-capable host
  builds the061 private base/worker, then restricted hosted acceptance with fresh
  baselines and explicit migration/worker authorization. These are not automatic
  Phase28 tasks. Public Launcher and physical writes need separate release gates.

Retained, not rerun: Node17/17; classic Electron28/28; unified dev18/18; offline2/2;
Vitest161/161; affected browser33/33. Prior full Python1162 run had three inherited
failures (account capability default, admin route count,0.2s timing); this closure
does not report that historical suite as green. Fresh targeted Ruff, format,
Python compile, JS syntax, package integrity and diff checks pass. No application,
parser, SQL, backend credentials or owner data were changed in this resume.

Evidence root: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase27c/`.
No new test listener remains on9337/55491–55493; test profiles/logs are retained.
No production migrations, V1/Shadow, real saves/economy or public physical writes.
**Next: return to Antonio. No next phase started.**
