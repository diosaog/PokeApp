param(
    [Parameter(Mandatory=$true)][string]$BuildRoot,
    [Parameter(Mandatory=$true)][string]$EvidenceRoot,
    [Parameter(Mandatory=$true)][ValidateSet('Install','Reinstall','Uninstall')][string]$Step
)
$ErrorActionPreference = 'Stop'
$build = [IO.Path]::GetFullPath($BuildRoot)
$evidence = [IO.Path]::GetFullPath($EvidenceRoot)
$install = Join-Path $build 'isolated-installed'
$installer = Join-Path $build 'release/PokeApp-Launcher-Private-Setup.exe'
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
$menu = Join-Path $env:APPDATA 'Microsoft/Windows/Start Menu/Programs'
$shortcut = Join-Path $menu 'PokeApp Launcher Private.lnk'
$baseline = Join-Path $evidence 'owner-install-baseline.json'
$receipt = Join-Path $evidence 'private-install-receipt.json'
function PrivateEntries { @(Get-ChildItem $registry | Get-ItemProperty | Where-Object { $_.DisplayName -like 'PokeApp Launcher Private*' }) }
function OwnerSnapshot {
    $entries = @(Get-ChildItem $registry | Get-ItemProperty | Where-Object { $_.DisplayName -like 'PokeApp Launcher*' -and $_.DisplayName -notlike 'PokeApp Launcher Private*' } | Sort-Object PSChildName)
    $roots = @((Join-Path $env:LOCALAPPDATA 'PokeApp/Launcher'))
    $records = @($entries | ForEach-Object {
        if ($_.UninstallString -match '^"([^"]+)"') { $roots += Split-Path -Parent $Matches[1] }
        @{key=$_.PSChildName;name=$_.DisplayName;version=$_.DisplayVersion;uninstall=$_.UninstallString}
    })
    $files = [ordered]@{}
    foreach($root in ($roots | Sort-Object -Unique)) {
        if(Test-Path -LiteralPath $root) {
            foreach($file in (Get-ChildItem -LiteralPath $root -File -Recurse | Sort-Object FullName)) {
                $files[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            }
        }
    }
    $ownerShortcut=Join-Path $menu 'PokeApp Launcher.lnk'
    if(Test-Path -LiteralPath $ownerShortcut) { $files[$ownerShortcut]=(Get-FileHash -LiteralPath $ownerShortcut).Hash }
    # Entries serialized separately; no owner file bytes or credentials leave this machine.
    return @{entries=$records;files=$files}
}
function CheckOwner {
    $expected=Get-Content -LiteralPath $baseline -Raw | ConvertFrom-Json
    $actual=OwnerSnapshot
    $expectedFiles=@($expected.files.PSObject.Properties | Sort-Object Name | ForEach-Object { $_.Name+'='+$_.Value })
    $actualFiles=@($actual.files.Keys | Sort-Object | ForEach-Object { $_+'='+$actual.files[$_] })
    if($expectedFiles.Count -ne $actualFiles.Count -or ($expectedFiles.Count -gt 0 -and (Compare-Object $expectedFiles $actualFiles))){throw 'Owner installation/profile changed: inspect, do not restore blindly'}
    $expectedEntries=@($expected.entries | ForEach-Object { $_.key+'|'+$_.name+'|'+$_.version+'|'+$_.uninstall })
    $actualEntries=@($actual.entries | ForEach-Object { $_.key+'|'+$_.name+'|'+$_.version+'|'+$_.uninstall })
    if($expectedEntries.Count -ne $actualEntries.Count -or ($expectedEntries.Count -gt 0 -and (Compare-Object $expectedEntries $actualEntries))){throw 'Owner registration changed'}
    return $actualFiles.Count
}
if($Step -eq 'Install') {
    if((Test-Path -LiteralPath $install) -or (Test-Path -LiteralPath $shortcut) -or @(PrivateEntries).Count -or (Test-Path -LiteralPath $baseline)){throw 'Fresh isolated installation required'}
    New-Item -ItemType Directory -Path $evidence -Force | Out-Null
    OwnerSnapshot | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $baseline -Encoding UTF8
} else {
    if(!(Test-Path -LiteralPath $receipt)){throw 'Verified initial install receipt required'}
    $prior=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if($prior.install -ne $install){throw 'Install target changed'}
    $entries=@(PrivateEntries)
    if($entries.Count -ne 1 -or !$entries[0].UninstallString.StartsWith(('"'+(Join-Path $install 'Uninstall PokeApp Launcher Private.exe')+'"'))){throw 'Unexpected private registration'}
    CheckOwner | Out-Null
}
if($Step -ne 'Uninstall') {
    $process=Start-Process -FilePath $installer -ArgumentList @('/S','/CURRENTUSER',('/D='+$install)) -WindowStyle Hidden -PassThru -Wait
    if($process.ExitCode -ne 0){throw "Private installer failed: $($process.ExitCode)"}
    $entries=@(PrivateEntries)
    if($entries.Count -ne 1 -or !(Test-Path -LiteralPath $shortcut)){throw 'Private registry/shortcut missing or duplicate'}
    if(!$entries[0].UninstallString.StartsWith(('"'+(Join-Path $install 'Uninstall PokeApp Launcher Private.exe')+'"'))){throw 'Unexpected private installation path'}
    $exe=Join-Path $install 'PokeApp Launcher Private.exe'
    if((Get-FileHash -LiteralPath $exe).Hash -ne (Get-FileHash -LiteralPath (Join-Path $build 'release/win-unpacked/PokeApp Launcher Private.exe')).Hash){throw 'Installed executable mismatch'}
}else{
    $uninstaller=Join-Path $install 'Uninstall PokeApp Launcher Private.exe'
    $process=Start-Process -FilePath $uninstaller -ArgumentList @('/S',('_?='+$install)) -WindowStyle Hidden -PassThru -Wait
    if($process.ExitCode -ne 0){throw "Private uninstall failed: $($process.ExitCode)"}
    if(@(PrivateEntries).Count -or (Test-Path -LiteralPath $shortcut) -or (Test-Path -LiteralPath (Join-Path $install 'PokeApp Launcher Private.exe'))){throw 'Private uninstall left application registration'}
}
$ownerFiles=CheckOwner
$result=@{status='PASS';step=$Step;install=$install;exit_code=$process.ExitCode;owner_files_identical=$ownerFiles;owner_registry_identical=$true;clean_vm=$false;isolated_app_identity=$true}
if($Step -eq 'Install'){$result | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding UTF8}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence ($Step.ToLowerInvariant()+'.json')) -Encoding UTF8
$result | ConvertTo-Json
