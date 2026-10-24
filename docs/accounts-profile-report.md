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

SEC-PIN-01 is separate and must follow this closure. P4 still uses the existing
pepper; it does not claim that secret has been retired. Keep the existing security
documentation intact. No legacy-key/signing-key operations, real users, saves,
economy, V1/Shadow, Railway, Cloudflare or production schema were changed.

Focused commit carries this report and source; derive its exact HEAD from Git.
Unrelated security documents, repository-map files, ZIP and protected guide stay
outside staging. Global completion estimate **85–90%** remains a judgment, not a
measured metric; private release/emulator and security migration gates remain.
