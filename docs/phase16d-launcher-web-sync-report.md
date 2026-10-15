# Phase 16D - Launcher to web trusted save sync

Closed 2026-10-15. **STATUS: PHASE 16D DONE.**
Launcher to web trusted sync COMPLETE; registered/current V2 save is the single
web authority; local-first PRESERVED; physical save writes NOT STARTED.
[Evidence](phase16d-launcher-web-sync-evidence.json),
[live record](work-in-progress/phase16d-launcher-web-sync-live.md).

## Root cause and implemented flow

The old Launcher sent private, unverified observation DTOs to migration 043's
inbox. Receipt of that DTO did not register a save, while the web correctly read
`save_files`, `parsed_saves` and `season_players.current_save_file_id`.

The Launcher now queues original stable bytes, scoped to API/account/season, and
sends them through verified JWT authentication. The server's isolated PKHeX parser
reads those bytes and validates hash, observation digest, trainer identity and
current-save context. Client DTOs never enter the authoritative write boundary.
The new service-only 044 RPC registers the existing save/parsed-save model,
reconciles supported identity, changes the current pointer and invokes existing
progress reward rules in one database transaction. No second save authority or
inbox promotion was introduced. The native parser is bundled in the API image.

Upgrading from 0.16.1 requires a new explicit synchronization opt-in; the old
private observation setting cannot silently trigger these authoritative effects.
Local parsing, PC browsing and offline use remain independent of the network.

## Idempotency, privacy and web consistency

Original bytes use an immutable deterministic private Storage key. A same-file
replay returns the established receipt, without registering or rewarding again.
CAS prevents a stale intent from overwriting a newer current save. After an
unknown response, the Launcher queries the receipt before retrying the original
request; it retains acceptance separately from successful PC readback. Only a
matching authoritative current save and ready PC produce **Sincronizado**.
Superseded receipts clear that success state; an old replay cannot rewind the save.

Save, Mi PC and the owner's Trainer profile consume the same current save. The
profile's new PC request is self-only. Rival/public views continue to use approved
Team Locks, never the raw live PC. Private identity, IVs/EVs and other private
details remain private. Restrictive Storage policies prevent browser accounts,
including browser admins, from inserting, replacing or deleting trusted raw bytes.

Existing Gen3-5 identity/progress/reward semantics are reused. The local concurrent
four-badge example credits **16 coins exactly once**. No reward, points, closed
snapshot or Team Lock is synthesized from the private inbox. X/Y save and PC
registration work; unsupported X/Y competitive progress/identity stay UNKNOWN.
No physical local save bytes are modified.

## Validation and evidence boundaries

Final Python **844 PASS** (including 19 pre-existing untracked map tests), focused
API/Launcher **26 PASS**, schema **15 PASS**, affected React **12 PASS**, Worker
**2 PASS**, affected Edge **14 PASS**. Compile, targeted Ruff, formatting/diff,
TypeScript/Vite and Wrangler dry-run pass. The initial full Python run found only
two outdated 043 schema expectations; both were updated, and the final full run
passed. The first mock-browser run shared a disposable server; the isolated final
run passed all 14 cases without an application change.

Retained `closure-pg2` proof uses real PostgreSQL, native Gen5/X/Y bytes and real
HTTP/PIN/JWT/application reads: migration/bootstrap parity through 044, exact
54-table restoration, CAS, concurrent/repeated registration, wrong-owner denial,
rollback, no replay rewind, immutable raw policy denial, unknown Gen6 state and
single reward effect. The real Launcher/API/PG/web journey recorded **23 API
responses**, reload/Save/Mi PC/self profile consistency, no rival private-PC
request and no browser errors/interception. External Auth and object transport
are local substitutes; this is not a positive hosted Storage import claim.
The later receipt UI adjustment has focused final tests. Historical matrices
were retained, not represented as fresh runs.

The 0.16.2 package audit and packaged core stdio smoke pass. The Linux-only lock
was corrected after Railway rejected an extra Windows RID; the final Docker image
build compiled and executed the parser smoke successfully. An optional additional
live synthetic-parser diagnostic could not use SSH because no SSH keys existed;
no keys were created and no remote synthetic save was registered.

## Delivery and preservation

Entry `18e05366cf7234bb09a748eb2da9e0bac1e512bf`. Implementation
`0a2732547dbcdc3edaa33a872a518956591825d9` was pushed before 044, applied once as
**20261014164204**. All 35 previous records remain unchanged; remote history now
has **36 records**. Linux packaging/configuration correction
`2959287b769c9b89897450551d78f55a15b51d18` was also pushed before deployment.

Railway **c3e33fd1-a355-4edc-a663-3947288e247d SUCCESS**, 256 committed inputs,
image `sha256:d93f6415a8d050dc24ec67370e382709ce44f36ed5c292c7cae7a48a8746f70a`.
The two earlier NU1004 builds failed without replacing the healthy prior service.
Cloudflare deployment **9468c50c-7a69-45dc-bda4-fe5d4d45cd04**, version
**34cb5721-c205-4ea3-9bd0-d97ffc400127**, 100%, same final source. Only the intended
new R2 key `windows/0.16.2/PokeApp-Launcher-Setup.exe` was uploaded.

Public proof: **13 HTTP checks PASS**, API health/new-route auth denial, exact CORS,
SPA/security headers, correct API build-config, live JS/CSS equal to the local
build, and stable installer GET/HEAD. No unexpected 5xx. Download size **159086018
bytes**, SHA-256 **4c4ddf69ac13a5566a58cffe04401fb7cc3a1c1d7efefe97c0d91561336f9523**.
[Download Launcher 0.16.2](https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download).
No hosted positive owner-season mutation or fixture was used. Hosted login was
not repeated without the owner's PIN; the actual-save acceptance journey is below.

All **59 baseline tables** were compared. **56 are byte-for-byte identical**;
differences are confined to `auth.users`, `auth.sessions`, `auth.refresh_tokens`
activity belonging to the sole owner account. Stable credentials/identity/admin,
business data, results/economy, Team Locks, Storage metadata and the one private
inbox observation remain unchanged. All 36 migration records and the security
catalog are identical after apply. Advisor **24 ERROR / 5 WARN / 171 INFO**;
zero new/removed ERROR/WARN (only observation timestamps excluded). No V1,
Shadow, legacy ingress or unrelated R2 writes were performed.

## Limits, cleanup and manual owner test

Storage upload precedes the database transaction: a failed transaction can leave
an immutable unreferenced private object. It cannot become the current save or
generate competitive effects; accepted source bytes are never deleted to guess
at an unknown outcome. Automatic orphan collection is not part of 16D.
The installer remains unsigned; clean-Windows acceptance and a fresh installation
matrix were not repeated. Numeric Pokemon/item/move labels remain for the next
localization packet.

No 16D test process/listener remains; the runner dropped its disposable databases
and the local cluster is stopped. Evidence is retained privately under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase16d/20261015`; the verified installer
under `%LOCALAPPDATA%/PokeApp-releases/0.16.2`. Automatic approval review rejected
deleting `%TEMP%/pokeapp-phase16d-20261014` with **blocked by policy**. That exact
temporary directory remains for manual cleanup; no bypass/repeated delete was
attempted. The older operator-owned 16C residue remains untouched.

Owner acceptance: download/install **0.16.2**, sign in, select the real save, click
**Sincronizar con PokeApp**, wait for **Sincronizado**, then reload the web and check
**Save -> Mi PC -> own Trainer**. Repeat sync on the unchanged file: it must retain
the same current save without another reward. Local browsing remains available
offline. This explicit synchronization may apply existing approved progression
rewards; merely upgrading does not.

Documentation closure is the subsequent commit carrying this report; use Git for
its exact HEAD. Explicit staging only; protected/unrelated files were not edited
or staged. The final deployment used only the committed API input export.
**NEXT: Spanish localization / user-visible Pokemon data - NOT STARTED. STOP.**
