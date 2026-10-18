# Phase 19 — Sun/Moon execution

Entry 2026-10-18: main/origin `7617315640936b6efa7abaf6d5397bf04a5e23f4`, 0/0,
tracked tree clean. Phase18 DONE. Remote entry remains migration045
`20261018105158`, 37 records. Railway `2253b885-dc35-43b4-8b93-773fd628656f`
SUCCESS and Cloudflare `411aeb3d-a68a-4d8c-8327-22430a97ba95`, both app source
`e7833440f0c77579a82a9f00a030ab6cdd27619c`.

**STATUS: PHASE19 DONE.** The implementation checkpoint below is historical;
final delivery supersedes its pending steps.

Implemented locally: explicit SAV7SM/SN/MN only; 32 boxes; independent EC;
Alolan/native form types; bounded SM species/moves/items/abilities; original-byte
MemeCrypto signature/checksum-table verification before PKHeX clears its cloned
buffer. Gen6/7 progression and competitive identity remain unsupported/unknown.
Forward046 extends the existing service-only atomic registration, no tables or
data rewrite. Spanish catalog through SM, game labels and Launcher0.19.0 prepared.

Real publicly contributed gameplay saves downloaded privately and parsed:
SN Twitch Plays Pokemon (331 occupied positions), MN TheWhiteDevil27 (68).
Provenance, caveats, exact hashes: `tests/fixtures/phase19-public-saves.json`.
No source modification, production import or independent legality attestation.
Upstream constructed SM fixture is not substituted for this evidence.

Current evidence: bounded native X/Y + ORAS + SM checks PASS; Python SM6,
ORAS5, XY9 PASS; affected React41 PASS. PostgreSQL/real-import, browser,
packaged Launcher and final release gates in progress. First PG attempt stopped
on a harness-only Unicode separator expectation and dropped its databases;
corrected run is recorded separately. Native first attempt encountered an
incomplete temporary .NET8 runtime; .NET9 roll-forward passed. Packaged parser
will use its own pinned complete .NET8 runtime.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase19/20261018`.
Disposable local PostgreSQL uses the retained isolated cluster
`%TEMP%/pokeapp-phase18-pg`, bound to127.0.0.1:55468. The Phase19 runner owns only
its randomly suffixed validation databases and drops them. Stop cluster on closure.

Next: finish local meaningful gates; commit/push before any migration/deployment;
fresh remote baseline; apply046 once; compatible backend, Launcher and web;
read-only public verification/preservation and concise closure. No Phase20.

## Local release checkpoint

All local meaningful gates now PASS: native102 checks; Python SM8/ORAS5/XY9
and schema15; React41; Edge4 desktop/mobile journeys with visual review. Real
PostgreSQL full-chain/bootstrap parity through046, synthetic six-game import
proof and real SN/MN contributor imports; exact54-table restoration. Concurrency,
replay, current-save protection, ownership, rollback, browser RPC denial,
no identity/reward/lock synthesis and offline cache pass. Launcher0.19.0 audit
and packaged parser/core read both public saves without cloud connectivity.
Web build/dry-run and affected web formatting, Python compile/targeted Ruff,
Launcher JS syntax and diff pass. Existing Launcher files retain their prior
formatting style; whole-file Prettier is not a newly passed gate.

Production build initially lacked VITE_API_BASE_URL; final build explicitly uses
the existing Railway API. Packaged smoke initially sampled transient SYNCING;
final smoke waits for READY plus OFFLINE and passes. These were harness/setup
issues. No product test failure was hidden.

Fresh pre-write baseline:59 tables,37 migrations, unchanged private inbox.
Next: commit/push source,046 exactly once, backend with Linux native SM smoke,
installer0.19.0 hosting, web, public checks, preservation and cleanup.

## Final delivery — 2026-10-18

Application HEAD `e29cb05c6a0c1965a7253c7b4169d84edbfa5f3d`, pushed before all
remote writes.046 applied once as `20261018112548`;38 migration records, prior37
identical. Railway `fa6ef08e-cabf-485f-ba17-936aa5802bab` SUCCESS with this source
and262 committed inputs. Linux native checks and final production-runtime SM
smoke pass. Cloudflare `c46c2f7b-1621-4102-9b88-aa74ae1ef77c`, version
`5547e5e6-2fec-454b-b580-5d8fe66f1046`,100%, same source.

Launcher0.19.0 new R2 key only; package and public GET SHA-256
`5b3c783a138b53a9f2b0fe172ce5a8b8ab4df8b954db5f58dc4c6a102fb1460e`,159086505 bytes.
12 public checks PASS;2 Worker tests PASS. Hosted positive import NOT RUN,
owner data preserved. All59 scoped tables including Auth/Storage identical;
stable owner/inbox/security identical. Advisor24 ERROR/5 WARN/171 INFO unchanged.
No V1/Shadow/Streamlit mutation, no physical writes.

Disposable Phase19 databases absent; cluster stopped; no5173/55468 listener.
Private evidence and audited installer retained. No destructive cleanup required.
Final Git is the documentation closure commit carrying this record; obtain its
exact hash from Git rather than a self-referential hash. Explicit staging only,
protected and unrelated files untouched.

[Report](../phase19-sun-moon-report.md), [evidence](../phase19-sun-moon-evidence.json).
**Remaining blockers: none. NEXT: Antonio acceptance. STOP before Phase20.**
