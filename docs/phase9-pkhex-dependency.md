# Phase 9 — PKHeX dependency and interop

Verified 2026-09-28 against primary sources and the restored package.

- Upstream: [kwsch/PKHeX](https://github.com/kwsch/PKHeX/tree/24.11.11).
  Tag `24.11.11` resolves to `b60c6e5f1427263260061d3f8c5540b924063572`.
- Dependency: [NuGet PKHeX.Core 24.11.11](https://www.nuget.org/packages/PKHeX.Core/24.11.11),
  exact version range, locked content hash in both .NET projects. Package metadata
  has repository commit `241112052953`, not a Git SHA: do not claim the package was
  reproducibly built from the tag. The tagged source and package metadata agree
  on net8.0 and GPL-3.0-or-later. Existing root DLL/legacy bridge stay unchanged.
- [Tagged project declaration](https://raw.githubusercontent.com/kwsch/PKHeX/24.11.11/PKHeX.Core/PKHeX.Core.csproj)
  identifies the license. [License text](https://github.com/kwsch/PKHeX/blob/24.11.11/LICENSE)
  is included with the parser source under `companion/parser/third-party/`.

Distribution checklist derived from GPL sections 4–6: preserve copyright/license
and warranty notices, identify modifications, provide corresponding source under
the applicable license when conveying covered binaries, and include build scripts
needed for that source. A separate process is an engineering boundary, not a legal
determination that the wider distribution is independent or exempt. This phase
does not distribute an installer or relicense the whole repository; packaging must
review the actual combined distribution and satisfy its obligations before release.

Choice: reuse the established Python/process interop pattern with a NEW read-only
.NET worker, not legacy mutation dispatch or Pythonnet. The worker receives bounded
bytes, produces neutral JSON and has no file-path/network API. Frontend, cloud
backend and competitive services do not import PKHeX. Local core remains UI-free
Python, without committing/depending on the ignored Electron experiment.

Update intentionally, never floating: review upstream/license, change exact package
version + locks, test all supported generations, 023 evidence and IPC DTOs, increment
parser version, then rebuild the eventual bundled worker/runtime. .NET 8 is the
current package target; runtime lifecycle and installer signing/update channel must
be reviewed at packaging time. No end-user PKHeX installation is intended.
