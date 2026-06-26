$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "[1/5] Native Backend bauen" -ForegroundColor Cyan
& "$Root\build_native.ps1"

Write-Host "[2/5] Python-Build-Umgebung vorbereiten" -ForegroundColor Cyan
if (!(Test-Path ".venv")) { py -3.12 -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/5] Tests ausführen" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" run_tests.py

Write-Host "[4/5] PyInstaller EXE bauen" -ForegroundColor Cyan
Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
$addData1 = "listingturbo\data;listingturbo\data"
$addData2 = "examples;examples"
$addBinary = "native\bin\listingturbo_native.dll;native\bin"
$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "ListingTurboEnterprise",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--hidden-import", "PIL._tkinter_finder",
    "--add-data", $addData1,
    "--add-data", $addData2
)
if (Test-Path ".\native\bin\listingturbo_native.dll") { $pyArgs += @("--add-binary", $addBinary) }
$pyArgs += "app.py"
& ".\.venv\Scripts\python.exe" @pyArgs

Write-Host "[5/5] Portable Paket schreiben" -ForegroundColor Cyan
$Portable = ".\dist\ListingTurboPortable"
Remove-Item $Portable -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Portable | Out-Null
Copy-Item ".\dist\ListingTurboEnterprise\*" $Portable -Recurse -Force
Copy-Item ".\README.md", ".\CHANGELOG.md", ".\VERIFY_NATIVE.md" $Portable -Force
Compress-Archive -Path "$Portable\*" -DestinationPath ".\dist\ListingTurboEnterprise_Portable.zip" -Force
Write-Host "Portable EXE: $Root\dist\ListingTurboPortable\ListingTurboEnterprise.exe" -ForegroundColor Green
Write-Host "Portable ZIP: $Root\dist\ListingTurboEnterprise_Portable.zip" -ForegroundColor Green
