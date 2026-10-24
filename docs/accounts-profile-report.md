# Accounts and profiles — local integration closure

2026-10-24. **P1 / P2 / P3 / P4 DONE LOCAL. NOT DEPLOYED.**
Continuation entry `1313820d247b82a07e470d1591972aef79744367`, main/origin aligned,
no other active agent. All inherited P4 changes were preserved and integrated.
[Operational handoff](work-in-progress/accounts-profile-live.md).

Registration, login, permanent profiles without season membership, name/photo/PIN
editing, trainer cards and admin account controls are wired into the existing UI.
Registration still requires server validation of the approved access code and
creates no membership, currency or role. Account capability defaults OFF. Admin
can disable/re-enable another account and reset its PIN without knowing the old
one; there is no role editor or identity replacement. Portrait decoding strips
metadata; private Storage uses short signed URLs and scoped image CSP. Unknown
command outcomes keep the same operation; browser recovery persists only its ID.

Session guard checks now also run on login and refresh responses, after verifying
the exact token and its Auth ID. Revoked, disabled, expired, unlinked and mismatched
sessions cannot receive a usable API response. API guards and persistent login
limits remain active with account/profile UI OFF. Infrastructure failure fails
closed. These are existing P2 guard semantics, not the later pepper migration.

New final validation: **8 session tests**, **10 affected Auth API regressions**,
**15 schema/static checks**, **8 React tests**, **3 Edge browser journeys** PASS.
Browser coverage includes desktop1440/mobile390 registration, no-season profile,
rename, photo, PIN/signout, rival collection privacy and confirmed Admin disable.
Desktop/mobile captures reviewed; no overflow or page errors. Auth/Storage in
browser journeys are intercepted fixtures, not hosted integration proof.

One mobile harness race attempted navigation before login completed; waiting for
the app banner fixed it. Only that case was rerun. The first session-test draft
referenced an absent principal field; verification now checks the Auth ID before
principal projection. Final eight tests pass with managed TestClient lifetime.

TypeScript/Vite production build, OpenAPI export, focused Ruff, formatting and
Python syntax/import checks pass. Build needed the explicit public API URL, as
required by its existing guard; no guard was removed. Bundle-size warning remains
nonfatal. No Docker image or deployment was created.

Real PostgreSQL evidence recovered, **retained rather than rerun**: P4 upgrade
through050–052/bootstrap parity,15385 schema/grant/ownership lines,54 pre-existing
public tables preserved, private account RLS/grants, and disposable reset preserving
Shadow. `p4-pg.json` and `reset-pg.json` under
`%LOCALAPPDATA%/PokeApp-migration-evidence/accounts/20261023/` both PASS. The runner
dropped its isolated databases and stopped its cluster. SQL was not changed in
this continuation; static bootstrap equality passes now. P1–P3 PG/Auth/profile
evidence remains recorded in the handoff. No historical or security21 matrix rerun.

Release gates: authorize migrations050–052 and deployment separately, after fresh
remote collision/baseline checks; disable direct Supabase public signup before
enabling registration (last observed `disable_signup=false`); validate actual
Auth provisioning/global signout, Storage and owner acceptance in an approved
environment. An unmapped Auth identity is denied, but that is not a substitute
for disabling direct signup. No live settings were inspected or changed here.

P4 was committed/pushed separately as
`24a87e45aac6372b2f39f05ae942f8d728872c79` before SEC-PIN-01 work. P4 still uses
the existing pepper; it does not claim that secret has been retired. Existing
security documentation remains untouched. No legacy-key/signing-key operations,
real users, saves, economy, V1/Shadow, Railway, Cloudflare or production schema
were changed.

## SEC-PIN-01 — PARTIAL, credential policy foundation only

The subsequent isolated foundation adds typed credential/intent versions, exact
legacy derivation before an explicit UTC cutoff, v2 domain-separated passwords,
separate intent/throttle keys, expiring intent HMACs and secret-redacted errors.
V2 intent hashes bind credential version and expiry. No key trial/fallback occurs;
missing metadata, reset-required state and expired legacy material fail closed.
Changing the password key does not change the new counter identity. This does
**not** migrate P4's existing counter hashes or retire any live credential.

One runtime prerequisite was fixed: default container construction formerly
omitted the account/session guard service entirely when the pepper was absent.
It now retains persisted session checks while disabling PIN-dependent account
mutations. Removing a derivation key cannot itself erase revocation enforcement.
The API does **not** load the new keyring or select versioned credentials yet.
Its explicit configuration loader requires a supplied mapping and cannot change
live configuration merely by importing the module.

**18 new synthetic keyring tests**, **1 configuration/guard test with UI ON/OFF**
and **1 affected legacy missing-pepper configuration regression** PASS. Focused
Ruff, formatting and syntax checks pass. No security21 matrix was repeated, no
SEC SQL was added, and no SEC PostgreSQL/Auth migration proof is claimed. The P4
PG proof above remains valid and cannot be used to certify pepper migration.

Remaining work is a coordinated Auth/SQL migration, substantially larger than a
P4 configuration change. Exact next units, keeping the existing journal:

1. Add a forward migration after052: trusted per-trainer credential version,
   reset-required state, bounded legacy policy and per-registration/PIN-intent
   password/HMAC versions and expiry. Enforce monotonic migration and cutoff in
   API **and RLS**, even with profiles OFF. Do not infer unknown credentials or
   silently re-sign old requests with a new key.
2. Wire version selection into login, registration, change/reset/resume and the
   existing claim/revoke/finish saga. Establish independent verified-identity
   renewal and first-admin bootstrap; possession of a potentially compromised
   PIN/session alone is not sufficient proof. Persist authorization, never PINs.
   Keep UUID/Auth ID/roles and do not create a replacement account.
3. Preserve existing rate counters during the first key transition; test real
   disposable PG plus fake Auth interruption before/after update, failed global
   revoke, concurrent claims, replay after cutoff, disabled users and refresh.
   Retire v1 only after pending intents and sessions are reconciled. An unknown
   Auth update must never cause a blind second password write.

No rollout date or identity-verification process has been chosen on behalf of the
owner. Those operational steps and deployment authorization remain future gates.
**SEC-PIN-01 is not resolved: its versioned policy is not integrated into live
authentication, and the current application still depends on the old pepper.**

Focused commit carries this report and source; derive its exact HEAD from Git.
Unrelated security documents, repository-map files, ZIP and protected guide stay
outside staging. Global completion estimate **85–90%** remains a judgment, not a
measured metric; private release/emulator and security migration gates remain.
