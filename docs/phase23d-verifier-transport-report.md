# PokeApp — Phase 23D report

2026-10-25. **Verifier and transport: DONE LOCAL. READY FOR RESTRICTED ACCEPTANCE.**
**PHYSICAL CERTIFICATION PENDING; Phase23 PARTIAL / NOT DEPLOYED.**
Entry `cb8cbbc773a4f862dc7144714860ea52963b0d11`, main/origin0/0, clean tracked.
[Evidence](phase23d-verifier-transport-evidence.json),
[operational handoff](work-in-progress/phase23-live.md).

## Independent verification and retention

Authenticated result PUT/GET uses the existing trainer/session guard, an OFF-by-default
flag and explicit trainer allowlist. Original save, current pointer, entity/revision,
claim, purchase and native plan remain server authorities. Submitted bytes, local
receipts and hashes are not proof. Only four supported native sizes are accepted
(maximum483328 bytes); concurrent storage submissions are bounded to two per API
process. No native execution or evidence credential is present in the intake service.

New additive **056_item_use_verifier_transport** reserves one immutable result digest
and private key per existing authorization/claim before upload. It creates one RLS
table, a restricted NOLOGIN verifier role and separate intake/worker functions.
Original bytes stay in existing trusted Storage; results use the same private
`raw-saves` bucket, namespace `item-use/<trainer>/<authorization>/<claim>/<hash>.sav`.
Uploads never upsert/delete. An unknown upload outcome is reconciled against the
existing object's digest. Browser accounts, including admins, cannot read or mutate
that result namespace through Storage policy. Public receipts contain only the
authorization ID, intake state and result digest.

The private worker receives short180-second signed read URLs through its private
SQL job, pinned to the configured HTTPS Storage origin and exact object path.
Redirects, other origins/paths, excessive bytes and hash mismatches fail closed.
Native parsing and exact transformation verification reuse23C unchanged. Three-minute
leases fence workers; proof insertion, authority recheck and VERIFIED transition are
one SQL transaction. The worker cannot directly select/modify business tables or
insert proof. Its sole callable non-trigger public SECURITY DEFINER is
`item_verifier_job(jsonb)`, confirmed against the actual disposable catalog.
The API service role, browser and Launcher cannot execute that issuer function.

Original/result objects and manifests are retained for reconciliation; URLs expire
and are cleared on terminal jobs. No automatic garbage collection or retention
deadline is introduced. Retention protects against application overwrites, not an
operator deleting an object with privileged Storage access. Hosted persistence,
credentials and transport have not been accepted yet.

## Recovery and current status

The engineering Launcher bridge reuses its existing SQLite binding and stable
claim. On restart it checks the native receipt/current file and queries intake
before resending. Expired worker leases can renew signed transport for the same
bytes; they never reapply the physical operation. Parser/worker outages and unknown
SQL outcomes stay retryable. Rejected/expired/conflicting operations consume nothing.
Only the existing completion transaction consumes once after matching private proof.
The new authenticated transport uses existing user JWTs; there is no runtime/IPC
activation and the production mutation registry remains EMPTY.

Additive `physical_state` is computed from current scoped authorization, while
historical receipts retain their original `physical_effect_status` snapshot.
Inventory now gets that state in its existing aggregate response, removing its
separate item-use request. Applied, pending, recovery, blocked, expired, unavailable
and unverified historical states are distinct. Old purchases without an authorization
are never backfilled into applied status; internal shield effects stay internal.
No extra item, currency, entitlement or retrospective effect is generated.

## Validation actually executed

- **106 unique focused Python checks PASS:**25 frontend reads,20 redemption API,
  11 item-use API,15 schema,15 existing verifier/binding,8 Launcher bridge,
  12 transport/security/current-state checks. Passing subsets were retained;
  this is the combined final evidence, not a claim of one106-test invocation.
- **14 React economy tests PASS**; all displayed physical states and no consumption
  controls. OpenAPI/types, TypeScript/Vite, changed-file critical Ruff, full Ruff
  on new Python files, syntax and diff checks PASS. No unrelated browser matrix.
  Existing bundle-size warning is nonfatal. CLI default prints DISABLED.
- Real PostgreSQL17.11 + native parser/writer + real FastAPI + isolated Storage
  contract: **nine main groups and three additional groups PASS**. Covers native
  result, tamper, correct-hash wrong transform, native-valid extra money/IV changes,
  foreign trainer/season/save/claim, expiry, duplicate workers, fencing, upload
  interruption, lost proof acknowledgement, failed proof persistence/rollback,
  current-save change during verification, exact-once completion, immutable history,
  SQL/Storage grants and Launcher restart without another file write.
- Upgrade/bootstrap through056: **16643 identical schema/grant/ownership lines**;
  **64 pre056 public table hashes preserved**. Private-worker catalog audit passes.
  Owned databases dropped, clusters stopped; no55475 listener remains.
- Existing **192 native checks across eight games retained, not rerun**. Production
  native source and23C verification contract are unchanged. A test-only C# command
  generated two independently serialized, native-valid negative artifacts from
  the retained X result; locked build passes. The new integrated positive path
  uses X; the foreign-save negative uses the public Y fixture, never owner's Y.

Auth is synthetic and Storage is isolated/emulated in these gates; SQL, application,
native verification and Windows journal/filesystem paths are real. This does not
prove hosted Auth/Storage or gameplay. No Docker installation was available: the
separate worker image recipe is prepared but **not built or deployed**.

Corrections: a new malformed-receipt KeyError is now a sanitized503; the schema
test now accounts for the private queue. Eight older bridge fixtures lacked23C's
required identity-revision/effect fields; fixtures were corrected, protections
retained. The first negative-transform harness supplied an invalid marking request;
corrected native-valid input is now rejected for its actual wrong effect.
A repository-wide lint attempt found unrelated pre-existing warnings; those files
were not changed. Only scoped checks are claimed above.

## Exact restricted rollout — requires separate owner authorization

1. Capture fresh remote history, collisions, private grants and business baselines.
   Apply committed054/055/056 only in the approved acceptance target/window. No
   migration was applied remotely in23D. Keep physical production capability OFF.
2. Build the API/parser image from this committed source; build
   `deploy/Dockerfile.item-verifier` with `API_IMAGE` pinned to that image digest.
   This separate non-root worker has no public listener. Run
   `tools/run_item_use_verifier.py` repeatedly under a bounded scheduler (one job
   per invocation). Build/startup acceptance remains required, not implied by localPG.
3. Provision a dedicated LOGIN with only membership in `pokeapp_item_verifier`,
   CONNECT to the intended DB and no other grants/ownership/admin/BYPASSRLS/role
   creation. Do not grant that membership to `service_role`, authenticator, anon
   or authenticated. Repeat the catalog privilege assertion before accepting it.
   Functions use fixed search paths and revoked PUBLIC execution, following
   [PostgreSQL guidance](https://www.postgresql.org/docs/current/sql-createfunction.html).
4. Only the worker receives `POKEAPP_ITEM_VERIFIER_DATABASE_URL` with verified TLS
   (`sslmode=verify-full`, trusted CA), `POKEAPP_NATIVE_PARSER_PATH`, exact
   `POKEAPP_ITEM_VERIFIER_STORAGE_ORIGIN`, and explicit
   `POKEAPP_ITEM_VERIFIER_ENABLED=true`. No Supabase service/JWT/signing/PIN key is
   needed there. Never put its credential in API, web, Launcher, arguments or logs.
   Avoid SQL parameter/body logging because jobs carry short-lived signed URLs.
5. The API retains its existing server Storage credential. Enable intake only
   with `POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED=true` and canonical UUIDs in
   `POKEAPP_ITEM_VERIFICATION_TRAINERS` for disposable approved accounts. This
   does not enable physical application. Source/result uploads must remain
   non-upsert, consistent with [Storage policy guidance](https://supabase.com/docs/guides/storage/security/access-control).
6. Prove actual JWT scope/disabled-user denials, private Storage put/read/sign,
   redirect/expiry/renewal, custom-role TLS connection, exactly-once proof and
   authorized completion, lost responses, restricted browser/admin grants and
   preservation. Reconcile the exact disposable acceptance UUIDs/keys before any
   cleanup. Disable intake/worker on failure; retain unknown artifacts/journals,
   never replay writes or consume to guess an outcome.

Proof establishes that the received file is the authorized transformation. A
player-controlled computer can replace it afterward; no continuous-save or emulator
attestation is claimed. Real Azahar/game flush, restart exclusion, platform/crash
and packaging/release gates remain Phase22 requirements. Two-save theft and all
other new item types remain outside23D. **Production UNCHANGED; Phase24 NOT STARTED.**

Implementation and this closure are committed/pushed with explicit paths; exact
final HEAD is supplied by Git, not a self-referential value inside this report.
