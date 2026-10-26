# Phase26C — Launcher with the full PokeApp web + infinite trainer items

2026-10-26. **PHASE26C PARTIAL (deploy-dependent items only). Production
UNCHANGED; nothing published; public physical writes OFF.** Entry `7b6909e`.
Started under an **owner-authorized exception** to the 26B gate: 26B stays
PARTIAL and deferred; its robbery items are release blockers, not 26C blockers.

## Infinite Rare Candy / Heart Scale

- Single source of truth `app/domain/unlimited_items.py`: two permanent,
  virtual items (codes `rare_candy`/50 and `heart_scale`/93). No migration, no
  stored quantity, no price, purchase, admin approval, quota or consumption.
- `InventoryRead.unlimited_items` returns both for every trainer, existing or
  new, in every season; ordinary purchases are untouched.
- Web inventory: section "Objetos ilimitados" with icon, name, **∞ · Gratis**,
  description; in a normal browser "Disponible en PokeApp Launcher", inside the
  Launcher a link «Añadir a mi partida» that opens the native quick-item panel
  (+, −, editable quantity, real bag limits, backup/journal/verification).
- Physical adding stays behind the prepared switch, OFF until certification.

## Launcher = the real PokeApp web

The «PokeApp» tab hosts the **deployed React app itself** (one web, one auth,
one API, no duplicated logic) in an isolated `WebContentsView`: no preload or
IPC, sandbox, context isolation, own persistent session, navigation pinned to the
web origin, popups denied, other HTTPS links opened in the system browser,
permissions denied, `<webview>` refused. The only bridge is the same-origin link
`/__launcher/quick-items/<rare_candy|heart_scale>`, intercepted to switch to the
native panel. Packaged builds always use `https://pokeapp-web.pokeapp-v2.workers.dev`;
a local origin override exists only in unpackaged development. Native areas stay:
«Mi partida» (save, Lime3DS/Azahar/Citra discovery, quick items, robberies,
backups, updater, version) and «Estado de la nube».

| Web route (React) | Page | In Launcher |
| --- | --- | --- |
| `/` | Inicio | PokeApp tab |
| `/liga` | Liga y clasificación | PokeApp tab |
| `/battle` | Combates | PokeApp tab |
| `/entrenadores`, `/entrenadores/scouting`, `/entrenadores/:id` | Entrenadores, scouting, perfil + inventario | PokeApp tab |
| `/pc` | Pokémon y PC | PokeApp tab |
| `/tienda` | Tienda | PokeApp tab |
| `/copa/*` | Copa | PokeApp tab |
| `/hall` | Hall of Fame | PokeApp tab |
| `/juicios` | Juicios | PokeApp tab |
| `/saves` | Saves | PokeApp tab |
| `/admin`, `/admin/cuentas` | Administración (role-gated by the API) | PokeApp tab |
| — | Partida, objetos rápidos, robos, backups, actualizador | Native «Mi partida» |

Parity is by construction: the same app, routes, API and permissions. **Limit:**
the Launcher shows what is deployed; the ∞ cards and `unlimited_items` reach it
only after the web and API are deployed (not done in this phase).

## Validation

- Python 99 affected tests OK (new: unlimited items virtual, free, not consumed,
  ordinary inventory intact, other season).
- Web 22 files / 154 tests OK (new: ∞ cards free with no purchase action; Launcher
  link only inside the Launcher), `tsc -b`, Prettier.
- Launcher Node tests 13/13 (web-view policy, updater, quantity); Electron 44:
  isolated web view 6/6 (no `window.launcher`/`require`/`process`, approved bridge
  only, external links out, never leaves origin, no popup), Launcher UI 25/25.
- Packaged private build `0.23.0-rc.2` with the official script: audit PASS
  (exact asar incl. `webview.cjs`, packaged web origin is production, updates not
  configured, unsigned, SHA-256 `c9f352dc…`). Not distributed; its web tab was not
  launched packaged (it would load the production web).

| Gate | Result |
| --- | --- |
| EXCEPTION TO 26B GATE | OWNER AUTHORIZED |
| PHASE 26B | PARTIAL, DEFERRED |
| TRAINER INVENTORY RARE CANDY ∞ | PASS (local) |
| TRAINER INVENTORY HEART SCALE ∞ | PASS (local) |
| UNLIMITED/FREE ACCESS | PASS |
| WEB INVENTORY | PASS (local build) |
| LAUNCHER INVENTORY | PARTIAL (native panel ready; web cards after deploy) |
| WEB ↔ LAUNCHER FUNCTIONAL PARITY | PASS (same deployed app) |
| AUTHENTICATION & PERMISSIONS | PARTIAL (reused; no live test account run) |
| PACKAGED LAUNCHER | PASS (build + audit; packaged web tab not run) |
| PUBLIC ROBBERY WITH NON-COOPERATIVE VICTIM | DISABLED |
| PUBLIC PHYSICAL WRITES | DISABLED |
| PHASE 26C | PARTIAL (deploy-dependent) |

Release blockers carried: 26B non-cooperative completion and mandatory sync,
`.displaced`/`.lock` handling (26D), hosted verifier, Authenticode, Windows 10,
054–060 deployment. The embedded web keeps its own login session (same accounts,
same API) separate from the Launcher's sync session.
