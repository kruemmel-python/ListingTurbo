# ListingTurbo Enterprise v1.4.2

ListingTurbo Enterprise ist ein lokales Desktop- und Mobile-Werkzeug für verkaufsfertige Inserate auf Kleinanzeigen, eBay, Vinted und Facebook Marketplace. Die Architektur bleibt offline-first: Produktdaten, Fotos, Preislogik, Plattformprofile, Lizenzdaten und Android-Sync laufen lokal auf den Geräten des Kunden. Es gibt keinen Konto-Zwang und keine Cloud-Pflicht.

Version 1.4.2 enthält zusätzlich zur bisherigen Desktop-App:

- maschinengebundene LT2-Lizenzen
- lokales Lizenz-Ledger für einmalige Aktivierungs-IDs
- Machine-ID-Anzeige in der App
- lokalen Android-/Mobile-Sync-Server auf dem Desktop
- Android-Erfassungs-App als natives Android-Projekt
- ausführliche PowerShell-Befehle für Build, Test, Export, Lizenzierung, Portable-EXE und Android-APK

---

## 1. Projektstruktur

```text
ListingTurbo_Enterprise/
├─ app.py                              # Desktop-GUI Einstieg
├─ listingturbo_cli.py                 # CLI Export / Batch
├─ mobile_sync_server.py               # lokaler Android-Sync-Server
├─ license_generator.py                # einfache Lizenzschlüssel-Erzeugung
├─ license_admin.py                    # Einmal-Aktivierungsledger + Lizenzverwaltung
├─ build.ps1                           # Desktop Build: Native + venv + Tests
├─ run.ps1                             # Desktop-GUI starten
├─ test.ps1                            # Tests ausführen
├─ export_example.ps1                  # Beispiel-Export erzeugen
├─ build_native.ps1                    # Native C++/OpenCL DLL bauen
├─ build_android.ps1                   # Android Debug-APK bauen
├─ make_license.ps1                    # maschinengebundene Lizenz erzeugen
├─ show_machine_id.ps1                 # Machine-ID ausgeben
├─ start_mobile_sync.ps1               # Sync-Server per CLI starten
├─ package_portable.ps1                # Portable Windows-EXE bauen
├─ license_ledger.json                 # wird beim Lizenzieren lokal erzeugt
├─ listingturbo/
│  ├─ core/                            # Engine, Preislogik, Export, Lizenz, Sync
│  ├─ data/                            # Kategorien, Plattformprofile, Preisregeln
│  ├─ native/                          # Python-Bridge zur C++/OpenCL-Schicht
│  └─ ui/                              # CustomTkinter/Tkinter GUI
├─ native/
│  ├─ src/listingturbo_native.cpp      # C++17/OpenCL Backend
│  └─ build_native.ps1                 # MSVC/MinGW Native Build
├─ android/
│  └─ app/                             # native Android-Erfassungs-App
├─ examples/
└─ tests/
```

---

## 2. Frische Installation aus ZIP

Immer in einen frischen Zielordner entpacken. Nicht über eine alte Version kopieren.

```powershell
$zip="$env:USERPROFILE\Downloads\ListingTurbo_Enterprise_v1_4_mobile_license.zip"; $dst="D:\ListingTurbo_Enterprise_v1_4_mobile_license"; if(Test-Path $dst){Remove-Item $dst -Recurse -Force}; Expand-Archive $zip $dst -Force; Set-Location "$dst\ListingTurbo_Enterprise"
```

---

## 3. Komplettlauf: Build, Test, Beispiel-Export, GUI

```powershell
$zip="$env:USERPROFILE\Downloads\ListingTurbo_Enterprise_v1_4_mobile_license.zip"; $dst="D:\ListingTurbo_Enterprise_v1_4_mobile_license"; if(Test-Path $dst){Remove-Item $dst -Recurse -Force}; Expand-Archive $zip $dst -Force; Set-Location "$dst\ListingTurbo_Enterprise"; .\build.ps1; .\test.ps1; .\export_example.ps1; .\run.ps1
```

Was dabei passiert:

1. C++/OpenCL Native Backend wird gebaut.
2. Python 3.12 venv wird erzeugt.
3. Abhängigkeiten werden installiert.
4. Tests laufen.
5. Beispiel-Inserate werden als TXT/HTML/PDF erzeugt.
6. Die Desktop-GUI startet.

---

## 4. Einzelbefehle Desktop

### Build ausführen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\build.ps1
```

### Tests ausführen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\test.ps1
```

### GUI starten

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\run.ps1
```

### Beispiel-Export erzeugen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\export_example.ps1
```

### CLI manuell nutzen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe listingturbo_cli.py .\examples\samsung_s22.lturbo.json --out .\out --format all
```

### CLI mit Fotoverbesserung

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe listingturbo_cli.py .\examples\samsung_s22.lturbo.json --out .\out --format all --enhance-photos
```

### Native Backend einzeln bauen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\build_native.ps1
```

### Native Build-Log ansehen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; Get-Content .\native\bin\build_native.log -Tail 160
```

---

## 5. Portable Windows-EXE bauen

Für Endkunden ist Python/PowerShell ungeeignet. Deshalb kann eine portable EXE gebaut werden.

```powershell
$env:LISTINGTURBO_LICENSE_SECRET="HIER-DEIN-LANGES-ZUFAELLIGES-SHOP-SECRET-EINTRAGEN"; Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\package_portable.ps1
```

Ergebnis:

```text
D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise\dist\ListingTurboPortable\ListingTurboEnterprise.exe
```

Diese EXE ist der spätere Kundenpfad: entpacken, doppelklicken, nutzen.

---

## 6. Lizenzmodell v1.4.2: LT2, Machine-ID, Einmal-Aktivierung

### Wichtiger Grundsatz

Eine Lizenz kann nur dann wirklich nicht weitergegeben werden, wenn sie an eine Maschine oder an einen Aktivierungsserver gebunden ist. ListingTurbo v1.4.2 nutzt dafür einen lokalen Offline-Mechanismus:

- Jede Installation besitzt eine `Machine-ID`.
- Der Lizenzschlüssel enthält genau diese Machine-ID.
- Die Desktop-App akzeptiert die Lizenz nur auf dieser Maschine.
- Eine Weitergabe an andere Rechner scheitert an der Machine-ID-Prüfung.
- Der Verkäufer führt lokal ein `license_ledger.json`, damit eine Aktivierungs-ID nur einmal ausgegeben wird.

Ohne zentralen Server kann niemand weltweit verhindern, dass derselbe Verkäufer aus Versehen zweimal eine Lizenz für dieselbe Aktivierungs-ID erzeugt, wenn er sein Ledger löscht oder auf mehreren Rechnern unabhängig arbeitet. Genau deshalb muss das `license_ledger.json` wie ein Shop-Kassenbuch behandelt und gesichert werden. Für harte Online-Einmalaktivierung wäre später ein kleiner Aktivierungsserver nötig. Die App selbst bleibt trotzdem offline nutzbar.

---

## 7. Machine-ID des Kunden ermitteln

Der Kunde öffnet in der Desktop-App den Tab **Lizenz** und kopiert die Machine-ID.

Alternativ per PowerShell auf dem Kundenrechner:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\show_machine_id.ps1
```

Oder direkt per Python:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe license_admin.py machine-id
```

JSON-Ausgabe:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe license_admin.py machine-id --json
```

---

## 8. Lizenz erzeugen

### PRO-Lizenz für konkrete Kunden-Machine-ID

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\make_license.ps1 -Owner "kunde@example.com" -Plan PRO -MachineId "0123456789abcdef01234567" -ActivationId "ORDER-2026-0001"
```

### STANDARD-Lizenz

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\make_license.ps1 -Owner "kunde@example.com" -Plan STANDARD -MachineId "0123456789abcdef01234567" -ActivationId "ORDER-2026-0002"
```

### Lizenz mit Ablaufdatum

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\make_license.ps1 -Owner "kunde@example.com" -Plan PRO -MachineId "0123456789abcdef01234567" -ActivationId "ORDER-2026-0003" -Expires "2027-12-31"
```

### Erneute Ausstellung bewusst erzwingen

Nur verwenden, wenn ein Kunde einen neuen Rechner bekommt, eine Fehlaktivierung passiert ist oder du bewusst eine Ersatzlizenz ausstellen willst.

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\make_license.ps1 -Owner "kunde@example.com" -Plan PRO -MachineId "aaaaaaaaaaaaaaaaaaaaaaaa" -ActivationId "ORDER-2026-0001" -Force
```

---

## 9. Lizenz-Ledger prüfen

Beim Erzeugen schreibt ListingTurbo automatisch:

```text
license_ledger.json
```

Anzeigen:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; Get-Content .\license_ledger.json
```

Nur letzte Zeilen:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; Get-Content .\license_ledger.json -Tail 80
```

Lizenz dekodieren, ohne sie zu aktivieren:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe license_admin.py inspect "LT2-DEIN-LIZENZSCHLUESSEL"
```

---

## 10. Eigenes Shop-Secret setzen

Im Projekt liegt nur für Entwicklung und Tests ein öffentliches Demo-Secret. Die Lizenztools verweigern Kundenlizenzen, wenn kein eigenes `LISTINGTURBO_LICENSE_SECRET` gesetzt ist. Für echte Verkäufe ist ein eigenes langes, zufälliges Secret Pflicht.

```powershell
$env:LISTINGTURBO_LICENSE_SECRET="HIER-DEIN-LANGES-ZUFAELLIGES-SHOP-SECRET-EINTRAGEN"; Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\make_license.ps1 -Owner "kunde@example.com" -Plan PRO -MachineId "0123456789abcdef01234567" -ActivationId "ORDER-2026-0004"
```

Wichtig: Wenn du das Secret änderst, müssen App-Verifier und Lizenzgenerator zusammenpassen. `package_portable.ps1` injiziert das gesetzte Secret in den Kundenbuild und legt es nicht im Git-Repository ab. Ohne Secret bricht der Kundenbuild ab; reine lokale Testpakete müssen bewusst mit `.\package_portable.ps1 -AllowDemoSecret` gebaut werden.

---

## 11. Lizenz auf Kunden-PC aktivieren

1. Desktop-App starten.
2. Tab **Lizenz** öffnen.
3. `LT2-...` Schlüssel einfügen.
4. **Lizenz aktivieren** klicken.

Die App prüft:

- Signatur korrekt
- Plan `STANDARD` oder `PRO`
- Ablaufdatum, falls vorhanden
- Machine-ID entspricht dieser Installation

---

## 12. Android-/Mobile-Sync ohne Cloud

### Desktop-Sync-Server in der GUI

1. Desktop-App starten.
2. STANDARD- oder PRO-Lizenz aktivieren.
3. Tab **Lizenz** öffnen.
4. **Sync-Server starten** klicken.
5. Die App zeigt eine lokale URL und eine sechsstellige PIN, zum Beispiel:

```text
Mobile Sync läuft: http://192.168.178.20:53317 | PIN: 482913 | gültig bis 14:32:10
```

Diese Werte in der Android-App eintragen. Der lokale Sync nutzt bewusst HTTP im LAN, weil kein Cloud-Server beteiligt ist. Nutze ihn nur in einem vertrauenswürdigen Netzwerk; die PIN ist kurzlebig und läuft nach 15 Minuten ab.

### Desktop-Sync-Server per PowerShell starten

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\start_mobile_sync.ps1
```

Mit fester PIN nur für kontrollierte Tests:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\start_mobile_sync.ps1 -Port 53317 -Pin "482913"
```

Der Import landet unter:

```text
%APPDATA%\ListingTurbo\mobile_imports
```

Beispielordner öffnen:

```powershell
explorer "$env:APPDATA\ListingTurbo\mobile_imports"
```

---

## 13. Android-App bauen

Die Android-App ist ein natives Android-Projekt unter:

```text
android/
```

Sie kann Artikeldaten erfassen, Fotos aus der Galerie übernehmen, Kamerathumbnails speichern, eine Vorschau erzeugen, JSON lokal speichern und das Paket per lokalem HTTP direkt an den Desktop senden.

Voraussetzungen auf Windows:

- Android Studio oder Android SDK installiert
- Gradle verfügbar oder Gradle Wrapper im `android`-Ordner
- Java 17+
- Android SDK Platform 35 installiert

APK bauen:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\build_android.ps1
```

Erwartetes Ergebnis:

```text
D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise\android\app\build\outputs\apk\debug\app-debug.apk
```

APK per ADB installieren:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; adb install -r .\android\app\build\outputs\apk\debug\app-debug.apk
```

APK auf Gerät kopieren:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; explorer .\android\app\build\outputs\apk\debug
```

---

## 14. Android-Workflow

1. Desktop-App starten.
2. STANDARD/PRO-Lizenz aktivieren.
3. Mobile Sync in der Desktop-App starten.
4. Android-App öffnen.
5. Desktop-URL und die kurzlebige PIN aus dem Desktop-Lizenz-Tab eintragen.
6. Artikeldaten am Smartphone erfassen.
7. Fotos auswählen oder Kamera nutzen.
8. **An Desktop senden** drücken.
9. Desktop speichert Projekt und Bilder lokal.
10. Projektdatei in der Desktop-App laden und final exportieren.

---

## 15. Plattformprofile aktualisieren

ListingTurbo kann Plattformdaten optional über ein HTTPS-Manifest aktualisieren. Standardmäßig ist der Updatekanal deaktiviert.

Update prüfen:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe -c "from listingturbo.core.resource_update import check_or_apply_resource_updates; print(check_or_apply_resource_updates(False).message)"
```

Update anwenden:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\.venv\Scripts\python.exe -c "from listingturbo.core.resource_update import check_or_apply_resource_updates; print(check_or_apply_resource_updates(True).message)"
```

---

## 16. Demo-, STANDARD- und PRO-Verhalten

| Funktion | DEMO | STANDARD | PRO |
|---|---:|---:|---:|
| Inserate generieren | 3 pro Tag | unbegrenzt | unbegrenzt |
| Wasserzeichenfreier Export | nein | ja | ja |
| Plattformprofile | ja | ja | ja |
| Fotoanalyse | ja | ja | ja |
| Native C++/OpenCL Backend | ja | ja | ja |
| Mobile Import | nein | ja | ja |
| Batch/Mehrartikel | nein | nein | ja |
| Portable EXE | technisch möglich | ja | ja |

---

## 17. Fehlerdiagnose

### Native Build schlägt fehl

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; Get-Content .\native\bin\build_native.log -Tail 160
```

### Tests erneut ausführen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\test.ps1
```

### Python venv löschen und neu bauen

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; if(Test-Path .\.venv){Remove-Item .\.venv -Recurse -Force}; .\build.ps1
```

### Ausgabeordner leeren und Beispiel neu exportieren

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; if(Test-Path .\out){Remove-Item .\out -Recurse -Force}; .\export_example.ps1
```

### Mobile-Import-Ordner leeren

```powershell
if(Test-Path "$env:APPDATA\ListingTurbo\mobile_imports"){Remove-Item "$env:APPDATA\ListingTurbo\mobile_imports" -Recurse -Force}
```

---

## 18. Saubere Release-Kette

Desktop prüfen und Portable-EXE bauen:

```powershell
$zip="$env:USERPROFILE\Downloads\ListingTurbo_Enterprise_v1_4_mobile_license.zip"; $dst="D:\ListingTurbo_Enterprise_v1_4_mobile_license"; if(Test-Path $dst){Remove-Item $dst -Recurse -Force}; Expand-Archive $zip $dst -Force; Set-Location "$dst\ListingTurbo_Enterprise"; .\build.ps1; .\test.ps1; .\export_example.ps1; $env:LISTINGTURBO_LICENSE_SECRET="HIER-DEIN-LANGES-ZUFAELLIGES-SHOP-SECRET-EINTRAGEN"; .\package_portable.ps1
```

Android zusätzlich bauen:

```powershell
Set-Location "D:\ListingTurbo_Enterprise_v1_4_mobile_license\ListingTurbo_Enterprise"; .\build_android.ps1
```

Kompletter Entwicklerlauf inklusive lokaler PRO-Lizenz für diese Maschine:

```powershell
$zip="$env:USERPROFILE\Downloads\ListingTurbo_Enterprise_v1_4_mobile_license.zip"; $dst="D:\ListingTurbo_Enterprise_v1_4_mobile_license"; if(Test-Path $dst){Remove-Item $dst -Recurse -Force}; Expand-Archive $zip $dst -Force; Set-Location "$dst\ListingTurbo_Enterprise"; .\build.ps1; $mid=.\show_machine_id.ps1; .\make_license.ps1 -Owner "ralf@example.com" -Plan PRO -MachineId $mid -ActivationId "DEV-LOCAL-0001" -Force; .\test.ps1; .\export_example.ps1; .\run.ps1
```

---

## 19. Was v1.4.2 bewusst nicht macht

- Kein Cloud-Zwang.
- Keine automatische Übertragung an eBay/Vinted/Facebook/Kleinanzeigen-Konten.
- Kein Scraping fremder Marktplatzpreise.
- Keine rechtlich riskante Garantieberatung.
- Keine harte globale Einmalaktivierung ohne Verkäufer-Ledger oder optionalen Server.

Die App bleibt ein lokales Werkzeug: erfassen, prüfen, formulieren, exportieren, kopieren.
