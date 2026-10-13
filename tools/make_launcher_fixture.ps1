param([Parameter(Mandatory=$true)][string]$BuildRoot, [Parameter(Mandatory=$true)][string]$Dotnet)
$ErrorActionPreference = 'Stop'
$build = [IO.Path]::GetFullPath($BuildRoot)
$fixture = Join-Path $build 'synthetic-fixture'
if (Test-Path -LiteralPath $fixture) { throw 'Synthetic fixture already exists; do not regenerate' }
New-Item -ItemType Directory -Path $fixture | Out-Null
$pkhex = [System.Security.SecurityElement]::Escape((Join-Path $build 'stage/parser/PKHeX.Core.dll'))
@"
<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup>
<ItemGroup><Reference Include="PKHeX.Core"><HintPath>$pkhex</HintPath></Reference></ItemGroup>
</Project>
"@ | Set-Content -LiteralPath (Join-Path $fixture 'Fixture.csproj') -Encoding UTF8
@'
using PKHeX.Core;
using static System.Buffers.Binary.BinaryPrimitives;
// Newly generated, disposable synthetic bytes only; no owner save is opened.
var save = new SAV6XY { Version = GameVersion.X, OT = "Package Test", TID16 = 54321, SID16 = 12345, Language = 2 };
WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
var p = new PK6 { Species = 650, PID = 123456, EncryptionConstant = 987654,
    TID16 = 54321, SID16 = 12345, OriginalTrainerName = "Package Test", Language = 2,
    Version = GameVersion.X, CurrentLevel = 20, Move1 = 85, Move1_PP = 15 };
p.RefreshChecksum(); save.PartyData = new PKM[] { p };
File.WriteAllBytes(args[0], save.Write());
'@ | Set-Content -LiteralPath (Join-Path $fixture 'Program.cs') -Encoding UTF8
& $Dotnet run --project (Join-Path $fixture 'Fixture.csproj') -c Release -- (Join-Path $fixture 'main')
if ($LASTEXITCODE -ne 0) { throw 'Synthetic fixture generation failed' }
