# PokeApp Launcher base

One UI-free Windows-first core, not separate Launcher editions. This is a runnable
development foundation; installer, final UI, bundled runtime and updater follow
later. PKHeX is internal, never an end-user UI requirement.

Python modules: `app/save_parser` and `app/launcher`. For a separate local Python
environment, install `requirements-launcher.txt`; the existing API environment also
contains these dependencies. Read-only .NET worker:
`parser/PokeApp.Parser`; pinned PKHeX.Core with NuGet locks. Requires Python with
the repository API environment, .NET 8 SDK to build and .NET 8 runtime to run the
framework-dependent development worker. Build on Windows:

```powershell
dotnet restore companion/parser/PokeApp.Parser --locked-mode
dotnet build companion/parser/PokeApp.Parser -c Release --no-restore
.venv-api/Scripts/python.exe tools/validate_phase9_launcher.py --dotnet <dotnet.exe>
.venv-api/Scripts/python.exe tools/run_unit_tests.py --pattern 'test_phase9*.py'
```

The integration tool builds/checks .NET, generates saves in a temporary directory,
executes real byte IPC, checks Windows locks, local sync/restart/backups/CLI and
removes only its own temporary fixtures. No personal save is required.

Local development commands (quote paths containing spaces):

```powershell
.venv-api/Scripts/python.exe -m app.launcher add-folder 'D:/Emulator/Saves'
.venv-api/Scripts/python.exe -m app.launcher discover
.venv-api/Scripts/python.exe -m app.launcher select 'D:/Emulator/Saves/game.sav'
.venv-api/Scripts/python.exe -m app.launcher --parser companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe inspect 'D:/Emulator/Saves/game.sav'
.venv-api/Scripts/python.exe -m app.launcher --parser companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe sync
.venv-api/Scripts/python.exe -m app.launcher --parser companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe watch
.venv-api/Scripts/python.exe -m app.launcher --parser companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe backup
.venv-api/Scripts/python.exe -m app.launcher login --backend https://your-pokeapp-backend.example --trainer your-slug
.venv-api/Scripts/python.exe -m app.launcher status
```

`--profile <directory>` selects an isolated local profile; default Windows profile
is `%LOCALAPPDATA%/PokeApp/Launcher`. Config stores selection, folders, backend origin
and watch settings, never credentials. PIN is prompted without echo; this CLI's
login checks existing identity and then discards its memory-only session. The new
Phase16 shell below owns a longer-lived session in current-user Windows DPAPI.
Ctrl+C stops watching. A profile has an OS-backed single-instance lease; UI callers
must acquire it before recovering interrupted operations or using the core.

**SYNCED means local observed snapshot recorded**, with destination in every result.
That CLI status alone is not cloud acceptance. No authoritative capture stream, entity
UUID or Team Lock is inferred from local sync. Journal revisions order local
observations, not gameplay. Replacing a save with an older one does not establish
competitively newer state. Journals/snapshots and backups contain private Pokemon
data and live in the user's local profile; do not attach them to public bug reports.

## Phase 16 local shell

From `companion/launcher`, run `npm ci` then `npm start`. The repository Python
environment, built parser executable and installed .NET 8 runtime are required.
This is a development shell, not an installer or updater. The ignored old
`desktop/` Streamlit wrapper is not used. Optional trusted local environment paths:
`POKEAPP_LAUNCHER_PYTHON`, `POKEAPP_LAUNCHER_PARSER`, `POKEAPP_LAUNCHER_PROFILE`.

Select a supported save. Local parse, six party slots, one 30-slot box and detail
navigation work without cloud access. Species/item/move/ability/nature IDs are
shown where the neutral DTO has no localized names; types/sprites are not invented.
PIN login reuses V2; tokens use current-user DPAPI, never plaintext. Local cache
and observations remain private user-profile files, not a shared-machine vault.
Separate workers handle stable local polling and network IO. API requests time out
after 15 seconds; heartbeat is 30 seconds, offline at 90 seconds without success.
Cloud reads refresh every 120 seconds or for pending observations/manual retry. Failures use
bounded backoff, stop after five attempts and expose manual retry; recovery within
that window is automatic. Re-authentication is required for rejected sessions.

Cloud synchronization is explicitly enabled in the shell. An immutable outbox
retains at most 64 pending and 64 accepted local records, scoped to API/trainer/
season. Every submission first queries its deterministic receipt, including after
restart or a lost response. Only observations are queued, never business commands.
The API accepts a private **client-observed** receipt into migration 043's inbox.
Authenticated submitter and season membership are validated; this does not prove
that the submitted bytes belong to that player's game. Trusted raw-file provenance
and competitive promotion are deliberately separate and still pending: no current
save head, identity stream, medal reward, Team Lock or public projection is updated.
The shell shows this limitation and last-known cloud age explicitly.

The shell grants the renderer only six IPC actions and blocks renderer network,
new windows, navigation and Node integration. No TCP service is exposed locally.
`POKEAPP_LAUNCHER_HEADLESS_TEST=1` creates a hidden shell for CLI validation only.

Supported initial family: native main-series Gen3/4/5 auto-recognized by pinned
PKHeX; ambiguous/unsupported/corrupt input fails explicitly. Gen3 game/language
recognition and combined game-family labels follow source evidence, not guesses.
No legality claim or exhaustive ROM-hack/emulator support. Discovery scans only
selected folders (flat, bounded) and returns candidates; selection stays explicit.

Future physical-write implementation must require a verified prepared backup and
expected fingerprint, serialize/validate a temporary output, recheck the live
source, perform controlled replacement, verify output and record recovery status.
The present `BackupService.apply` always rejects with `PHYSICAL_WRITES_DISABLED`.
Backups remain available for manual recovery; no restore writes execute in Phase 9.

[Contract](../docs/phase9-parser-launcher.md), [dependency/license](../docs/phase9-pkhex-dependency.md),
[evidence](../docs/phase9-completion-report.md).
