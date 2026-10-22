# Accounts and profiles — live handoff

2026-10-23. **P1–P3 IMPLEMENTED / LOCAL PASS; P4 INTEGRATION NEXT. LOCAL ONLY.**
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
