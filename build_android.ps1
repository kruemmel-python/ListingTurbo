$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$Root\android"
if (Test-Path ".\gradlew.bat") {
    .\gradlew.bat assembleDebug
} elseif (Get-Command gradle -ErrorAction SilentlyContinue) {
    gradle assembleDebug
} else {
    throw "Kein Gradle gefunden. Installiere Android Studio oder lege einen Gradle Wrapper im android-Ordner ab."
}
$Apk = Join-Path (Get-Location) "app\build\outputs\apk\debug\app-debug.apk"
if (!(Test-Path $Apk)) { throw "APK wurde nicht erzeugt: $Apk" }
Write-Host "ListingTurbo Android APK gebaut: $Apk" -ForegroundColor Green
