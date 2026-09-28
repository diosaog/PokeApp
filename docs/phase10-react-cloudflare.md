# Phase 10 - React frontend and Cloudflare delivery contract

Authorized 2026-09-28 after verified Phase 9 DONE at `ee7ff53`.
Current execution: [live handoff](work-in-progress/phase10-live-handoff.md).

## Scope

Build a real Spanish React/TypeScript frontend: Home, League, Battle/Team Preview,
trainers, private PC, shop, Hall, Cup, trials, season administration and a simple
Launcher/save page. Preserve Streamlit/V1 as reference/fallback; no cutover or
Phase 11. Dark premium visual identity, section accents, restrained motion,
keyboard/focus/dialog support and real desktop/laptop/tablet/mobile layouts.

React requests existing typed FastAPI mutations. Add only missing bounded typed
reads through application/repository boundaries; never access Supabase tables from
the browser. No new SQL expected. Official standings and teams come from frozen
backend facts, not client recomputation. Unavailable data is explicit, never seeded
as real product data. Test fixtures are restricted to tests/local validation.

## Implementation boundaries

- React + Vite + TypeScript, React Router, TanStack Query. Exact dependencies and
  lockfile. Feature components, reusable small UI primitives and typed API client.
- Existing PIN/Supabase identity through FastAPI; memory-only access/refresh tokens
  initially. Refresh coalesced, private query cache cleared on logout/expiry. No
  service key or PIN persistence. Backend verifies every permission.
- Centralized requests/errors. Existing required idempotency keys and CAS revisions
  preserved; no silent stale-revision retry. 401/403/409/422/5xx have explicit UI.
  Disable duplicate submits and keep uncertain-outcome retries on the same key/body.
- Cup uses 8L format/side/member contracts. Hall handles nullable champion trainer
  and both doubles members; no unadapted legacy single-champion DTO.
- CORS is an explicit configured origin allowlist; no wildcard credentials.
  Existing /health remains liveness; deployment verification must check API config
  and authenticated data, not treat liveness as database readiness.
- No existing Cloudflare/React/Railway deployment configuration found at entry.
  Choose Cloudflare Workers static assets with SPA routing; FastAPI origin stays
  configurable and hosting-independent. Build/local delivery validation precedes
  any remote deployment. Never invent credentials, account, domain or deployed API.
- Launcher 9 has no remote heartbeat, download installer or cloud ingestion.
  UI explains availability honestly; no fake connected/sync state or download URL.

## Flows and completion

Implement functioning vertical slices, including login, season selection, next
match/team lock, official League reads, private Pokemon details within React,
purchases, Cup/Hall reads and admin commands with confirmations. Extend remaining
judicial/competition flows through the approved APIs; do not invent business rules.
Empty/loading/error/forbidden/conflict states apply to every feature.

DONE requires connected principal pages and critical mutations, focused client/
component/API tests, representative browser E2E and render inspection at multiple
breakpoints, production build, Cloudflare delivery-boundary validation, appropriate
backend regression, docs and Git push. Remote deploy status must be stated exactly;
missing credentials are not a deployment PASS. No final audio/polish, schema for
visual convenience, physical save writes, V1 migration or Phase 11.
