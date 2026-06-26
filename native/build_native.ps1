$ErrorActionPreference = "Stop"
# Deduplicate process-level PATH to avoid "command line too long" error in cmd/vcvars64
$env:PATH = ($env:PATH -split ';' | Where-Object { $_.Trim() -ne "" } | Select-Object -Unique) -join ';'

$NativeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $NativeRoot
$Src = Join-Path $NativeRoot "src\listingturbo_native.cpp"
$Bin = Join-Path $NativeRoot "bin"
$Out = Join-Path $Bin "listingturbo_native.dll"
$Log = Join-Path $Bin "build_native.log"
New-Item -ItemType Directory -Force $Bin | Out-Null

function Write-Step([string]$Text) {
    Write-Host "[ListingTurbo Native] $Text" -ForegroundColor Cyan
}

function Get-VsInstallRoot {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $hit = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
        if ($LASTEXITCODE -eq 0 -and $hit -and (Test-Path $hit)) { return $hit.Trim() }
    }

    $candidates = @(
        "$env:ProgramFiles\Microsoft Visual Studio\2022\Enterprise",
        "$env:ProgramFiles\Microsoft Visual Studio\2022\Professional",
        "$env:ProgramFiles\Microsoft Visual Studio\2022\Community",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools"
    )
    foreach ($root in $candidates) {
        if (Test-Path (Join-Path $root "VC\Auxiliary\Build\vcvars64.bat")) { return $root }
    }
    return $null
}

function Import-VsDevEnvironment([string]$VsRoot) {
    $vcvars = Join-Path $VsRoot "VC\Auxiliary\Build\vcvars64.bat"
    if (!(Test-Path $vcvars)) { throw "vcvars64.bat nicht gefunden: $vcvars" }

    $tmp = Join-Path $env:TEMP ("listingturbo_vcvars_" + [Guid]::NewGuid().ToString("N") + ".cmd")
    $cmd = "@echo off`r`ncall `"$vcvars`" >nul`r`nif errorlevel 1 exit /b %errorlevel%`r`nset`r`n"
    Set-Content -Path $tmp -Value $cmd -Encoding ASCII
    try {
        $lines = & cmd.exe /d /c "`"$tmp`""
        if ($LASTEXITCODE -ne 0) { throw "Visual-Studio-Umgebung konnte nicht initialisiert werden." }
        foreach ($line in $lines) {
            if ($line -match "^([^=]+)=(.*)$") {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Test-MsvcStdHeaders {
    if (-not $env:INCLUDE) { return $false }
    foreach ($dir in ($env:INCLUDE -split ';')) {
        if ($dir -and (Test-Path (Join-Path $dir "algorithm"))) { return $true }
    }
    return $false
}

function Invoke-MsvcBuild {
    $vsRoot = Get-VsInstallRoot
    if (-not $vsRoot) { return $false }

    Write-Step "Visual Studio erkannt: $vsRoot"
    Import-VsDevEnvironment $vsRoot

    if (-not (Test-MsvcStdHeaders)) {
        Write-Warning "MSVC-Standardheader nicht im INCLUDE-Pfad gefunden. MinGW-Fallback wird versucht."
        return $false
    }

    $cl = Get-Command cl.exe -ErrorAction SilentlyContinue
    if (-not $cl) { return $false }

    Write-Step "Baue DLL mit MSVC: $($cl.Source)"
    $args = @(
        "/nologo",
        "/TP",
        "/O2",
        "/std:c++17",
        "/EHsc",
        "/LD",
        "`"$Src`"",
        "/Fe:`"$Out`"",
        "/link",
        "/INCREMENTAL:NO"
    )

    $cmdLine = "`"$($cl.Source)`" " + ($args -join " ")
    $cmdLine | Set-Content -Path $Log -Encoding UTF8
    cmd.exe /d /c $cmdLine 2>&1 | Tee-Object -FilePath $Log -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "MSVC-Build fehlgeschlagen. Details: $Log"
        return $false
    }
    return (Test-Path $Out)
}

function Invoke-GppBuild {
    $gpp = Get-Command g++.exe -ErrorAction SilentlyContinue
    if (-not $gpp) { $gpp = Get-Command g++ -ErrorAction SilentlyContinue }
    if (-not $gpp) { return $false }

    Write-Step "Baue DLL mit MinGW/G++: $($gpp.Source)"
    & $gpp.Source -std=c++17 -O3 -shared -static-libgcc -static-libstdc++ -o $Out $Src 2>&1 | Tee-Object -FilePath $Log
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "MinGW-Build fehlgeschlagen. Details: $Log"
        return $false
    }
    return (Test-Path $Out)
}

if (!(Test-Path $Src)) { throw "Native-Quelle nicht gefunden: $Src" }
Remove-Item $Out -Force -ErrorAction SilentlyContinue

$ok = Invoke-MsvcBuild
if (-not $ok) { $ok = Invoke-GppBuild }
if (-not $ok) {
    throw "Native-Build fehlgeschlagen. Installiere 'Desktopentwicklung mit C++' in Visual Studio 2022 oder MinGW-w64. Build-Log: $Log"
}

Write-Host "ListingTurbo Native Backend gebaut: $Out" -ForegroundColor Green
