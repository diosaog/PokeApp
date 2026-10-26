# Robbery backend, private verifier and restricted deployment (27A)

Contract and states: [robbery-rules.md](robbery-rules.md). Everything here is
**local only**: no migration applied to production, no worker deployed, public
physical writes disabled.

## Components

| Layer | Piece | Role |
| --- | --- | --- |
| SQL | `api_prepare_transfer` (061) | reservation; early same-title check; one active operation per trainer |
| SQL | `api_transfer_leg` (061) | participant's own leg: before the decision only `get`/`ready`/`cancel` (requester); after it only its own obligation: `ready`, `begin`, `reserve_result`/`queue_result`, `reserve_candidate`/`queue_candidate`; `cancel` → `transfer_adjudicated` |
| SQL | `api_transfer_list` (061) | own legs with `status`, `obligation`, `pair_id`; own plan only after the decision |
| SQL | `transfer_verifier` (061, verifier role only) | `queue`, `plan`, `adjudicate`, `adjudicated_context`, `artifact`, `finish` (proof), `rebase`, `reject_candidate`, `settle_context`, `settle`, `status` |
| SQL | `guard_team_lock_robbery` (trigger) | no team lock while a victim removal is pending or from a party holding another trainer's Pokémon |
| API | `PUT /v1/launcher/seasons/{s}/transfers/{a}/candidate` | the Launcher's current bytes for re-planning (octet-stream, own principal) |
| API | existing transfer routes | request, list, leg get/put, result upload, requester cancel |
| Worker | `TransferVerification` + `run_transfer_step` | plan → adjudicate → (rebase) → verify → settle; every step idempotent |
| Worker | `PrivateTransferStorage` | reads accepted saves, stores immutable `trusted/…` and `transfer-basis/…` bytes |
| Launcher | `LauncherTransfers.obligations/fulfil`, runtime `transfer_fulfil` | mandatory sync; safe engine; uploads result or current bytes |
| Web | inventory transfer cards | decision and per-save delivery shown separately; no veto |

Nothing outside the verifier role can decide, prove or settle: `anon`,
`authenticated` and `service_role` cannot execute `transfer_verifier`,
`transfer_leg_view` or `transfer_obligation`, nor read the transfer tables; the
worker role executes exactly `item_verifier_job` and `transfer_verifier`.

## Migration plan

Real sequence: `001`–`061` (no other migration was added by 26C/26D). Pending
production, in order: `054` item-use authorizations, `055` native identity
evidence scope, `056` item-use verifier transport, `057` two-save reservations,
`058` provenance/finalization, `059` integration reads/queue, `060` party origin,
`061` authoritative adjudication. Each is additive (new tables/columns, `create
or replace`/renamed function versions, triggers); none rewrites history.
`supabase/v2/bootstrap.sql` is regenerated from the 61 files.

Proven on disposable PostgreSQL 17: bootstrap applies; `001–060` then `061`
leaves every existing table's data byte-identical and the schema equal to the
bootstrap dump (69 tables). 061 must be applied **after** 060 and in the same
release as the API/Launcher/worker that speak the 27A states.

## Private verifier procedure

Image: `deploy/Dockerfile.item-verifier` built **from the exact validated API
image digest** (`--build-arg API_IMAGE=…@sha256:…`); adds only `psycopg` and the
runner. Runner: `tools/run_item_use_verifier.py`, one job per invocation, no
listener, logs only outcome codes.

27C build preparation: the base must contain the full061-capable main source;
the current minimal public API release501a399 does **not** contain those modules
and cannot be used. Build/qualify a separate private API/parser image first,
record its exact source and registry digest, without deploying that image.
`deploy/Dockerfile.item-verifier.dockerignore` allows only the worker COPY inputs
and overrides the public API's root ignore file. Docker itself remains untested
on the current host (CLI/engine unavailable).

On an authorized Docker-capable host, with a recorded private base digest:

```text
docker build --file deploy/Dockerfile.item-verifier --build-arg API_IMAGE=<private-base>@sha256:<digest> --tag pokeapp-item-verifier:27c .
docker run --rm --network none pokeapp-item-verifier:27c
```

Expect exactly `DISABLED` and exit0, no listener. Build gates reject mutable
image tags, missing adjudication/rebase/settlement methods and an enabled/broken
default runner. Record the output image digest before any acceptance. An actual
Linux build, non-root inspection and verified-TLS hosted startup are still
required; local Python import and restricted PG proof do not substitute for them.
No secrets belong in build arguments, image layers or those commands.

| Variable | Purpose |
| --- | --- |
| `POKEAPP_ITEM_VERIFIER_ENABLED=true` | master switch (default `false`: prints `DISABLED`) |
| `POKEAPP_ITEM_VERIFIER_DATABASE_URL` | verifier-role DSN, `sslmode=verify-full` mandatory |
| `POKEAPP_ITEM_VERIFIER_STORAGE_ORIGIN` | HTTPS origin of signed artifact URLs |
| `POKEAPP_NATIVE_PARSER_PATH` | native PKHeX companion inside the image |
| `POKEAPP_TRANSFER_VERIFIER_ENABLED=true` | robbery steps (separate switch) |
| `POKEAPP_TRANSFER_STORAGE_URL` / `_KEY` | storage-only credential for `raw-saves` (read accepted saves, write immutable keys) |

Secrets live only in the worker service's secret store; never in the API
environment, the repository, a command line or logs. The database role is the
existing `pokeapp_item_verifier` grant on a login role without table DML (the
adapter refuses to start otherwise).

The table's storage-only privilege is a **release requirement**, not an already
provisioned identity. A generic Supabase service-role/secret key bypassing RLS is
not bucket-scoped. Before hosted approval, demonstrate that the selected dedicated
identity cannot access other buckets/tables or overwrite existing objects; if
that cannot be established, keep hosted activation blocked. Local immutable-key
and lost-response tests establish application behavior, not provider IAM scope.

## Restricted deployment procedure (future hosted acceptance)

Each step needs the owner's explicit go; stop at the first failure.

1. **Database preflight** — read-only: server version, `max(migration)`,
   absence of 054–061 objects, no long transactions, free space.
2. **Pending migrations inventory** — exactly 054–061 in order; checksums of
   the files against this commit.
3. **Backups** — fresh provider backup + logical dump of affected schemas;
   restore tested into an isolated database before applying anything.
4. **API compatibility** — deploy the API that understands 061 states with the
   transfer service still unwired (`transfer_integration=None` → 503).
5. **RLS** — after applying, run the grants/RLS checks (no direct table access
   for `anon`/`authenticated`/`service_role`; forced RLS on transfer tables).
6. **Roles and least privilege** — create the worker login role, grant only
   `pokeapp_item_verifier`; verify the exact executable function allowlist.
7. **Private worker** — build from the API digest; start with
   `POKEAPP_ITEM_VERIFIER_ENABLED=false` (expect `DISABLED`), then enabled with
   transfers off.
8. **Private storage** — `raw-saves` private; storage key limited to that
   bucket; signed URLs ≤ 180 s; immutable uploads (`upsert=false`).
9. **Queue** — scheduler invoking the runner (e.g. every 30–60 s), one
   instance; queue is discovery only, so overlap is safe but unnecessary.
10. **Service identity** — dedicated worker identity distinct from the API;
    secrets rotated independently.
11. **Authentication tests** — two engineering accounts; expired/foreign tokens
    refused on every transfer route.
12. **Authorization tests** — cohort-gated `TransferIntegration` with exactly
    the two engineering trainers; victim cancel refused; outsider refused.
13. **Result verification** — disposable saves: robbery decided with the victim
    offline, robber delivery verified, then victim removal verified.
14. **Reconciliation** — `RECONCILED`, purchase consumed once, ROBADO/BLINDADO,
    entity owner, both accepted saves; repeat the worker: no new effects.
15. **Observability** — worker outcome codes and queue length dashboards;
    alert on `REJECTED`, `BLOCKED_UNCERTAIN`, queue age.
16. **Rollback / containment** — switch off `POKEAPP_TRANSFER_VERIFIER_ENABLED`
    and unwire the API service (decisions already taken stay valid; nothing is
    reverted automatically); restore from step 3 only on data corruption.
17. **Progressive activation gates** — engineering cohort → owner + one tester
    → league; public physical writes remain a separate owner switch.
18. **Owner approval checklist** — signed-off evidence of steps 1–17, Lime3DS
    two-player acceptance, Windows 10 run, Authenticode, update server.
