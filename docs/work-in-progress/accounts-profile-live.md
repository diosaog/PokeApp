# Accounts and profiles - live handoff

2026-10-24. **ACCOUNTS & PROFILES DONE GLOBAL. REGISTRATION ACTIVE.**
Application source `912908179c310630c0d10145969e1013b5dcbad6` pushed before deployment.
Release entry `d5e83993846d3ce3f08c3a429171c1e5a0f786e1`; preparation `cbe8acf`.
[Release report](../accounts-profile-report.md), [evidence](../accounts-release-evidence.json).

## Current state — initial administrator and general registration verified

Entry HEAD `91639eda01bd55677fa3ca05a9b683c7c8e16d23`, main/origin aligned before
this documentation closure. The owner confirmed that Anto signs in and sees
Administración. Exact trainer `32ec4e97-bf04-4a28-a68d-88c2194f4b65` and Auth
user `3246e081-5fa4-4edd-bf15-233746a43edf` match the completed v2 registration,
server provisioning HMAC and private authorization. Name alone was not used.
There is one Anto trainer/Auth identity and one administrator; no ambiguity.

`tools/account_admin_bootstrap.py` executed once for those exact identities with
the independent owner-verification reference. One private bootstrap receipt and
one administrator exist. PIN/password, UUIDs and owner sessions are preserved.
Real production `/v1/me` returns200 with `is_admin=true`; `/v1/admin/accounts`
returns200 with that one Anto account. A private Admin-generated verification
session was used without requesting/changing the PIN or sending email; only that
temporary session was revoked afterwards. No replacement account was created.

The initial authorization is consumed/invalidated and remains absent. The ordinary
invitation is configured again in Railway; its value is never logged or documented.
The bootstrap hash remains empty. Configuration deployment
`b91ecd9f-c341-467e-860d-df417d59b01a` is SUCCESS, same application source,
health200. Capabilities report registration ON, renewal ON, bootstrap not required.
The initial-token route is therefore unavailable and cannot be reused. Direct
Supabase signup remains OFF.
Temporary token/hash material was removed from the private DPAPI bundle and
`Anto-alta-inicial.txt` now contains only a consumed notice. The ordinary invitation
is retained privately for a later authorized opening. The one-use SQL receipt
prevents another initial promotion; no public promotion route or temporary SQL
function exists.

Direct Supabase signup remains OFF, v2 credential controls remain active, old
pepper absent and migration count45 unchanged. No reset, migration, broad test
matrix, Cloudflare/V1/Shadow/Launcher or competitive-data operation was repeated.
Private evidence: `anto-admin-final.json`, `anto-admin-bootstrap-result.json`,
`anto-authority-probe-result.json` and `anto-registration-close-result.json` in
the release evidence directory below.

The owner-approved disposable registration proof used Auth and the backend with
the private invitation: registration, PIN login, `/v1/me`, self profile and
no-season membership all passed. The new trainer was not Admin. Its exact trainer,
Auth, credential, registration and session data were removed afterwards; counts
returned to the pre-test state and Anto remained the only admin. No economy,
season, Storage, V1, Shadow, Launcher or save data was touched.

**FINAL STATE:** registration is ACTIVE for normal trainers; the invitation is
mandatory; the initial authorization is disabled; Anto is a functional Admin;
new accounts have no season membership or Admin role. Account management, PIN,
session, RLS and rate-limit controls remain active. The web, Railway and Cloudflare
are healthy. Accounts & Profiles is **DONE GLOBAL**. Stop here; do not start another
package.

## Completed remote units — DO NOT REPEAT

Owner explicitly authorized removing all V2 test accounts/business data, including
old Anto. Backup BEFORE reset:105 PostgreSQL/Auth/Storage/Shadow tables restored
with exact hashes;4 actual Storage objects (524732 bytes) privately captured and
round-trip restored under disposable keys with exact cleanup. PostgreSQL archive
SHA256 `2459888ab860f61079e2365f79803a81c2e99311d2fdef3054496fb53180b624`.
Private evidence/root: `%LOCALAPPDATA%/PokeApp-migration-evidence/accounts-release/20261024/`.
Folder access restricted to owner/SYSTEM; new key material is DPAPI-protected.
`pre-reset-v2-postgres.dump`, Storage manifest/bytes and restore scripts retained.

Old Railway deployment c90bccc2-553e-42e5-95c8-86eedf63d045 removed before reset.
CLI down rejected the sleeping deployment; live health/state were reconciled,
then explicit ID removal succeeded. Old API did not operate after053.
One atomic explicit52-table DELETE, with exact baseline preconditions, removed
competitive test state. No TRUNCATE, trigger/FK bypass or schema/grant reset.
Old Auth identity and4 backed-up Storage objects deleted through Admin/Storage.
Divisions/configuration versions/promotions were season-scoped test data; global
settings2 and shop catalog62 remain. Shadow15 tables/135 rows remain identical.
V1/local original saves/Launcher installs untouched.

050=20261024120248;051=20261024120251;052=20261024120253;
053=20261024120256. Each applied once;45 records,41 prior records identical.
Private v2/intent/throttle keys + invitation configured; v1 pepper REMOVED.
Legacy cutoff `2026-10-24T00:00:00Z`; no v1 account/session/intent remains.
Supabase direct signup OFF; Admin provisioning proved. Existing modern Supabase
keys unchanged. All8 new private account tables enforce RLS/browser denial.
Advisor24ERROR/5WARN/40INFO: one additional WARN is authenticated execution of
read-only SECURITY DEFINER `account_session_allowed`, required by session RLS;
it returns eligibility only, does not elevate or modify accounts. No new ERROR.
Only3 old relation grants changed, as050 deliberately revokes trainer/view writes.

Railway `3d03e4eb-62a1-414b-9cb4-e1f4af7d6f39` SUCCESS; /health200;
image `sha256:565c8affc85931ac8a6fb58f1a95a17e2bafdfe5bba90d463f9cb41b6c9ac5b7`.
280 committed inputs. Earlier8b8f36ee image built but startup demanded old pepper;
9129081 fixes the entry-point guard to require complete v2 configuration. Four
new startup tests pass; no retired secret restored. Final Linux parser smoke PASS.
Cloudflare deployment `4ad95457-bc53-4e0d-8830-9482ce3795a6`, version
`8330afcf-e94c-4135-858d-5ae60cff1704`,100%, correct API and byte-identical assets.
Public Launcher pinned independently to0.20.0, unchanged bytes/ETag; no R2 writes.
Production physical writes remain disabled; no Phase22/23 work.

## Historical release acceptance — before owner registration

24 focused Python,5 React,2 Worker and2 local Edge cases PASS. Real services:
26 FastAPI HTTP checks plus direct-signup and5 private REST/elevation denials;
actual provisioning/login/refresh/PIN/global revoke/disabled guards, rename,
portrait upload/read, stable identity and zero membership/economy PASS.
Real Edge desktop1440/mobile390 registers from login, logs in, opens/edits the
no-season profile and logs out;11 API responses, no interception/page errors/5xx.
Registration/profile captures reviewed.8 public infrastructure checks PASS.
OpenAPI/build/dry-run, targeted lint/format/syntax/diff pass. Prior full suites
retained. Disposable PostgreSQL clusters stopped, browser process ended.

Harness-only corrections: Supabase uses numeric `code` plus `error_code`; use
`signup_disabled` from the latter. Browser waits for DOM/product controls, not
network idle; corrected a private-script encoding error in Spanish selectors.
No repeated registration after an unknown outcome: initial browser failures
preceded registration and were reconciled before retry.

Both acceptance accounts/Auth identities and their one photo removed by exact
UUID/key. At that cleanup, trainers/Auth users/sessions/refresh/Storage objects all0;
credentials/registrations/PIN intents/commands/grants/session guards all0.
Opaque v2 security rate counters and the credential policy remain intentionally.
All52 old public test tables empty; catalog/settings/Shadow preserved. Migrations
remained45; no admin promotion had run remotely. No owner account/PIN invented.

## Historical owner-registration instructions — completed and superseded above

Registration remains controlled by a private initial token in addition to the
normal invitation. `POKEAPP_REGISTRATION_BOOTSTRAP_HASH` stores only its hash.
The field is **Autorización de alta inicial**; the token grants registration only,
never Admin. Owner instructions/token are in the private `Anto-alta-inicial.txt`
inside the evidence folder. Never print it, the invitation or any PIN in logs/Git.

1. Owner opens production web, chooses Crear cuenta, name Anto, their own new PIN,
   known invitation, and the private initial authorization. No personal email.
2. STOP here until owner confirms creation through the existing owner channel.
   Do not repeat reset/deployment. Reconcile exact new trainer/Auth IDs, complete
   v2 registration, creation time and controlled enrollment with that independent
   owner confirmation/local-token delivery. Name/PIN/session alone are insufficient.
3. Render/review `tools/account_admin_bootstrap.py` for only those exact UUIDs,
   fresh operation UUID, independent verification reference and release-time lower
   bound. Execute privately as postgres once; verify journal receipt and Admin role.
   Tool has no HTTP route, requires zero existing admins and complete v2 binding;
   exact concurrent replay is idempotent. Local backup rehearsal proved denials.
4. Owner accepts Admin panel/trainer management. Verify other accounts remain
   ordinary. Then remove the initial-registration hash in a controlled configuration
   rollout (retain invitation), verify normal invitation-only registration, and
   archive/restrict temporary authorization. No automatic first-user/name privilege.
5. Only then close GLOBAL. No admin/enrollment acceptance is claimed before owner.

Historical authorization/readiness statements below are superseded by this release.

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
