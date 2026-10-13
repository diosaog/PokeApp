param([Parameter(Mandatory=$true)][string]$BuildRoot, [Parameter(Mandatory=$true)][string]$Fixture, [switch]$ResumeAfterRuntimeProof)
$ErrorActionPreference = 'Stop'
$build = [IO.Path]::GetFullPath($BuildRoot)
$install = Join-Path $build 'installed'
$evidence = Join-Path $build 'smoke'
$installer = Join-Path $build 'release/PokeApp-Launcher-Setup.exe'
$shortcut = Join-Path $env:APPDATA 'Microsoft/Windows/Start Menu/Programs/PokeApp Launcher.lnk'
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
function InstalledEntries { @(Get-ChildItem $registry | Get-ItemProperty | Where-Object { $_.DisplayName -like 'PokeApp Launcher*' }) }
if (!$ResumeAfterRuntimeProof -and ((Test-Path -LiteralPath $install) -or (Test-Path -LiteralPath $shortcut) -or @(InstalledEntries).Count)) {
    throw 'Existing install/shortcut detected; refusing to replace an owner installation'
}
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
function Install {
    $process = Start-Process -FilePath $installer -ArgumentList @('/S','/CURRENTUSER',("/D=$install")) -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }
    if (!(Test-Path -LiteralPath (Join-Path $install 'PokeApp Launcher.exe'))) { throw 'Installed executable missing' }
    if (!(Test-Path -LiteralPath $shortcut)) { throw 'Start Menu shortcut missing' }
    $entries = @(InstalledEntries)
    if ($entries.Count -ne 1) { throw 'Per-user uninstall registration missing or duplicated' }
    $expectedUninstaller = Join-Path $install 'Uninstall PokeApp Launcher.exe'
    if (!$entries[0].UninstallString.StartsWith(('"' + $expectedUninstaller + '"'))) { throw 'Unexpected registered location' }
}
if ($ResumeAfterRuntimeProof) {
    $proof = Get-Content -LiteralPath (Join-Path $evidence 'installed-smoke.json') -Raw | ConvertFrom-Json
    if ($proof.status -ne 'PASS' -or !$proof.default_data_outside_install.StartsWith($evidence)) { throw 'No valid runtime checkpoint' }
    $installedHash = (Get-FileHash -LiteralPath (Join-Path $install 'PokeApp Launcher.exe')).Hash
    if ($installedHash -ne (Get-FileHash -LiteralPath (Join-Path $build 'release/win-unpacked/PokeApp Launcher.exe')).Hash) { throw 'Installed binary differs from build' }
} else {
    Install
    & node (Join-Path $PSScriptRoot 'validate_launcher_installed.mjs') $install $evidence $Fixture
    if ($LASTEXITCODE -ne 0) { throw 'Installed runtime smoke failed; inspect evidence before cleanup' }
}
$sentinel = Join-Path $evidence 'local-data/PokeApp/Launcher/preserve-on-upgrade.txt'
$original = Get-FileHash -LiteralPath $sentinel -Algorithm SHA256
Install
if ((Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash -ne $original.Hash) { throw 'Reinstall changed local data' }
# Target was created by this exact run and checked against its uninstall registration.
$uninstaller = Join-Path $install 'Uninstall PokeApp Launcher.exe'
if (!(Test-Path -LiteralPath $uninstaller)) { throw 'Expected uninstaller missing' }
$process = Start-Process -FilePath $uninstaller -ArgumentList @('/S',("_?=$install")) -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw 'Uninstall failed' }
if (@(InstalledEntries).Count -or (Test-Path -LiteralPath $shortcut)) { throw 'Uninstall left registry/shortcut' }
if (Test-Path -LiteralPath (Join-Path $install 'PokeApp Launcher.exe')) { throw 'Uninstall left application' }
if ((Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash -ne $original.Hash) { throw 'Uninstall removed user data' }
@{
    status='PASS'; install=0; reinstall=0; uninstall=$process.ExitCode;
    current_user_registry=$true; start_menu=$true; shortcut_registry_removed=$true;
    local_data_preserved=$true; no_visible_window=$true; clean_vm=$false;
    unsigned=(Get-AuthenticodeSignature -LiteralPath $installer).Status.ToString()
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'install-uninstall.json') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $evidence 'install-uninstall.json')
