param(
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $SkipBuild) {
    & "$Root\export_example.ps1"
    & "$Root\package_portable.ps1" -AllowDemoSecret
}

$Portable = Join-Path $Root "dist\ListingTurboPortable"
if (!(Test-Path $Portable)) {
    throw "Demo-Paket konnte nicht erstellt werden: dist\ListingTurboPortable fehlt. Ohne -SkipBuild erneut ausführen."
}

$DemoReadme = Join-Path $Root "docs\DEMO_README.md"
if (Test-Path $DemoReadme) {
    Copy-Item $DemoReadme (Join-Path $Portable "DEMO_README.md") -Force
}
if (Test-Path (Join-Path $Root "docs\SALES_ONEPAGER.md")) {
    Copy-Item (Join-Path $Root "docs\SALES_ONEPAGER.md") (Join-Path $Portable "SALES_ONEPAGER.md") -Force
}
if (Test-Path (Join-Path $Root "out")) {
    Copy-Item (Join-Path $Root "out") (Join-Path $Portable "example_exports") -Recurse -Force
}

$DemoZip = Join-Path $Root "dist\ListingTurboEnterprise_Demo_v1.4.4.zip"
Compress-Archive -Path "$Portable\*" -DestinationPath $DemoZip -Force

Write-Host "Demo ZIP: $DemoZip" -ForegroundColor Green
