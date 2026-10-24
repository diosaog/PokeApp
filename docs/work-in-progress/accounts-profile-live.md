# Accounts and profiles - live handoff

## Authorized clean production release — 2026-10-24

**IN PROGRESS. Entry d5e83993846d3ce3f08c3a429171c1e5a0f786e1.** Owner now
authorizes deleting all V2 test accounts/seasons/business data, including old
Anto, after verified backup. This supersedes preservation/deployment restrictions
in the historical local closure below. No account names confer privileges.

Pinned targets verified: Supabase `uwleqeuzsveqlugugzba` / Pokeapp 2.0;
Railway project `f5c4666a-508f-4e5a-8aae-a54581814f29`, production,
service `9a78e086-c927-471f-8bb9-befe62c77de7`; existing Cloudflare account/Worker.
Remote migration head049,41 records;050–053 still unapplied at this checkpoint.

Private backup in `%LOCALAPPDATA%/PokeApp-migration-evidence/accounts-release/20261024/`:
`pre-reset-v2-postgres.dump`, SHA256
`2459888ab860f61079e2365f79803a81c2e99311d2fdef3054496fb53180b624`.
All105 tables restore exactly on disposable PostgreSQL, including Auth/Shadow.
Four Storage objects,524732 bytes, backed up and restored to unique disposable
keys, downloaded/hash-verified and removed; original Storage metadata unchanged.
No source reset yet. No Shadow Storage dependency found.

Private `reviewed-reset-public.sql` uses one explicit52-table DELETE statement,
exact baseline preconditions and a transaction; no TRUNCATE, disabled triggers,
schema/permission changes or foreign-key bypass. Rehearsal empties test data and
preserves all53 other tables. `app_settings` and62 `shop_items` retained;
divisions/config versions/promotions are season-scoped test rows, not global
reference catalogs. Their original values remain in the verified backup.
Actual49 backup upgrades through053 successfully after rehearsal cleanup.

Private bootstrap tool `tools/account_admin_bootstrap.py` renders SQL only;
postgres operator, independently verified exact new trainer/Auth IDs, complete
v2 registration, zero prior admins, one auditable receipt. Four concurrent exact
replays produce one promotion; wrong Auth/disabled/second operation and browser/
service-role execution denied. `tools/validate_account_release.py` reproduces
the isolated backup/reset/bootstrap proof without remote access.

New optional `POKEAPP_REGISTRATION_BOOTSTRAP_HASH` adds a private initial-registration
token in addition to the ordinary invitation. It never grants admin; raw token/PIN
remain in memory in the UI. Keep this gate until owner-created Anto is independently
verified and promoted. Public Launcher download pinned separately to0.20.0 so
deploying the web cannot accidentally publish the private0.22.0-rc.3 candidate.
Fresh focused20 Python,5 React,2 Worker,2 Edge desktop/mobile checks PASS;
OpenAPI/build/dry-run, targeted Ruff, formatting/syntax/diff PASS. Prior suites
retained. PostgreSQL rehearsal clusters stopped; no owner files touched.

Next: push validated source; quiesce old API; fresh baseline check; execute exact
reset and scoped Storage/Auth deletion; apply missing050–053 once; configure v2
only policy/keys and disable direct Auth signup; deploy API/web and real disposable
acceptance. Stop at owner manual registration, never create their PIN/account.
Reconcile unknown remote outcomes before retry. Do not open general registration
or claim global completion before owner Admin acceptance.

## Historical local closure (superseded operational authorization)

2026-10-24. **P1-P4 and SEC-PIN-01 DONE LOCAL. NOT DEPLOYED.**
Real-user renewal/production old-pepper retirement: **NOT EXECUTED**.
Entry `0908a33be1ed1baa1df8e5443a1cd87290f79e4f`, fetched main/origin0/0,
no other active agent. Application `1b8db579822ea3470568bc0bd3f6f007c1d83722` pushed.
Prior P4/foundation retained; no restart or remote audit.
[Report](../accounts-profile-report.md), [evidence](../accounts-profile-acceptance-evidence.json).

## Implemented and validated

Existing login now exposes registration only when privately configured/enabled.
The invitation moved from a source constant to private server configuration;
no real invitation in current source/browser/evidence. Earlier Git history remains.
Existing form/profile/Admin flows reused; no automatic season/economy/role grant.
Operator-authorized renewal is available even with profiles OFF. No HTTP grant
issuance, no reset based solely on a potentially compromised old PIN/session.

New053 extends existing PIN/registration journals with versions, expiry and bound
Auth identity; three private RLS tables hold policy/versions/hashed renewal grants.
Default runtime selects VersionedAccountService; no legacy fallback without full
new config. PIN intent HMAC + session block are atomic before Auth. Single claim,
verify/revoke/finish recovery; unknown outcomes never blindly repeat writes.
SQL/API cutoff and monotonic credentials, unchanged UUID/history, stable throttle
key plus active old counters. Old unversioned credential RPCs fail closed.

Fresh PASS:50 focused Python/static checks,12 React,4 Edge desktop/mobile journeys,
real FastAPI/PG with synthetic Auth/object transport. Final PG runner evidence
sec-pin-http-final.json: interruption/replay/concurrency/renewal/cutoff/RLS/rates;
053 ordered/bootstrap parity15858 identical lines,54 prior public tables preserved;
reset preserves Shadow. Test databases dropped, owned clusters stopped.
Build/OpenAPI/Ruff/format/syntax/diff PASS. Existing bundle-size warning nonfatal.
Browser APIs are fixtures; HTTP/PG is separate real application/SQL proof.
18 previous keyring tests and unaffected P1-P4/enrollment retained, not rerun.
Private evidence: %LOCALAPPDATA%/PokeApp-migration-evidence/accounts/20261024/.

## Next exact action - controlled acceptance, not automatic deployment

See the report's ordered rollout procedure. Requires owner authorization:
independent identity-verification/token-delivery policy and UTC cutoff/window;
fresh real bindings/pending-intent/baseline checks; drain old credential writes;
coordinated050-053, policy row and complete private keyring (feature OFF initially).
Set Supabase direct signup OFF before PokeApp registration; prove hosted Admin
provisioning, global signout, Storage and acceptance. Do not change providers/keys
blindly. Renew existing identities through operator grants; reconcile all pending
operations and sessions before old-secret removal. Keep throttle key, wait bounded
48h old-counter window. Unknown Auth outcomes stay blocked for operator resolution.

Production and real users, saves, economy, history, V1/Shadow, public Launcher and
security keys untouched. Real-user migration remains pending; no claim that the
old pepper was retired. No other phase starts. Unrelated untracked files/security
documents and protected guide excluded. Final docs commit carries this handoff;
obtain exact HEAD from Git, not a self-referential document hash.

## Retained P1–P3 execution record

Entry main/origin `2b77b62d2a7fd8d0f1b6e01f4ac2d0c8e51b4b82`, fetched 0/0,
clean tracked tree, five unrelated untracked files preserved. Previous Phase22E
work is committed/pushed and finished; no active child agent or Git lock. Phase22
remains PARTIAL only for deferred emulator/platform/durability/release gates.
Its private candidate and recovery evidence remain valid; no safety defect opened.
The new owner instruction authorizes this separate account/profile packet.

Scope: P1 registration/auth → validated commit → P2 personal profile/photo/PIN →
validated commit → P3 admin accounts → P4 UI/integration. Existing trainer UUID,
PIN derivation, Supabase Auth and competitive history remain authoritative.
Registration never enrolls a season. Unknown provisioning fails closed.

Remote migrations, real accounts/Storage mutations and deployments are explicitly
NOT AUTHORIZED. Additive SQL will be validated on disposable local PostgreSQL.
Public access code verification stays server-side. Credential values are never
recorded in evidence. New account-management deployment will default disabled.

P1 adds service-only migration050: reserved trainer/Auth UUIDs, keyed request
digest, disabled pending accounts, compare-and-complete, persistent atomic rate
windows. Auth creation uses the supported admin UUID and private app metadata;
read-by-ID reconciliation precedes any retry. No name-based identity linking.
Completed receipt replay cannot re-enable a disabled account. Existing PIN
derivation/login remains; names normalize to the existing ASCII slug contract.
New feature flag defaults OFF. Browser trainer writes are revoked; reads retained.

P1 validation:13 registration tests,29 Auth regressions,10 API authentication tests
PASS. PostgreSQL17.11: four concurrent reservation/replay calls, four completions,
same-name/body conflicts, rollback, disabled replay,10 permission denials and
eight competing throttle attempts PASS. No season/economy rows. Fresh bootstrap
through050 succeeded. Database dropped, cluster stopped, logs retained privately:
`%LOCALAPPDATA%/PokeApp-migration-evidence/accounts/20261023/p1-pg.json`.
The first Windows harness captured inherited server pipes and stalled before SQL;
corrected file-backed logging, stopped owned cluster, final run PASS. No product
failure. Supabase Auth uses local doubles; hosted signup-disabled configuration
and real Auth transport remain explicit release checks, never a claimed remote PASS.

P1 commit `ee9d425` is pushed. P2 adds migration051: profile revision/CAS and
receipts, normalized display-name uniqueness (including legacy names different
from their slugs), private portrait bucket with restrictive browser write denial,
PIN intents and immediate API/RLS session guards. Images decode/re-encode to
bounded JPEG without metadata. Rename/photo never change trainer/Auth IDs.
PIN changes authenticate current credentials, permit only ONE outbound password
update attempt, reconcile new credentials, revoke Auth sessions and raise the JWT
issuance floor. Exact interrupted-intent recovery cannot originate a new change.
If interruption precedes the Auth write and no new credential can be proved,
the account stays blocked for operator reconciliation; no stale password replay.
The UI retains only the opaque operation key across reload, never PINs.

P2 tests:10 Python service/API,5 React editor and real PostgreSQL profile/PIN/
Storage/RLS gates PASS, including four concurrent claims (one winner), concurrent
profile replay, stale/duplicate/foreign portrait rejection and preserved membership.
Display-name/legacy-slug collision regression PASS. Fake Auth/object transport
remain explicitly local doubles; real Auth/global signout is a remote release gate.
Migration/bootstrap051 local only. DB dropped/cluster stopped; `p2-pg.json` next to
P1 evidence. Editor is ready; P4 wires navigation and account-only profiles.

P2 commit `6e66c63` is pushed. P3 adds migration052 and admin API/UI: paginated
accounts, CAS/idempotent disable/re-enable with session guards, explicit target
PIN reset through the same durable intent, no role editor/delete/name linking.
Self-disable/reset bypass is denied. Existing draft-only season enrollment remains
authoritative; late enrollment is denied rather than inventing division/history.
Five new Admin API tests, three Admin React tests plus five invalidated PIN-form
regressions PASS. Real PG: four status retries, preserved identity/membership,
stale/nonadmin/self/late-enrollment denials, pending PIN cannot be bypassed PASS.
The first harness expected only two rows despite baseline seed trainers; corrected
to check exact fixture inclusion and private-field omission. Product unchanged.
Local052 database dropped/cluster stopped; `p3-pg.json` retained.

Next: P4 register/login/navigation, public account profiles without membership,
portrait integration, affected browser tests and final local build/parity. No
Phase22/23 or Launcher work. No production effects.
