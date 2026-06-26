# CHANGELOG

## v1.4.1 Bugfix Release

- Mobile Sync gegen große Bild-Batches gehärtet: Bildanzahl, Einzelbildgröße und Gesamtgröße werden validiert.
- Mobile Sync liest HTTP-Payloads defensiver und vermeidet unnötige UTF-8-String-Duplikation.
- Lizenzschlüssel-Parsing toleriert kopierte Schlüssel mit Zeilenumbrüchen und lehnt ungültige Zeichen sauber ab.
- PDF-Export ersetzt Unicode-Sonderzeichen nicht mehr still durch Fragezeichen, sondern normalisiert sie lesbar.
- VKS-Bildexport markiert abgeschnittene Beschreibungen mit einem sichtbaren Hinweis.
- Plattformdaten-Updateprüfung läuft in der Desktop-GUI asynchron und blockiert die Oberfläche nicht mehr.
- Regressionstests für Mobile Sync, Lizenzdecode und PDF-Textnormalisierung ergänzt.

## v1.4 Mobile License Hardening

- LT2-Lizenzformat eingeführt.
- Lizenzen sind jetzt an die lokale Machine-ID gebunden.
- App lehnt Lizenzen ab, die für eine andere Maschine erzeugt wurden.
- Lizenz-Tab zeigt Machine-ID, Lizenz-Machine-ID und Aktivierungs-ID.
- `license_admin.py` ergänzt: Ausgabe, Ledger, Inspect, Machine-ID.
- `make_license.ps1` erweitert: MachineId, ActivationId, Expires, Force.
- `show_machine_id.ps1` ergänzt.
- Lokales `license_ledger.json` verhindert doppelte Aktivierungs-ID-Ausgabe auf Verkäuferseite.
- Lokaler Android-/Mobile-Sync-Server ergänzt.
- Desktop-GUI kann Mobile Sync mit URL und PIN starten/stoppen.
- Android-App-Projekt ergänzt: native Java/Android-Erfassungs-App ohne Cloud.
- `build_android.ps1` ergänzt.
- Mobile Sync Tests ergänzt.
- README vollständig neu geschrieben.

## v1.3.1 GUI DnD Fix

- CustomTkinterDnD-Root ergänzt.
- Drag-&-Drop ist optional und darf die GUI nicht mehr crashen.

## v1.3 Commercial Hardening

- Plattformprofile materiell getrennt.
- Doppelte Preisblöcke entfernt.
- CustomTkinter-Modernisierung.
- Optionaler JSON-Updatekanal.
- PyInstaller Portable Packaging.
