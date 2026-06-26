$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path ".venv")) { & "$Root\build.ps1" }
Remove-Item ".\out" -Recurse -Force -ErrorAction SilentlyContinue
& ".\.venv\Scripts\python.exe" listingturbo_cli.py ".\examples\samsung_s22.lturbo.json" --out ".\out" --format all
Get-ChildItem ".\out" -Recurse
