param(
    [Parameter(Mandatory=$true)][string]$BuildRoot,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Dotnet,
    [switch]$PrivateCandidate,
    # Private owner preview: the PokeApp tab loads http://127.0.0.1:4173 (the
    # local design preview) instead of the deployed web. Private builds only.
    [switch]$WebPreview,
    # Optional signed updates. The signing key must live outside the repository
    # and the build root; only the public key is embedded in the package.
    [string]$UpdatePublicKeyFile = '',
    [string]$UpdateFeed = '',
    [string]$UpdateSigningKeyFile = '',
    [string]$UpdateDownloadUrl = '',
    [string]$UpdateMinimumVersion = '',
    [string]$UpdateNotes = '',
    [string]$BuildVersion = ''
)
$ErrorActionPreference = 'Stop'
if ($WebPreview -and -not $PrivateCandidate) { throw 'WebPreview requires PrivateCandidate' }
$repo = Split-Path -Parent $PSScriptRoot
$build = [IO.Path]::GetFullPath($BuildRoot)
if ($build.StartsWith($repo, [StringComparison]::OrdinalIgnoreCase)) { throw 'BuildRoot must be outside the repository' }
New-Item -ItemType Directory -Path $build -Force | Out-Null
function Checked([string]$Program, [string[]]$Arguments) {
    # Windows PowerShell 5 wraps native stderr (including harmless progress) as
    # ErrorRecord when redirected. The native exit code is the build result.
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Program @Arguments; $nativeExit = $LASTEXITCODE }
    finally { $ErrorActionPreference = $previousErrorAction }
    if ($nativeExit -ne 0) { throw "Build step failed: $Program ($nativeExit)" }
}
Push-Location $repo
try {
    Checked $Python @('-c', 'import sys; assert sys.version_info[:3] == (3,14,3), sys.version')
    Checked $Python @('-m','venv', (Join-Path $build 'build-venv'))
    $buildPython = Join-Path $build 'build-venv/Scripts/python.exe'
    Checked $buildPython @('-m','pip','install','--disable-pip-version-check','-r','companion/launcher/requirements-build.lock')
    Checked 'npm.cmd' @('ci','--prefix','companion/launcher')
    $overlay = Join-Path $build 'core-source'
    Checked $buildPython @('tools/prepare_launcher_core.py', $overlay)
    Checked $buildPython @('-m','PyInstaller','--noconfirm','--clean','--onedir','--console',
        '--name','PokeApp.Core','--paths',$overlay,
        '--distpath',(Join-Path $build 'python-dist'),
        '--workpath',(Join-Path $build 'pyinstaller-work'),
        '--specpath',$build,(Join-Path $overlay 'core-entry.py'))
    $stage = Join-Path $build 'stage'
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    if (Test-Path -LiteralPath (Join-Path $stage 'core')) { throw 'Use a fresh BuildRoot: core staging already exists' }
    Copy-Item -LiteralPath (Join-Path $build 'python-dist/PokeApp.Core') -Destination (Join-Path $stage 'core') -Recurse
    Checked $Dotnet @('publish','companion/parser/PokeApp.Parser/PokeApp.Parser.csproj',
        '-c','Release','-r','win-x64','--self-contained','true',
        '-p:RuntimeFrameworkVersion=8.0.29','-p:RestoreLockedMode=true',
        ('-p:NuGetLockFilePath=' + (Join-Path $repo 'companion/launcher/parser-win-x64.lock.json')),
        '-o',(Join-Path $stage 'parser'))
    Checked $buildPython @('tools/prepare_launcher_notices.py','--stage',$stage,'--build',$build)
    $env:POKEAPP_PACKAGE_STAGE = $stage
    $env:POKEAPP_PACKAGE_OUTPUT = Join-Path $build 'release'
    $env:POKEAPP_PRIVATE_CANDIDATE = if ($PrivateCandidate) { '1' } else { '0' }
    $env:POKEAPP_WEB_PREVIEW = if ($WebPreview) { '1' } else { '0' }
    $env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
    $env:POKEAPP_UPDATE_PUBLIC_KEY_FILE = $UpdatePublicKeyFile
    $env:POKEAPP_UPDATE_FEED = $UpdateFeed
    $env:POKEAPP_BUILD_VERSION = $BuildVersion
    Checked 'companion/launcher/node_modules/.bin/electron-builder.cmd' @(
        '--projectDir','companion/launcher','--config','electron-builder.cjs','--win','nsis','--x64','--publish','never')
    Checked $buildPython @('tools/audit_launcher_package.py','--build',$build)
    if ($UpdateSigningKeyFile) {
        $key = [IO.Path]::GetFullPath($UpdateSigningKeyFile)
        if ($key.StartsWith($repo, [StringComparison]::OrdinalIgnoreCase) -or $key.StartsWith($build, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Update signing key must be outside the repository and the build root'
        }
        $installer = Get-ChildItem -LiteralPath (Join-Path $build 'release') -Filter '*.exe' | Select-Object -First 1
        $channel = if ($PrivateCandidate) { 'private' } else { 'stable' }
        $authenticode = (Get-AuthenticodeSignature -LiteralPath $installer.FullName).Status.ToString()
        $version = if ($BuildVersion) { $BuildVersion } else { (Get-Content companion/launcher/package.json -Raw | ConvertFrom-Json).version }
        Checked 'node' @('tools/sign_launcher_update.cjs','--installer',$installer.FullName,'--version',$version,
            '--channel',$channel,'--minimum',$UpdateMinimumVersion,'--notes',$UpdateNotes,'--url',$UpdateDownloadUrl,
            '--key-file',$key,'--authenticode',$authenticode,'--build-root',$build,
            '--out',(Join-Path $build ('release/' + $channel + '.json')))
    }
} finally { Pop-Location }
