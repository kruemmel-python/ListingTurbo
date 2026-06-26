param(
    [int]$Port = 53317,
    [string]$Pin = ""
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path ".venv")) { & "$Root\build.ps1" }
$argsList = @("mobile_sync_server.py", "--port", "$Port")
if (![string]::IsNullOrWhiteSpace($Pin)) { $argsList += @("--pin", $Pin) }
& ".\.venv\Scripts\python.exe" @argsList
