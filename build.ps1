$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
& ".\build_native.ps1"
if (!(Test-Path ".venv")) { py -3.12 -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" run_tests.py
Write-Host "ListingTurbo Build OK" -ForegroundColor Green
