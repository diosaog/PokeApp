# POKEAPP 2.0 — FINAL RELEASE AND PERFORMANCE REPORT

Date: 2026-10-28 (Europe/Madrid). Covers the publication of Phases 30 and 32
and the Phase 33 work. Facts below were checked on the deployed services.

## 1. Answer

**Can we open PokeApp 2.0 now, download the Launcher and use every certified
feature? Yes — for every feature that is certified.** The web, API, database,
Launcher 0.26.1 download and its automatic updates are live and verified
(public acceptance 20/20). **The physical save operations (adding Rare Candy /
Heart Scale to a save, robberies/transfers between saves) are NOT active**,
because they have not passed the in-game and two-save certifications the
project requires (§4). They still answer honestly in the UI («se activará
tras la certificación») instead of pretending to work. So this is not
FINAL DONE for the physical mechanics.

## 2. What is live

| Component | Live version / state | Verified |
| --- | --- | --- |
| Supabase V2 | Migrations 001–064 (history 56 records; 054–064 applied 2026-10-28 00:45 UTC). Catalog identical to a fresh Supabase-shaped 001–064 build; 107 previous tables byte-identical after migrating; 8 new tables force RLS, no browser privilege; Security Advisor: no new ERROR/WARN | Parity, fingerprints, Advisor |
| Railway API | Code `9a9881d`/`d7f9659` (API unchanged since d7f9659), 104 routes, **EU West** (one replica, next to Supabase; was us-west), app sleeping on; incident center ON; item verification and transfer flags OFF | Health, OpenAPI, 401 guards, CORS |
| Cloudflare web | Version `ed858bf1` (web `2fb379b`): one league / Liga A+B, admin and incident center, robbery cancellation, Launcher 0.25 compatibility, Phase 33 optimizations | Hosted checks, browser 1440/390 |
| R2 | `windows/0.26.0/` (bridge), `windows/0.26.1/` (current), older 0.16.1–0.25.0 kept; `updates/stable.json` → 0.26.1 | Full download hashed |
| Launcher | **0.26.1**, SHA-256 `edf8d6479a7bf8187b76e240457eb0399d8eb36a5ac4c029face22366e18d320`, no Authenticode by owner policy (recorded `NotSigned`/`private-distribution`) | Audit, guard, download |
| Updater | Stable channel live, Ed25519 (stable key `639e5440…`, DPAPI-protected) + SHA-512 + downgrade/channel refusals. 0.25.0 → 0.26.0 transition 8/8; 0.26.0 updated itself to 0.26.1 from the hosted feed | Real installers |

Details: [Phase 30](phase30-release-readiness-report.md) (backup, rehearsal
24/24 run twice, plan) and [Phase 32](phase32-final-report.md) (keys,
channel, transition, incident note).

## 3. Performance (measured, before → after)

All web numbers: hosted site, Edge, median of 3 runs, PokeApp's own origins
only (this PC's security software injects its own scripts and slows TLS;
those bytes are excluded, the delay is not removable from client timings).

| Component | Before | After | Change | Method | Regression |
| --- | --- | --- | --- | --- | --- |
| Web initial JS (raw) | 557 KB | 349 KB | −37 % | Vite build | Playwright 114/0 |
| Web first visit, transferred | 264 KB (JS 181 KB) | 199 KB (JS 115 KB) | −25 % (JS −36 %) | `measure_web_performance` | same |
| Web return visit | 6 revalidated assets, 7.9 KB | 0 revalidations, 2.8 KB | assets served from cache | same | same |
| Web return visit LCP (1440) | 184 ms | 140 ms | −24 % | same | same |
| Web first visit, slow 4G LCP | 3.16 s | 2.88 s | −9 % | same, 1.6 Mb/s + 150 ms | same |
| Web mobile CLS (390) | 0.093 | 0 | removed | layout-shift observer | sign-out storage test kept |
| Launcher idle CPU (all processes) | ~16 % of a core | ~1.1 % | −93 % | per-process CPU, 30 s | Vitest 189, Playwright visuals 20/20 |
| Launcher usable window | ~1.0 s (2.8 s cold disk) | unchanged | — | CDP, packaged 0.26.1 | — |
| Launcher memory | ~605 MB working set, 7 processes | unchanged | — | Win32_Process | — |
| API region | us-west (`sfo`), Supabase in Frankfurt | EU West | every DB call no longer crosses the Atlantic | Railway manifest | hosted 20/20 |
| API server time, trivial routes | — | ~150 ms floor on Railway vs 2–3 ms in-process | platform overhead, not code | Railway HTTP logs vs local | — |

What changed: screens load as lazy chunks and are pre-fetched while idle
after sign-in; hashed assets are immutable for a year; the API origin is
preconnected; the sign-in screen holds the place of the registration and PIN
renewal offers (nothing stored in the browser); after 45 s without input the
decorative animations pause on their current frame; the API runs next to the
database. Not changed on purpose: the framework libraries that make up most
of the remaining bundle, app sleeping (turning it off costs money), the Liga
Nocturna visuals. The database holds one draft season and one trainer today:
query latency is not measurable as a bottleneck yet; the indexes from 008
and later migrations are in place.

Not achieved: the ~150 ms per-request floor on Railway (proxy/app sleeping)
remains; a cold start after sleep was not measured in this session.

## 4. Physical save operations — why they are not active

| Operation | Certified so far | Missing (blocks activation) |
| --- | --- | --- |
| Rare Candy / Heart Scale (local, free, unlimited) | File level on isolated copies of a real save: 0→10 and 0→7, backup, native read-back, recovery cases | **In-game check** (procedure step 6: open the modified copy in the isolated Lime3DS, see the bag, save in game, reopen). The project's rule: «only this step is an in-game PASS». Enabling it is one line (`PRODUCTION_MUTATIONS = {"add_item"}`) and a 0.26.2 through the live updater |
| Revive | Native fixtures | In-game check on a prepared copy |
| Robbery / two-save transfer | SQL, API and Launcher fixtures (24A/24B) | Two different real saves (two players), the hosted verifier, and the verifier's Linux import path (it still loads the Windows-only write engine) |

These are safety gates on real games, not paperwork: no real save may be the
destructive test, and the in-game result can only be seen by running the
game. They are the only open items.

## 5. Defects found and fixed during the release

- API could not start on Linux (Windows-only import) — fixed, portability test.
- Transfer-notice cache could hide a new notice — fixed, shipped in 0.26.1.
- Worker exported a string from its entry module — fixed.
- Signer tests left private test keys in `%TEMP%` — fixed (44 old folders remain; safe to delete `%TEMP%\pokeapp-sign-*`).
- Publication guard misread a bridge manifest — fixed.
- Web: 0.25 Launcher lost its native panels with the new web — fixed.
- Release harness issues (asar cache, versioned uninstall name, Git Bash `/S`, NSIS relaunch) — fixed; the stable-identity update test opened the owner's real profile for ~70 s (session token refreshed, no save written, production unchanged) — the harness now refuses that phase where a real profile exists.

## 6. Tests

| Gate | Result |
| --- | --- |
| Python | 1200/1200 |
| Vitest · TypeScript | 189/189 · clean |
| Playwright full | 114 passed, 11 skipped, 0 failed (+ visuals subset 20/20 after the idle change) |
| SQL | Rehearsal on real backup 24/24 (twice); parity 001–064 identical; Cup in one league 4/4; Phase 29 suites |
| Launcher / Worker node | 37/37 · 4/4 |
| Packaged | A→B rehearsal 30/30; public transition 8/8; hosted auto-update 0.26.0→0.26.1 |
| Public acceptance | 20/20 + browser 1440/390 without console errors or overflow |
| Windows 10 | Not available here — not certified |

## 7. Git

`HEAD` = `origin/main` (this report's commit, after `2fb379b`). Eight foreign
untracked files preserved; the protected guide untouched.

## 8. After the release (2026-10-28)

**0.26.2 — physical operations for the real tests.** Rare Candy, Heart Scale
and both robbery legs are production mutations (backup before every write,
paired permit for robberies, emulator closed). The hosted verifier runs on
Linux. Robberies need both players in one active season; revive/item use has
no production flow and stays off.

**0.26.3 — automatic save sync, also without a season.** The «Pendiente»
that never cleared came from a trainer with no active season: every save
endpoint and «Mi PC» were season-scoped, so the Launcher queued nothing.

| Change | Where |
| --- | --- |
| `trainer_personal_saves` (065) + least privilege (066): one backend-only row per trainer, forced RLS, service_role select/insert/update | Supabase, history 58 |
| `/v1/me/save/{context,receipt,raw}` and `/v1/me/pc`: same server-side parse and digest check as season saves; not competitive evidence | API, 108 routes |
| Signing in is the consent; each stable new save goes to the active season, otherwise to the personal record; «Sincronizada» only after the server readback | Launcher 0.26.3 |
| «Sincronizar ahora» removed; «Mis partidas» keeps the team of six, no box browser | Launcher 0.26.3 |
| «Mi PC» shows the season PC when ready, otherwise the personal save (15 s refresh); nobody is enrolled in a league | Web |

Backups are still made only before PokeApp changes a save (the first of each
day kept 30 days); syncing never writes to it.

Gates: Python 1208/1208; Vitest 189/189; Playwright Mi PC/saves specs 39 passed,
4 skipped; Launcher node 31/31; rehearsals on fresh production backups 14/14
(065, then 066); hosted acceptance 19/19; unpacked 0.26.3 in a sandboxed
profile reads the hosted feed as `UP_TO_DATE`.
