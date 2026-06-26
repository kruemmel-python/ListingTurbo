param(
    [string]$Owner = "kunde@example.com",
    [ValidateSet("STANDARD", "PRO")][string]$Plan = "PRO",
    [string]$MachineId = "",
    [string]$ActivationId = "",
    [string]$Expires = "",
    [switch]$Force
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path ".venv")) { & "$Root\build.ps1" }
if ([string]::IsNullOrWhiteSpace($MachineId)) {
    $MachineId = & ".\.venv\Scripts\python.exe" license_admin.py machine-id
    Write-Host "Keine Machine-ID angegeben. Nutze lokale Entwickler-Machine-ID: $MachineId" -ForegroundColor Yellow
}
$argsList = @("license_admin.py", "issue", "--owner", $Owner, "--plan", $Plan, "--machine-id", $MachineId)
if (![string]::IsNullOrWhiteSpace($ActivationId)) { $argsList += @("--activation-id", $ActivationId) }
if (![string]::IsNullOrWhiteSpace($Expires)) { $argsList += @("--expires", $Expires) }
if ($Force) { $argsList += @("--force") }
& ".\.venv\Scripts\python.exe" @argsList
