# Windows Launcher distribution

Version authority: `companion/launcher/package.json`. Electron, NSIS and the web
download label/Worker key consume it. `0.16.1` is an unsigned preview for Windows
10/11 x64. SmartScreen may warn. No updater is enabled.

Build on Windows x64 with Python **3.14.3**, Node **24.14.0** and .NET SDK
**9.0.318** available to the builder. End users need none of these installed.
Use a fresh directory outside the repository:

```powershell
./tools/build_launcher_windows.ps1 -BuildRoot C:/build/pokeapp-release `
  -Python C:/Python314/python.exe -Dotnet C:/dotnet9/dotnet.exe
```

This installs exact Python build requirements and `npm ci`, builds a narrow
desktop Python source overlay, freezes it with PyInstaller, publishes the locked
parser with .NET **8.0.29** self-contained for win-x64, assembles notices and covered
parser source, builds per-user NSIS and audits the result. It fails on an unexpected
application module or payload. Locks/configuration make inputs and procedure
repeatable; PE/installer timestamps mean bit-for-bit reproducibility is not claimed.
The original parser development lock is unchanged; packaging has a separate RID lock.

Output: `release/PokeApp-Launcher-Setup.exe` and `package-audit.json` with SHA-256.
The icon is the current web favicon; `node tools/launcher_icon.mjs` regenerates
its committed ICO using headless Edge. Build-only electron-builder dependencies
are not shipped. The Python namespace overlay omits the competitive domain barrel;
it copies the actual Launcher, parser and Pokémon identity implementation without
changing server imports or behavior.

Runtime data is `%LOCALAPPDATA%/PokeApp/Launcher` (Electron cache under `shell`).
Current-user DPAPI remains the token boundary. Per-user install defaults to Windows'
local Programs directory; Start Menu and Add/Remove Programs are registered.
Uninstall removes the application and shortcuts while retaining user data.
Packaged mode ignores development Python/parser executable overrides.

Focused proof (no desktop control; creates a synthetic save, never opens an owner save):

```powershell
./tools/make_launcher_fixture.ps1 -BuildRoot C:/build/pokeapp-release -Dotnet C:/dotnet9/dotnet.exe
./tools/validate_launcher_install.ps1 -BuildRoot C:/build/pokeapp-release `
  -Fixture C:/build/pokeapp-release/synthetic-fixture/main
```

The smoke refuses to replace an existing installation. It installs to its disposable
directory, launches the installed binary hidden with developer runtimes unavailable,
parses synthetic X bytes, restarts from local data, reinstalls, uninstalls and verifies
the current-user registration/shortcut cleanup and user-data preservation.
This is isolated-host proof, not a claim of testing a clean Windows VM.

Release hosting uses one private R2 bucket, `pokeapp-launcher-releases`, bound only
to the existing `pokeapp-web` Worker. Upload the committed version's installer to
`windows/<version>/PokeApp-Launcher-Setup.exe`. Then deploy the web. The sole public
download is `/launcher/download`; it streams that exact object with attachment/MIME
headers and has no upload, arbitrary-key or bucket-listing interface. The Save card
links directly there. Do not replace a versioned object after publication; publish
a new package version. Keep the previous object and Worker version for rollback.

Included license notices cover Electron/Chromium, Python, bundled Python packages,
.NET and PKHeX. `runtime/licenses/parser-corresponding-source.zip` contains the
read-only adapter and official pinned PKHeX Core source/build inputs under GPL-3.0-or-later.
The upstream tag and NuGet package share the pinned release; NuGet metadata does
not establish a reproducible Git source-to-binary match. This does not relicense
the rest of the private repository. No repository credentials, fixtures, tests,
private evidence, backend, migration tools or owner save bytes are distributed.
