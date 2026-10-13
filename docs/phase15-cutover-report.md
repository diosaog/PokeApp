# Phase 15 — production cutover closure

Closed 2026-10-13 Europe/Madrid. **STATUS: PHASE 15 DONE. CUTOVER: COMPLETE.**
**PRODUCTION AUTHORITY: V2. PUBLIC DUAL AUTHORITY: NONE.**
[Evidence](phase15-cutover-evidence.json),
[execution record](work-in-progress/phase15-cutover-live.md).

## Entry and scope

15C resumed from `ef044175ecc1043877f709be7cc4101acbc3cd4b`, main/origin 0/0,
clean tracked tree. 15A established readiness and retained rollback artifacts.
15B closed branch B after the owner made the legacy Streamlit app private;
the existing V2 deployments already served the intended production path.

The owner replaced the blocked desktop-browser method with CLI/headless proof.
This execution used HTTP, read-only database queries and isolated headless Edge.
No physical desktop control, product/configuration change, deployment, migration,
business mutation or fixture was needed. Historical suites were not rerun.

## Final authority and retained artifacts

| Authority/resource | Verified state |
|---|---|
| Public web | Cloudflare React: `https://pokeapp-web.pokeapp-v2.workers.dev` |
| Application | Railway FastAPI: `https://pokeapp-api-production.up.railway.app` |
| Competitive data | Supabase V2 `uwleqeuzsveqlugugzba`, ACTIVE_HEALTHY |
| Cloudflare | `pokeapp-web`, version `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, 100%; source `eb4e402891cbaa02e0999229874ac3003e016ae0` |
| Railway | `PokeApp V2 / pokeapp-api`, deployment `9b75a24f-ca5e-474b-9c3c-555625cceb14`, SUCCESS/RUNNING; source `d05e28e01639d146976300dbcd7bb16baa92c9d1` |
| V2 migrations | 34 records; 042 once as `20261011160629`; unchanged |
| Legacy Streamlit | Private, non-public, non-authoritative; retained |
| V1 | `fdtytpeyfzyssfrsulxd`, ACTIVE_HEALTHY, preserved reference only |
| `v1_shadow` | Private reference only; reconciled, 6 batches, 57 mappings, 135 rows |

Cloudflare build configuration names the exact Railway origin. The verified
owner session has the V2 Auth issuer. Browser traffic uses that API, without a
V1/Streamlit competitive path or direct Supabase business writes. The installed
Kaspersky origin was recorded separately; antivirus protection was not changed.

Anonymous Streamlit `/` and `/_stcore/stream` returned 303 to Streamlit hosting
authentication in all three final observation cycles. The owner-confirmed app
was not deleted. This is a hosting privacy gate, not a claim that allowlisted
private legacy sessions cannot write. They remain outside public authority.

## Fresh production proof

Headless Edge 155.0.4283.45 passed **35 rendered states: 20 desktop at 1440 px
and 15 mobile at 390 px**. The final main run recorded **44 API responses,
all 200**, with no interception, mocks, page errors, console errors or failed
requests. Navigation, useful content and document overflow were checked at
every state. Ten screenshots were reviewed as files.

- Existing private PIN login, enabled owner/admin identity, current season and
  logout passed. Logout cleared local/session storage. No credential was printed
  or committed.
- GENERAL's eight rows match authoritative points, coins and unknown-death
  values. Only J1 closed and J2 current/scheduled are offered. A focused mobile
  follow-up compared all eight J1 rows with frozen revision 1, and confirmed the
  table scrolls to the deaths column (314 px viewport, 540 px content).
- Own/rival profiles and PC render truthful progress and save absence. Battle
  self/rival selection and spectator mode preserve self/public response types;
  scouting exposes the public projection. Missing Team Locks remain explicit.
- Shop balances and all four categories match responses: 5 Comodines, 32 Bayas,
  19 Competitivos and 5 Crianza. Inventory loads without fabricating purchases.
- Admin reads current rewards **5/12**, protects the active season's name and
  shows an incomplete championship without a finish button. No form was saved.
- Hall and Cup reads load. Hall is empty; no champion or historical team is
  fabricated. Existing frozen League history renders independently of live save.

The focused mobile follow-up used six successful API responses and no mutation.
Production currently has no self save, selected current Team Locks, inventory
purchases/targets or Hall entries. Populated versions of those states are not
claimed as fresh positive proof; prior representative evidence remains unchanged.

## Security and preservation

Twelve focused HTTP security checks passed: anonymous/invalid JWT denial on
identity and Admin (401), public scouting projection, rejected private-field
escalation on scouting/Team Preview (422), exact allowed CORS and foreign-origin
preflight denial, authenticated `no-store`, HTTPS/deep SPA, JS/CSS MIME, CSP and
`nosniff`. A post-logout anonymous denial also passed. No separate existing
non-admin session was available; no user or role claim was fabricated for that
case. The owner session is not represented as a non-admin denial test.

The final read-only capture at **10:36:55 UTC** equals the retained 15B baseline
and the 15C entry for migration history, stable owner facts, Shadow and its
security expectations. Across **59 scoped V2 tables, all 55 non-Auth tables are
identical**: owner/manual seasons, memberships, results, economy, locks, history,
reward facts and Storage metadata are preserved. Only `auth.users`, sessions and
refresh-token tables differ. Non-owner Auth hashes equal the retained baseline;
owner identity/credential hashes remain stable.

All **13 V1 table/count/hash records** are unchanged. Shadow's 15 private tables
retain forced RLS, postgres ownership, zero role/table/column/public access and
zero external FKs. This is the retained catalog-expectation comparison, not a new
broad audit. Storage bytes written, remote business writes and fixtures: **zero**.

## Observation and the reproduced 503

**The historical read-503 symptom reproduced; it was not fixed here.** At
10:29:37 UTC the initial browser attempt received two 503s on `overview` and
`pc`. Railway HTTP/deployment logs confirm application responses, without proxy
errors or a service restart. The precise internal cause remains **UNKNOWN**.
The existing client retry recovered PC. A harness assertion still using its
five-second default ended that attempt before overview recovery finished;
Railway recorded that cancelled request as 499. Both failures remain in evidence.

Only the harness assertion deadline was corrected. A second harness attempt
had five successful API responses but an incorrect exact season-label selector;
that selector was corrected without changing its expected season. Product
timeouts, retries and responses were never changed.

The complete final browser proof and focused mobile follow-up passed without
5xx. The bounded final observation, **10:34:34–10:35:19 UTC**, made **24 requests
in three cycles**, including authenticated League/inventory/Hall reads, web,
configuration, health and Streamlit gates. All had expected results, without
repeated or sustained 5xx. This supports closure with the brief reliability
incident explicitly retained; it does not establish a root cause or permanent
fix. No authority, privacy or data-preservation failure was observed.

## Rollback, Git and next action

Rollback was not executed. Retain private Streamlit, V1, Shadow, the current
Cloudflare/Railway artifacts and previous compatible Railway checkpoint
`3845ce2d-6488-43ef-893a-1459c2aed0bb`. The current Railway image digest is in
the evidence. Any later rollback must control traffic/application authority;
never rewind business data, migrations or history, or reopen concurrent public
legacy writes. Closure does not authorize deleting these resources.

Private logs, captures, screenshots, harnesses and a checksum manifest are retained
under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase15/20261013/phase15c-closure/`.
Only this report, sanitized evidence and live handoff enter the documentation
commit. Resolve that commit's exact HEAD from Git; no self-referential hash is
embedded. Explicit staging only; protected and unrelated untracked files remain
untouched.

**PHASE 15 DONE. CUTOVER COMPLETE. ROLLBACK SAFETY PRESERVED.** No remaining
cutover blocker. The reproduced read-503 reliability follow-up remains recorded.
**NEXT ROADMAP: LAUNCHER / CLOUD / SAVE COMPLETION — NOT STARTED.** Installer,
distribution and physical-save work are not implied complete by this cutover.
Stop here; no next-roadmap implementation is authorized by this closure.
