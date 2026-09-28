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

Commit/push before deploying. Export a new temporary directory with:

```powershell
.venv-api\Scripts\python.exe -m tools.build_api_deploy_bundle --output <new-temporary-directory>
railway up <new-temporary-directory> --path-as-root --project f5c4666a-508f-4e5a-8aae-a54581814f29 --service 9a78e086-c927-471f-8bb9-befe62c77de7 --environment production --detach
```

The exporter reads committed Python API sources and three explicit build files;
it excludes documentation, protected/untracked files, saves, credentials, local
builds and tests. A source/hash manifest accompanies the upload. Do not use
`railway up` on the whole workspace or `--no-gitignore`.

Build React with `VITE_API_BASE_URL` set to the allocated HTTPS backend, then use
the [web runbook](../web/README.md). Verify public liveness, rejected/allowed CORS,
real login/refresh/reads/mutations and browser flows before claiming deployment
ready. Fixture runs require fresh public/Auth/Storage hashes, migration history,
Advisor inventory and independently checked cleanup under the master protocol.

References: [Railway IaC](https://docs.railway.com/infrastructure-as-code),
[FastAPI hosting](https://docs.railway.com/guides/fastapi).
