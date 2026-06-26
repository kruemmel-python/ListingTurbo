# ListingTurbo Mobile Android v1.4.4

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
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\start_mobile_sync.ps1 -Port 53317
```

Die Desktop-App zeigt URL und kurzlebige Transfer-PIN an. In der Android-App sind diese Felder absichtlich leer und nur mit Beispiel-Hints versehen. Der Sync läuft per HTTP im lokalen WLAN; nutze ihn nur in vertrauenswürdigen Netzwerken.
