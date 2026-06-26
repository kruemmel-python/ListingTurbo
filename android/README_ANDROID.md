# ListingTurbo Mobile Android

Die Android-App ist ein lokaler Erfassungs-Satellit für ListingTurbo Enterprise.

Funktionen:

- Artikeldaten am Smartphone erfassen
- Fotos aus Galerie übernehmen
- Kamera-Thumbnail erfassen
- lokale Vorschau erzeugen
- JSON lokal in den App-Ordner schreiben
- Projekt inklusive Bilder per HTTP an den Desktop-Sync-Server senden

Build:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\build_android.ps1
```

Installation:

```powershell
adb install -r .\android\app\build\outputs\apk\debug\app-debug.apk
```

Desktop vorher starten:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\start_mobile_sync.ps1 -Port 53317 -Pin "123456"
```
