# Phase 28 — Launcher definitivo y administración avanzada: contracts

Status: **local only.** Nothing in this document is deployed. Migration 062 and
the incident API are off in production; public physical writes stay OFF.
Report: [phase28-report.md](phase28-report.md).

## 1. Navigation (web = Launcher)

- One sidebar for both. The 27C «Escritorio» group is removed; its tools moved:

  | Former entry | Where it lives now |
  | --- | --- |
  | Mi partida | «Saves y Launcher» › Mis partidas |
  | Objetos ∞ | Inventario (profile) › «Añadir a la bolsa» |
  | Robos y entregas | Robbery cards in Inventario, Launcher notice strip, admin incident center |
  | Copias de seguridad | «Saves y Launcher» › Copias de seguridad |
  | Conexión | Automatic; sync chip in Mis partidas and Launcher tab |

- Doors the Launcher watches (the web only navigates, never sends data):
  `/saves` → native hub; `/escritorio/objetos/<rare_candy|heart_scale>` and
  `/escritorio/robos` → native dialogs over the web. Legacy
  `/escritorio/partida|copias|nube` → hub tabs (in a browser: redirect to `/saves`).
- Native views are an allow-list in `webview.cjs`, re-filtered in `preload.cjs`.

## 2. Session (one sign-in)

1. First run shows the PokeApp login (the web). When the web's
   `POST /v1/auth/pin-login` succeeds, main forwards the same trainer/PIN —
   held in memory for that request only — to the core, which signs in and keeps
   the session encrypted with DPAPI (TokenStore). The PIN is never stored.
2. Later runs: main gives the web an **access token only** (never the refresh
   token) via `window.__pokeappLauncherSession(...)`, only if the web's API
   origin (its `build-config.json`) equals the core's backend origin. The web
   asks with a navigation to `/__launcher/session` (no query, no data), which the
   Launcher cancels and answers. The core is the only refresher.
3. The token never appears in URLs, logs, `state()` (renderer) or storage; the
   web keeps it in memory. Junk offers are ignored (shape, length, UUID).
4. Signing out in the web navigates to `/__launcher/logout`: the core drops the
   web token **at once** (before its queue runs logout), stops sync and clears
   its session. Refused until the next successful sign-in.
5. Preview builds (synthetic API) never receive or forward real credentials:
   origins differ, so steps 1–2 are skipped.

## 3. Save detection and automatic sync

- Discovery lists Lime3DS/Azahar/Citra save paths at fixed depth and `stat()`s
  them (modified time); it never opens a save for writing.
- One candidate and none selected → chosen and remembered (`AUTO_SELECTED`).
  Several → the selector opens by itself once (`CHOOSE`) and stays as a notice.
  None → empty state with «Buscar partidas en un emulador» (`NONE`).
  A remembered save is never replaced (`KEPT`); a candidate not seen before is
  announced (`new`, by path hash in `known-saves.json`; the first discovery
  sets the baseline).
- Cycle (unchanged engine, verified): watch → debounce until stable → native
  read → journal receipt (hash) → `enqueue_raw` refuses bytes that differ from
  the stable read → one outbox row per content (same hash = same row) →
  delivery asks `/receipt` first (no duplicate upload), compare-and-swap on the
  current save, read-back of the PC before success → `last_synced`.
  Offline: rows stay queued and retry; superseded/foreign rows are blocked,
  never shown as synced. Works with the emulator open (read only).
- Consent: signing in enables automatic sync for that trainer **if no other
  trainer synced from this Launcher profile**; on a shared PC a second trainer
  confirms once («Sincronizar ahora»). The server also refuses a save of a
  different in-game trainer once a season's identity is set
  (`SAVE_TRAINER_MISMATCH`).
- Chip: Sincronizado / Sincronizando / Pendiente / Sin conexión / Error
  (+ Sin partida, Sin cuenta).

## 4. In-app confirmations (replace native message boxes)

Every confirmed step asks main for a ticket: `launcher:confirm-begin(kind,
target)` re-reads the core state, refuses an action that is not available now,
writes the dialog text itself and returns a **single-use ticket** (120 s) bound
to the kind, the target and a fingerprint of that state. The action IPC must
present it; main redeems it (spent even on mismatch) and re-checks the
operation before the core runs it; the core and the server re-check again.

| Kind | Target | Fingerprint |
| --- | --- | --- |
| `write` | operation id | selected save, operation, description |
| `export` | `current` | selected save, export intent |
| `restore` | backup operation id | selected save, operation, game, creation time |
| `transfer:prepare/apply/fulfil/cancel` | authorization id | save, kind, id, status, obligation, apply_started, location |
| `install` | version | version |

File pickers stay native (OS dialogs, not alerts).

## 5. Restore policy

Copias de seguridad lists each backup (game, date and time, type, integrity,
retention). «Restaurar…» appears only when the engine reports `can_restore`
(original, verified, no-replace protocol, not a transfer, engineering
capability — so never in public builds). The dialog shows main's summary and
checks; the button enables only with all checks, «He cerrado el juego y el
emulador» and the exact word **Confirmo** (case and spaces exact; Enter never
submits). Main requires the word, the ticket for that backup of that save, no
busy operation, no recovery, and **no open robbery** (mandatory sync, an
unverified obligation, or an applied but uncommitted leg). The engine then
saves and verifies the current state first and restores transactionally with
its journal; retention unchanged (original per change, daily 30 days).

## 6. Admin console

Three areas (no more): **Liga y competición** (Resumen, Configuración,
Entrenadores, Competición, Historial, Zona de riesgo — unchanged tools),
**Economía e incidencias** (new) and **Cuentas y sistema** (accounts +
capability status). The setup read polls every 20 s and the incident read every
15 s while open; every command invalidates the reads it affects after the
server's receipt (never before).

### Permissions matrix

| Capability | Anonymous | Trainer | Admin | Backend role | Notes |
| --- | --- | --- | --- | --- | --- |
| Incident read | ✗ | ✗ | ✓ | execute only | `admin_incident_read` |
| Cancel / refund purchase | ✗ | ✗ | ✓ (reason) | execute only | `admin_purchase_resolve` |
| Coin correction | ✗ | ✗ | ✓ (reason) | execute only | `admin_coin_adjust` |
| Read `admin_incident_commands` directly | ✗ | ✗ | ✗ | ✗ | forced RLS, no grant |
| Update/delete audit rows | ✗ | ✗ | ✗ | ✗ | trigger refuses (also truncate) |
| Cancel a robbery after application | ✗ | ✗ | ✗ | ✗ | reconciliation only |
| Restore a backup (Launcher) | — | own save, engineering builds | — | — | ticket + Confirmo |

Admin = enabled trainer with `is_admin` and a provisioned auth identity,
checked by the API (`require_admin_principal`) **and** inside each SQL function.

### Cancellation and refund contracts (migration 062)

`POST /v1/admin/seasons/{season}/incidents/purchases/{purchase}`
`{ "action": "cancel" | "refund", "reason": "5–500 chars" }`, header
`Idempotency-Key: <uuid>`.
`POST /v1/admin/seasons/{season}/incidents/coins`
`{ "trainer_id", "amount": ±1–100000, "reason" }`, same header.
`GET  /v1/admin/seasons/{season}/incidents` → wallets, purchases (with
`cancellable`, `refundable`, `linked_operation`), robberies (read only),
intervention history.

Rules, all enforced in SQL under the wallet lock every purchase takes:

- cancel: purchase `pending`, no applied redemption → `cancelled`, credit its
  price once (`compensation`, `purchase_cancellation`).
- refund: purchase `used` → `refunded`, credit once (`purchase_refund`); the
  applied effect is not undone.
- Never for a purchase linked to an item-use/transfer authorization
  (`PURCHASE_LINKED_TO_SAVE_OPERATION`): a physically applied robbery is
  reconciled by its own flow, never by a status change.
- Coin correction: `admin_adjustment`, never leaves the wallet below zero.
- Archived seasons are frozen (`HISTORICAL_ARTIFACT_IMMUTABLE`).
- Idempotency: the operation id + request hash (kind, season, target, body)
  replays the stored receipt (`replayed: true`); same id with other data →
  `IDEMPOTENCY_CONFLICT`. One reversal per purchase is also a unique index on
  the ledger and on the audit.
- Nothing is deleted: the purchase row stays with `metadata.admin_incident`
  (operation, actor, previous status); coins move only by new ledger rows.

Errors: 403 `ADMIN_REQUIRED`; 404 `SEASON_NOT_FOUND`, `PURCHASE_NOT_FOUND`,
`PARTICIPANT_NOT_FOUND`; 409 `PURCHASE_NOT_CANCELLABLE`,
`PURCHASE_NOT_REFUNDABLE`, `PURCHASE_LINKED_TO_SAVE_OPERATION`,
`PURCHASE_ALREADY_REVERSED`, `INSUFFICIENT_FUNDS`, `IDEMPOTENCY_CONFLICT`,
`HISTORICAL_ARTIFACT_IMMUTABLE`, `ITEM_UNAVAILABLE`; 422 validation;
503 `INCIDENTS_UNAVAILABLE` (center off or backend down — never shown as done).

Enabling it (owner authorization required): apply 062 after 054–061, set
`POKEAPP_ADMIN_INCIDENTS_ENABLED=true` on the API, redeploy API and web.

## 7. Updates

Browser: «Descargar Launcher». Launcher: «Buscar actualizaciones» re-runs the
signed-manifest check (Ed25519 manifest, SHA-512 + size of the installer
verified before install). With no channel configured (every build so far) the
popup says so and offers nothing; «Descargar e instalar» appears only for a
verified offer, and installing needs a ticket for that version.
