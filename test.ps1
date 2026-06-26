$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path ".venv")) { py -3.12 -m venv .venv; & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt }
& ".\.venv\Scripts\python.exe" run_tests.py
