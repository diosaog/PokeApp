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
login checks existing identity and then discards its memory-only session. A future
long-lived UI can own `LauncherSession`; there is no persistent token store yet.
Ctrl+C stops watching. A profile has an OS-backed single-instance lease; UI callers
must acquire it before recovering interrupted operations or using the core.

**SYNCED means local observed snapshot recorded**, with destination in every result.
There is no remote save-ingestion endpoint or cloud-sync claim. BackendClient only
uses existing PIN login/refresh/me. No season, authoritative capture stream, entity
UUID or Team Lock is inferred from local sync. Journal revisions order local
observations, not gameplay. Replacing a save with an older one does not establish
competitively newer state. Journals/snapshots and backups contain private Pokemon
data and live in the user's local profile; do not attach them to public bug reports.

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
