# Hosted FastAPI

Railway project `PokeApp V2` (`f5c4666a-508f-4e5a-8aae-a54581814f29`),
service `pokeapp-api` (`9a78e086-c927-471f-8bb9-befe62c77de7`), environment
`production` (`d05ccec3-7a85-4eeb-9b01-c0f8d2111896`). The environment label is
Railway's default; the database is the isolated pinned Supabase V2, not V1.
Railway allocated `https://pokeapp-api-production.up.railway.app`.
Cloudflare account `a8e089ff4da821ed3dbd24701437514c` has registered workers.dev
subdomain `pokeapp-v2`; the frontend Worker name is `pokeapp-web`.
Deployment/validation status belongs in the Phase 10 handoff, not this runbook.

The root Dockerfile installs only API runtime dependencies, runs without root,
and binds `0.0.0.0:$PORT`. Hosted startup refuses missing server configuration.
No migration runs at build/start. API secrets are supplied through Railway's
server variables using stdin; never put their values in commands, Git or bundles.
The initial PIN pepper was generated only after verifying zero provisioned V2
trainers. Preserve it; replacing it would invalidate provisioned PIN credentials.

`.railway/railway.ts` keeps the healthcheck, exact CORS origin and one replica.
Secret values use `preserve()`. Run `npm ci --prefix .railway`, inspect
`railway config plan`, then apply the reviewed changes. Config as Code files
`railway.json`/`railway.toml` are deprecated and not used.
On Windows, put the native Railway executable directory on the child process's
PATH for IaC evaluation: SDK 3.11.0 invokes `railway --version` without a shell,
which cannot run the npm `.cmd` shim. Do not bypass the version check.

PIN throttling is currently in-memory, one process/replica. Proxy headers are
not trusted, so forwarded IP spoofing cannot change its key; clients behind the
edge can share a limit per trainer. Shared durable throttling is needed before
scaling replicas. `/health` is liveness, not a database/auth readiness assertion.

Region: the service runs in **EU West** (one replica), next to Supabase
(`eu-central-1`); it ran in us-west until 2026-10-28, which put an Atlantic
round trip on every request and on every database call. Railway keeps the
region in the service settings (`railway scale eu-west=1 sfo=0 us-west=0`
from a folder linked to the service), not in the uploaded files. App
sleeping stays on.

Commit/push before deploying. Export a new temporary directory with:

```powershell
.venv-api\Scripts\python.exe -m tools.build_api_deploy_bundle --output <new-temporary-directory>
railway up <new-temporary-directory> --path-as-root --project f5c4666a-508f-4e5a-8aae-a54581814f29 --service 9a78e086-c927-471f-8bb9-befe62c77de7 --environment production --detach
```

The exporter reads committed Python API sources and three explicit build files;
it excludes documentation, protected/untracked files, saves, credentials, local
builds and tests. A source/hash manifest accompanies the upload. Do not use
`railway up` on the whole workspace or `--no-gitignore`.

## Hosted verifier (`pokeapp-verifier`)

Second service of the same project (`0564a8f6-7d04-4ea2-ad43-0b293e8edb9e`),
built with `build_api_deploy_bundle --worker`: the API image ending in a loop
that runs `tools/run_item_use_verifier.py` once per turn (item-use artifacts and
server-authoritative robbery steps). It has no listener, so app sleeping can
never wake it: keep every turn shorter than Railway's 5-10 minute idle window.

Since 2026-11-03 its Railway start command overrides the image's `sleep 5`:

```text
/bin/sh -c "while true; do python run_item_use_verifier.py; sleep 60; done"
```

A turn every ~61 s instead of ~7 s cut its billed usage (about 80% of the
project's usage, for an empty queue) from $0.0063 to $0.0007 per hour, measured
on Railway billing for 18:30-19:30 UTC against the two hours before (-89%),
while a queued job is still
leased well inside the 2-minute `RETRY_REQUIRED` and 15-minute authorization
limits of migrations 054/056. Since 085 each turn drains the queue in bounded
passes (plan then adjudicate, verify then settle, up to five item jobs), so a
step no longer waits for another 60 s turn.

Apply or revert only with a new deployment of the service instance, which takes
the current settings. `deploymentRedeploy` of an existing deployment keeps that
deployment's own settings (tried 2026-11-03: the start command did not change).
Rollback procedure, tested on production 2026-11-03 18:25 UTC (Railway GraphQL
`https://backboard.railway.com/graphql/v2`, the owner's CLI token):

1. Unset the override. The value must be the empty string `""`; the API
   silently ignores `startCommand: null` (tried: the 60 s command stayed).

   ```graphql
   mutation { serviceInstanceUpdate(
     environmentId: "d05ccec3-7a85-4eeb-9b01-c0f8d2111896",
     serviceId: "0564a8f6-7d04-4ea2-ad43-0b293e8edb9e",
     input: { startCommand: "" }) }
   ```

2. Deploy the instance with its current settings (no source change; the build
   is a cache hit and the image digest stays the same):

   ```graphql
   mutation { serviceInstanceRedeploy(
     environmentId: "d05ccec3-7a85-4eeb-9b01-c0f8d2111896",
     serviceId: "0564a8f6-7d04-4ea2-ad43-0b293e8edb9e") }
   ```

3. Check: the new deployment is `SUCCESS`, its `meta.serviceManifest.deploy.
   startCommand` is `''`, `meta.imageDigest` is unchanged
   (`sha256:cf64f9b4...`), and its logs show `IDLE` / `TRANSFER []` every
   ~8 s (test result: deployment `849568aa`, 9 turns, median 8.0 s, no error).

To apply the 60 s cadence again, run step 1 with the command above as the
`startCommand` value and repeat steps 2-3 expecting a turn every ~63 s (done the
same day: deployment `2853bbc4`, the current one).

Build React with `VITE_API_BASE_URL` set to the allocated HTTPS backend, then use
the [web runbook](../web/README.md). Verify public liveness, rejected/allowed CORS,
real login/refresh/reads/mutations and browser flows before claiming deployment
ready. Fixture runs require fresh public/Auth/Storage hashes, migration history,
Advisor inventory and independently checked cleanup under the master protocol.

References: [Railway IaC](https://docs.railway.com/infrastructure-as-code),
[FastAPI hosting](https://docs.railway.com/guides/fastapi).
