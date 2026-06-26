$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path ".venv")) { & "$Root\build.ps1" }
& ".\.venv\Scripts\python.exe" license_admin.py machine-id
