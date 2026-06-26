# ListingTurbo Enterprise Demo

Diese Demo ist für einen schnellen Produkttest gedacht. Sie nutzt bewusst kein Produktions-Lizenzsecret und darf nicht als Kundenbuild verkauft werden.

## In 3 Minuten testen

1. `ListingTurboEnterprise.exe` starten.
2. Im Tab **Eingabe** auf **Beispieldaten** klicken.
3. **Inserat generieren** klicken.
4. Im Tab **Inserat** die Plattform wechseln und Texte vergleichen.
5. Export über **TXT**, **HTML**, **PDF** oder **VKS-Bild** ausprobieren.

## Was die Demo zeigt

- fertige Verkaufstexte für mehrere Plattformen
- Preisvorschlag mit Verhandlungsbereich
- Checkliste für bessere Inserate
- lokaler Export ohne Cloud-Zwang
- Beispielprojekt unter `examples\samsung_s22.lturbo.json`

## Demo-Grenze

Die Demo ist für Produktprüfung und Vorführung gedacht. Kundenlizenzen und verkaufsfähige Builds müssen lokal mit eigenem `LISTINGTURBO_LICENSE_SECRET` gebaut werden.

## Kundenbuild erstellen

```powershell
$env:LISTINGTURBO_LICENSE_SECRET="DEIN-LANGES-PRODUKTIONSSECRET"
.\package_portable.ps1
```
