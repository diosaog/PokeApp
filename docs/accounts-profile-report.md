# Accounts and profiles — controlled production activation

2026-10-24. **ACCOUNTS & PROFILES DONE GLOBAL. REGISTRATION ACTIVE.**
Application `912908179c310630c0d10145969e1013b5dcbad6`; documentation HEAD is the
subsequent Git commit. [Live continuation](work-in-progress/accounts-profile-live.md),
[release evidence](accounts-release-evidence.json).

The owner authorized a clean start. Verified private backups restore all105
PostgreSQL/Auth/Storage/Shadow tables exactly and all4 Storage objects (524732
bytes). The active V2 test trainers, seasons, results, economy, saves, snapshots
and old Anto/Auth were then removed. Cleanup used52 explicit DELETE targets and
exact preconditions; no schema/grant/trigger reset or TRUNCATE. Global settings2,
shop catalog62 and Shadow15 tables/135 rows preserved. V1, original local saves
and Launcher installations were untouched. Backups remain private and recoverable.

050–053 applied once:20261024120248/251/253/256 respectively. History now45 records;
all41 previous records unchanged. Direct Supabase signup is disabled. New private
v2 password/intent/throttle keys are active; old PIN pepper removed from Railway.
There are no surviving v1 credentials, old sessions or old credential operations.
No Supabase API/signing keys were rotated. Eight account tables deny browser access.
Advisor has24ERROR/5WARN/40INFO; added WARN concerns the intentional read-only
SECURITY DEFINER session predicate used by RLS, not a mutation/elevation capability.

Initial Railway release **3d03e4eb-62a1-414b-9cb4-e1f4af7d6f39 SUCCESS**, health200.
Cloudflare deployment **4ad95457-bc53-4e0d-8830-9482ce3795a6**, version
**8330afcf-e94c-4135-858d-5ae60cff1704**,100%, correct API and matching build bytes.
The first image compiled but an old startup guard required the retired v1 pepper;
corrected and tested in9129081. No credential downgrade was used. Public Launcher
stays0.20.0 with identical download bytes; physical writes remain disabled.

Fresh affected validation:24 Python,5 React,2 Worker,2 local browser cases;
real backup/reset/bootstrap PostgreSQL proof;26 real API checks, direct-signup
and5 RLS/private/elevation denials; real desktop/mobile browser registration,
login/no-season profile/logout with11 API responses and no interception/errors.
Auth provisioning, refresh, PIN change/global revocation, disabled sessions and
portrait Storage are real hosted proofs.8 public infrastructure checks pass.
Build/OpenAPI/targeted lint/format/syntax/diff pass. Previous unaffected suites
were retained. Private harness error-field, encoding and navigation waits were
corrected; no corresponding product defect or false PASS was hidden.

Two disposable acceptance accounts and their portrait were removed by exact IDs.
After that cleanup, trainers/Auth users/sessions/refresh/Storage objects were all0. Credential,
registration, PIN, command and grant journals contain no test identities.
V2 rate-limit security counters and the rollout policy remain intentionally.

**Initial Anto activation is complete.** The owner manually registered and
explicitly authorized promotion. Exact trainer `32ec4e97-bf04-4a28-a68d-88c2194f4b65`
and Auth `3246e081-5fa4-4edd-bf15-233746a43edf` were verified against the completed
v2 registration, creation time, provisioning HMAC and private authorization;
the name was not sufficient. `tools/account_admin_bootstrap.py` produced one
audited private receipt. There is one trainer, one Auth user and one admin.
PIN/password and owner sessions are unchanged; no duplicate identity was created.

Real `/v1/me` returns200/is_admin=true and `/v1/admin/accounts` returns200 for Anto.
A temporary private verification session was revoked locally after the proof;
no owner PIN was requested or changed. Health200. The initial token is invalidated,
its private handoff replaced by a consumed notice and its DPAPI material removed.
The ordinary invitation is configured in Railway and remains mandatory; its value
is never logged or documented. The initial-token hash is empty and the temporary
authorization is retired. Configuration-only Railway deployment
**b91ecd9f-c341-467e-860d-df417d59b01a SUCCESS** uses unchanged source and health200.
Capabilities report registration ON, renewal ON and bootstrap not required. Direct
Supabase signup remains disabled; v2 keys and45 migration records are unchanged.

The owner-approved disposable real registration then passed: new account creation,
PIN login, `/v1/me`, self profile and no-season membership. The account was not
Admin and its exact Auth/trainer/credential/registration/session data was deleted
afterward. Counts returned to the pre-test state; Anto remained the sole admin.
Cloudflare stayed on the existing healthy release. No migration/reset, V1, Shadow,
Launcher, save, economy or historical matrix was touched.

**FINAL:** registration is ACTIVE for normal trainers; invitation required;
initial authorization disabled; Anto ADMIN FUNCTIONAL; new trainers NORMAL with
no season membership. Auth, Storage, PIN, sessions, RLS and rate limits remain
protected. Accounts & Profiles: **DONE GLOBAL**. Stop; do not start another packet.
Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/accounts-release/20261024/`.

---

# Historical local acceptance before the production release

2026-10-24. **Historical local checkpoint at d5e8399; superseded by the release above.**
Real-user renewal and production pepper retirement: **NOT EXECUTED**.
Entry `0908a33be1ed1baa1df8e5443a1cd87290f79e4f`, main/origin aligned.
Previous P4 `24a87e45aac6372b2f39f05ae942f8d728872c79` retained.
Final application source `1b8db579822ea3470568bc0bd3f6f007c1d83722`, committed and pushed.
[Live handoff](work-in-progress/accounts-profile-live.md),
[sanitized evidence](accounts-profile-acceptance-evidence.json).

## Registration, profiles and administration

P4's existing form is reused. Login shows **¿Todavía no tienes cuenta? / Crear
cuenta** on desktop/mobile when registration is enabled, with return to login.
An incorrect invitation is rejected server-side. The approved shared invitation
now comes only from private `POKEAPP_REGISTRATION_ACCESS_CODE`; current source
constants and browser bundle do not contain it. Earlier Git history is not
rewritten. Tests use fictional invitations. Missing configuration disables
registration; account management still defaults OFF.

Registration reserves one trainer/Auth UUID pair and creates a v2 credential,
without season membership, coins, inventory or admin privileges. Identical
retries recover the same account; conflicts fail closed. A trainer can log in
without a season, edit their own name/photo/PIN and retain identity/history.
Existing image normalization, private Storage, signed URLs, scoped CSP and
revision checks remain. Profile bodies reject economic/admin fields. Rival
editing is unavailable and rejected by the backend.

Admin list, disable/re-enable and PIN reset remain integrated. A privileged reset
now additionally needs a one-use authorization issued by a trusted operator after
independent identity verification. An old PIN or admin session alone cannot
issue it. Season enrollment uses the existing controls and unchanged economics;
its previous evidence is retained, not represented as newly executed.

## SEC-PIN-01

New additive **053_versioned_account_credentials** extends the existing journals
and adds three private RLS tables: versions/reset state, bounded rollout policy
and hashed renewal grants. No PIN, password, pepper or raw grant is stored in SQL.
Existing linked v1 accounts keep UUID/Auth ID/roles/history. Credential versions
cannot decrease; the chosen SQL deadline cannot extend.

The default API container uses `VersionedAccountService` for login, registration,
PIN changes, renewal and admin reset. SQL metadata chooses exactly one derivation;
no try-both-key fallback. V1 is bounded by SQL and configuration (stricter wins).
V2 password, journal HMAC and throttle keys are separate. API, refresh and RLS deny
expired v1/reset-required/disabled/unlinked/blocked sessions even with profiles
OFF. Missing derivation keys do not remove session guards. This new source does
not expose legacy login without the complete keyring.

Renewal works without a session and with profiles OFF, using a grant bound to the
exact trainer/Auth ID, expiry and operation. There is no HTTP grant-issuance route.
This also permits the first administrator to renew independently of an old admin
session. Actual verification and secure token delivery are operator procedures to
approve; no email/phone or identity-verification policy is invented.

Preparation atomically binds the intent and blocks sessions before Auth effects.
One claimant may update Auth. Retry verifies the new credential, globally revokes
sessions and finishes the original operation, without blindly repeating a password
write. Completed replay has no new effect. Expired, conflicting or unprovable
outcomes remain blocked for operator reconciliation. The browser retains only the
operation UUID; PINs and grant tokens remain in memory and must be re-entered after
reload. Old pending intents are neither re-signed nor silently abandoned.

Old active rate windows are counted during transition. The new throttle key
survives password-key changes; early v1 removal with unexpired old counters fails
closed. Unversioned registration/PIN RPCs are retired by053. No replacement account,
credential guessing, retroactive reward or business mutation is introduced.

## Fresh validation and retained evidence

- **50 Python/static checks PASS:**13 registration,8 session guards,15 schema,
  3 runtime/configuration,5 Admin API and6 affected Auth bridge checks.
- **12 React tests PASS**, registration/profile/PIN/Admin. **4 Edge journeys PASS**:
  desktop1440/mobile390 registration, wrong invitation, return/login, no-season
  profile, name/photo/PIN and re-login; accounts OFF with renewal; existing rival
  privacy and confirmed Admin disable. Screenshots reviewed, no overflow/errors.
- Real disposable **PostgreSQL17.11 + synthetic Auth PASS**: concurrent/replayed
  registration, lost provisioning response, four PIN claims with one winner,
  lost atomic-prepare response, interrupted Auth write, failed global revoke,
  lost finish response, expiry/replay, independently authorized legacy renewal,
  old-PIN-only denial, disabled/refresh/UI OFF, API/RLS cutoff, counter transition,
  rollback, private grants and stable IDs/roles/history.
- Real FastAPI HTTP + PostgreSQL journey PASS: wrong/correct invitation, exact
  registration replay, login, self name/photo/PIN, old-session/refresh denial,
  re-login, forbidden fields/Admin access, authorized admin reset and disable.
  Auth and photo transport are in-memory substitutes.
- Upgrade/bootstrap through053: **15,858 identical schema/grant/ownership lines**;
  **54 prior public business tables preserved**. Reset removes disposable account
  objects while preserving Shadow. Owned databases dropped and clusters stopped.
- OpenAPI, TypeScript/Vite, focused Ruff, formatting, syntax and diff PASS.
  Existing nonfatal bundle-size warning remains. No Docker/deployment build.

Browser APIs are intercepted fixtures; the separate HTTP/PG gate exercises the
real application and SQL. Neither proves hosted Auth/Storage transport. Prior18
keyring tests and unaffected P1–P4/enrollment evidence are retained, not rerun.
No security21, historical full matrix or Launcher test was repeated.

Two initial schema assertions were updated:29 private RLS declarations and checks
for forbidden credential columns instead of matching legitimate intent-kind
strings. A syntax-check command had PowerShell quoting damage; corrected input
passed. Intent preparation was strengthened before final proof to bind its HMAC
atomically. Only affected gates were repeated. Final PG evidence:
`sec-pin-http-final.json`, under private
`%LOCALAPPDATA%/PokeApp-migration-evidence/accounts/20261024/`.
Runner: `tools/validate_sec_pin_local.py`. Earlier052 proof is historical.

## Exact rollout gates — not authorized or executed here

1. Approve independent identity verification/token delivery, UTC cutoff and
   operational window. Inventory real account bindings and pending journals;
   reconcile v1 intents before transition. Do not infer account counts or an
   unknown Auth outcome. Unprovable changes stay blocked for operator resolution.
2. Fresh remote preservation/collision/security baseline; quiesce old credential
   mutations and drain in-flight calls. Apply050–053 in a coordinated window.
   Old backends cannot originate PIN requests after053. No credential downgrade
   or restoration of unsafe legacy APIs as a rollback shortcut.
3. Configure private `POKEAPP_REGISTRATION_ACCESS_CODE`,
   `POKEAPP_AUTH_PIN_PEPPER_V2`, `POKEAPP_ACCOUNT_INTENT_KEY_V2`,
   `POKEAPP_ACCOUNT_THROTTLE_KEY`, `POKEAPP_AUTH_PIN_V1_DEADLINE` (explicit UTC).
   Keep old `POKEAPP_AUTH_PIN_PEPPER` only during bounded transition. Use distinct
   strong random keys, never values in CLI arguments/Git/logs/browser. Insert the
   same approved cutoff into `account_credential_policy`; it deliberately starts
   empty and access fails closed until configured. Keep the feature flag OFF
   initially. This source needs053 and a complete keyring together.
4. Supabase Auth → Sign In / Providers: **Allow new users to sign up OFF**
   (`disable_signup=true`) before registration activation; keep email/password
   sign-in, do not enable anonymous signup. Direct signup otherwise creates
   unlinked Auth identities without the invitation. PokeApp denies them, but
   denial does not replace closing signup. See official
   [configuration](https://supabase.com/docs/guides/auth/general-configuration)
   and existing server-only
   [Admin creation](https://supabase.com/docs/reference/python/auth-admin-createuser).
   Prove direct-signup denial and Admin provisioning in approved acceptance.
   No live setting was read or changed in this task.
5. Approve real Auth provisioning/signout, Storage, registration/login/refresh,
   RLS and owner acceptance before feature activation. Operator renewal grants:
   generate at least32 cryptographically random bytes, store only SHA-256 via
   service-only `sec_pin_authorize_renewal`, exact trainer/Auth IDs, verification
   reference and expiry ≤24h. Deliver the raw token privately. Redeem through
   `/v1/auth/pin-renewal`; no new identity or email is required.
6. Reconcile pending v2 operations and sessions. After cutoff, unrenewed accounts
   remain blocked but can renew with an operator grant. Wait at least the bounded
   48h old-counter window from rollout before removing v1; keep the throttle key.
   Prove renewed login/refresh and old-secret denial before retiring live pepper.

Production, real accounts, saves/economy/history, V1/Shadow, security keys and public
Launcher are unchanged. Unrelated files/security documents remain outside staging.
The final documentation commit carries this report; obtain exact HEAD from Git.

**Local implementation complete; real-user migration/public activation pending.**
Next: controlled account/credential acceptance and deployment after authorization.
Global PokeApp + Launcher estimate **85–90%**, subjective and unchanged; emulator,
release and live security gates remain. **STOP: no new functional phase.**
