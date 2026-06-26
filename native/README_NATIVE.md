# ListingTurbo Native Backend v1.1

Diese Schicht zieht die rechenintensive Bildarbeit aus Python heraus:

- `lt_analyze_rgb8`: Helligkeit, Kontrast und Schärfe auf RGB8-Puffern
- `lt_enhance_rgb8`: Helligkeits-/Kontrast-/Schärfe-Enhancement auf RGB8-Puffern
- deterministische C++17-CPU-Referenz als immer verfügbarer Pfad
- dynamisch geladener OpenCL-Hotpath ohne OpenCL-SDK-Linkpflicht
- C-ABI v1 für Python-`ctypes`, damit die GUI unverändert produktiv bleibt

Die OpenCL-Runtime wird erst zur Laufzeit geladen (`OpenCL.dll`, `libOpenCL.so`). Fehlt OpenCL oder meldet der Treiber keine Plattform, läuft dieselbe API über die CPU-Referenz weiter.

Windows-Build:

```powershell
.\build_native.ps1
```

Linux-Testbuild:

```bash
./native/build_native.sh
```

Die Python-Brücke sucht die DLL/SO in:

```text
native/bin/
native/build/
Projektwurzel/
```
