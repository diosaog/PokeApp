# Phase 22E - isolated private candidate and independent qualification

Observed 2026-10-23. **PRIVATE CANDIDATE VALIDATED. Phase22 PARTIAL; production
physical writes OFF.** Entry main/origin `5156d64213f21a00fdf2c75f0a73c08dc01237db`,
fetched 0/0, clean tracked tree. The owner explicitly authorized independent
packaging/installation work without a 3DS game. This supersedes the previous
all-packaging stop, not the real-emulator or public-release gates.
[Evidence](phase22e-private-candidate-evidence.json),
[live handoff](work-in-progress/phase22-save-writes-live.md).

## Finished independent work

Private **0.22.0-rc.3** includes the existing 22C native engine, journal, backup
history, Save Copy and recovery protections. No writer redesign or new physical
mutation authorization. `-PrivateCandidate` builds with separate application ID,
executable, Start Menu shortcut, uninstall registration and default
`PokeApp/Launcher-Private` profile. The ordinary build retains its existing identity.
The packaged core and parser run without developer Python/.NET in PATH.

The corresponding native source archive now includes the previously omitted
`NativeWrite.cs`; package auditing verifies the exact four adapter source files.
The private candidate remains **unsigned/unpublished**, with no production write
capability. Original public0.20.0, private rc.2 and owner-installed0.16.2 are intact.

Azahar preparation now has a pinned2126.2 binary inspection and portable-copy tool:
runtime files only, empty isolated `user` directory, no keys/games/owner settings.
Unknown binary versions, network/reparse paths and occupied destinations fail
closed. Runtime exposes a fresh unqualified status; identifying a binary never
grants launch/close/write authority. No real-game lifecycle adapter is certified.

## New validation

- **6 focused Python PASS:** three new qualification/preparation tests and three
  affected runtime fallback regressions. Other74-case/eight-game engine evidence
  and 22D recovery tests retained; no full matrix or DS replay.
- **3 installed private Electron journeys PASS:** native X read/local/cloud-tab
  startup; seeded after-park recovery; restart after reinstall. Recovery remains
  blocked, exact verified backup copies succeed and eight restore/write IPC
  requests are denied. No renderer write capability or cloud login. Screenshot
  reviewed. Picker response is controlled by the harness; this is not interactive
  native-dialog acceptance or actual emulator gameplay.
- **Install, same-version reinstall and uninstall PASS**, all exit0. Private
  registration/shortcut removed. **440 owner installation/profile files and owner
  registration remain identical** throughout; **65 isolated profile files** and
  a sentinel in the actual private default profile survive reinstall/uninstall.
  This is a fresh isolated app installation on the existing Windows11/NTFS host,
  not a clean Windows VM or genuine cross-version production upgrade.
- Package audit, Ruff, Python compile, JS syntax, format and diff pass. Initial
  build found no SDK at the system dotnet path; only the native stage resumed
  after retrieving official SDK9.0.318 with SHA512 verification. Python was not
  rebuilt. Final formatting of the qualification module is whitespace-only;
  AST equality with the packaged input is recorded. A package smoke initially
  read a transient null observation; bounded state polling corrected the harness
  and a fresh profile passed, without changing product behavior.

The actual portable Azahar2126.2 main window also starts and closes normally,
exit0, **without a game**. Its meta frontend rejected `--version`; that failed
probe is retained. Closing the first startup window too early left a process
alive; the owned idle/no-game diagnostic was terminated for cleanup, not counted
as successful shutdown. Waiting for the ready main window gives normal closure.
This establishes only idle startup/exit, not game flush or restart exclusion.
The next lifecycle adapter must handle startup interruption explicitly.

## Artifact and boundaries

Installer: `%LOCALAPPDATA%/PokeApp-releases/0.22.0-rc.3-private/`
`PokeApp-Launcher-Private-Setup.exe`, **159181644 bytes**, Authenticode **NotSigned**.
SHA-256: `567993ad1e83b82eb5c8c9051f2f9075d12d2ef5db4c97f8a53fae6d0c14e3d3`.
The directory includes checksum and NOT-PUBLISHED notices. No distribution,
Railway, Cloudflare, Supabase, economy, entitlement, reward or owner-save write.
The authentic X source remained unchanged; the interrupted transaction existed
only in its disposable copy. No DS support, Phase23 or profiles added.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22e/20261023/`;
reproducible build retained in `%LOCALAPPDATA%/PokeApp-builds/0.22.0-rc.3-private-20261023/`.
The test installation was uninstalled and all test processes ended. Build, portable
Azahar copy and isolated profiles are retained deliberately for reproducibility.
Older cleanup residue was not touched. Automatic approval review rejected removal
of the sole new `%LOCALAPPDATA%/PokeApp/Launcher-Private/installation-sentinel.txt`
and its empty parent with **blocked by policy**; no bypass/retry was attempted.

## Remaining work

Real 3DS game/save flush, resource release during gameplay, actual restart
exclusion throughout application/recovery and in-game readback still need a legal
supported title. Windows10/additional builds/storage, OS-crash/power-loss policy
and evidence, clean-OS/cross-version acceptance and signing remain separate gates.
The approved absent-path interval does not need repeat approval. Future item use
still requires backend-authorized intent and an idempotent verified application
acknowledgement; export/backup never consumes an entitlement.

**Next:** review this private candidate independently; use a legal3DS title when
available to qualify the pinned lifecycle adapter. Do not enable writes meanwhile.
Estimated overall progress: **about90%**, qualitative, not a measured burndown.
Phase22 cannot be declared DONE. This focused commit carries the final report;
obtain its exact HEAD from Git. Explicit staging; five unrelated files preserved.
