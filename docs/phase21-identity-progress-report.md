# Phase 21 - Trusted Gen6/7 identity and native progression

Closed 2026-10-20 Europe/Madrid. **STATUS: PHASE 21 DONE.**
Trusted identity and native progress reads are deployed. Gen6/7 rewards remain
gated as required; this closure does not authorize them.
[Final evidence](phase21-identity-progress-evidence.json),
[live handoff](work-in-progress/phase21-identity-progress-live.md).

Phase 21 adds conservative, season-scoped trusted identity evidence for Generation 6/7 saves and additive native progression evidence for X/Y, Omega Ruby/Alpha Sapphire, Sun/Moon and Ultra Sun/Ultra Moon. Existing Generation 3-5 reader and receipt semantics remain compatible. No physical save bytes are written and no owner competitive data is changed.

## Identity and progression

Identity schema 2 is only accepted for the native Gen6/7 path. Trainer scope, immutable candidate evidence, PID/encryption-context collisions, eggs, trade or incomplete origin facts, ambiguous clones and unsafe reappearances fail closed as `UNKNOWN`/ambiguous. Identity IDs are deterministic and scoped to the save, trainer and season; later visible edits do not rewrite immutable evidence.

Native progression is structured and game-specific. Gen6 exposes Kalos (X/Y)
or Hoenn (OR/AS) badges plus independent League/Hall-of-Fame/champion facts where
supported. Gen7 exposes island challenge progress and independent champion
facts; it does not fabricate gym badges. Missing evidence stays UNKNOWN,
distinct from observed zero/false. Native facts do not prove legitimate gameplay,
a unique physical Pokémon, or a complete battle-entry transition.

## Rewards and history

Gen6/7 progression rewards remain blocked (`pending_validation` or `pending_policy`) until approved transition evidence and policy exist. No backfill or speculative award was performed. Existing Gen3-5 rewards are unchanged. Frozen history, Team Locks, owner seasons, economy and save data are preserved.

## API, SQL and web

Forward migrations `048_trusted_gen67_identity.sql` and
`049_native_progress_read.sql` extend existing registration/identity functions
and add a native read helper. No historical row rewrite or schema reset occurs.
The service-only native projection uses a strict allowlist, fixed search paths
and fail-closed shape/game checks. The authenticated progress read presents
badge/island/champion facts without private identity evidence; React does not
rank, authorize or award.

## Validation

- Full Python: **916 PASS**, including 19 pre-existing untracked map tests.
- Focused Phase 21 identity: **16 PASS**; progress/API: **30 PASS**.
- Compatibility suites: 13 + 9 + 5 + 8 + 3 + 11 PASS.
- Schema/contract: **15 PASS**.
- Native synthetic checks: **360 assertions PASS** and PostgreSQL native gate PASS.
- Legacy identity SQL/security gate: **19 PASS**.
- Fresh migration/bootstrap builds: **54 public / 15 private tables**, identical.
- React progress: **7 PASS**; affected browser: **2 PASS**.
- Vite build, formatting and targeted Ruff syntax gates PASS.
- Disposable PostgreSQL databases were dropped and the local cluster stopped.

Evidence for native fixtures is retained privately under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase21/20261018`; public JSON fixtures contain only sanitized metadata and hashes. They do not replace authentic proof of every legitimate gameplay transition.

These valid gates were retained on final resume, not rerun. The final production
TypeScript/Vite build and Wrangler dry-run passed. Railway's successful Linux
image build also executed the eight-game native progression/runtime smoke.

## Verified delivery and preservation

Entry HEAD was `1c5e1a0e46af18c02e6739c9670efa12ef5b5ff7`.
Application `5260eac53b555840df5dc11fc40b8e1078328782` was committed and pushed
before remote writes. A fresh 59-table baseline, owner-stable credential hashes,
migration history and Advisor baseline preceded application:

- 048 applied once as **20261019231747**.
- 049 applied once as **20261019231750**.
- Final history: **41 records**, all original 39 unchanged.
- Railway **319be126-91fd-43d7-98c3-dd8556941757 SUCCESS**, exported from
  265 committed inputs. Deployment image digest
  `sha256:b36235100b16e070a879602fa111616b92da0317eb106ea7d8b1c3acc3de45b0`.
- Cloudflare deployment **bc36d34b-42b1-490b-91fb-bb1817af5e6d**, version
  **5d6ceff7-03f2-4c4d-ac43-c1a63c137007**, 100%.

Final public smoke: **26 checks PASS**, zero unexpected 5xx. API health,
missing/invalid JWT denial, private PC/progress/collection denial, CORS,
SPA routes, security headers, production API configuration and exact deployed
JS/CSS/HTML bytes passed. Positive hosted PIN login and owner save ingestion
were not repeated; authenticated privacy/ingestion proof remains local.
No PIN was requested and no hosted business mutation or fixture was used.

**59/59 baseline table count/hash records are identical**, including their
Auth and Storage scope. Owner-stable identity/credential hashes also match.
Results, economy, saves, Team Locks and history in that baseline are preserved.
The retained private-schema security catalog is unchanged; six relevant
functions have their expected fixed search paths, invoker security, postgres
ownership, service-only execution and denied browser/PUBLIC execution.
Advisor remains **24 ERROR / 5 WARN / 171 INFO**, with zero added or removed
ERROR/WARN. This is the retained baseline scope, not a new whole-database audit.

The initial final-comparison harness incorrectly expected an empty search path
for every function. It was corrected to compare each function's declared fixed
path; the same captured catalog passed without a product or database change.
No migrations or deployments were repeated on final resume.

Private final evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase21/20261020`.
The documented disposable database cleanup is retained; no postgres process
was present at final resume. The 265-file API export remains a retained local
artifact. Launcher 0.20.0, R2 artifacts, V1, Shadow data and original saves were
not changed by this delivery.

## Final boundary

No blocker remains for the delivered identity/native-read scope. Reward
activation still needs sufficient transition evidence/policy and stays disabled.
No new Launcher package, physical save writes or Phase 22 work was performed.
Documentation closure is the subsequent commit containing this report and
evidence; obtain its exact HEAD from Git. Explicit staging only; unrelated
untracked files and the protected guide remain untouched.

**NEXT: Antonio acceptance of the deployed read behavior. STOP before Phase 22.**
