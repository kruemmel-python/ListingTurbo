# Verify Native Backend

In der Erstellumgebung wurde geprüft:

```text
native/build_native.sh -> liblistingturbo_native.so gebaut
python3 run_tests.py -> ERGEBNIS: 10 Tests bestanden
listingturbo_cli.py examples/samsung_s22.lturbo.json --out out --format all -> OK: 4 Plattform-Inserate exportiert
```

Die Erstellumgebung besitzt keine nutzbare OpenCL-Plattform; deshalb wurde dort der deterministische C++-CPU-Fallback validiert. Auf deinem Windows-System mit AMD OpenCL wird `build.ps1` die DLL bauen und die Native-Brücke meldet im Fotoanalyse-Tab, ob OpenCL aktiv ist oder auf CPU-Fallback läuft.

## Windows-Buildfix v1.1.1

Falls MSVC `fatal error C1083: algorithm: No such file or directory` meldet, war nicht der C++-Code defekt, sondern die Visual-Studio-Compilerumgebung wurde ohne Standardheader-Pfad gestartet oder die C++-Workload ist unvollständig. Ab v1.1.1 importiert `native/build_native.ps1` die Visual-Studio-Umgebung explizit über `vcvars64.bat`, prüft den `INCLUDE`-Pfad und versucht danach optional MinGW-w64 als Fallback.

Diagnose:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_1_1_native_buildfix\ListingTurbo_Enterprise"; .\build_native.ps1; Get-Content .\native\bin\build_native.log -Tail 80
```


## v1.3.1 Hinweise

Die Native-Schicht bleibt unverändert ABI-kompatibel. Die neue PyInstaller-Paketierung nimmt `native\bin\listingturbo_native.dll` automatisch auf, wenn sie gebaut wurde. Zusätzlich wird `tkinterdnd2` vollständig eingesammelt. Falls die lokale Tk/Tcl-DnD-Erweiterung trotzdem nicht ladbar ist, startet die GUI ohne Drag-and-Drop und bleibt über `Fotos hinzufügen` vollständig bedienbar.
