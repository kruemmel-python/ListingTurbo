from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from listingturbo.core.license import (
    create_license_key,
    decode_license_key_for_admin,
    is_development_license_secret,
    machine_fingerprint,
)

DEFAULT_LEDGER = Path("license_ledger.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="ListingTurbo Lizenz-Administration mit Einmal-Aktivierungsledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    issue = sub.add_parser("issue", help="maschinengebundene STANDARD-/PRO-Lizenz erzeugen")
    issue.add_argument("--owner", required=True, help="Name oder E-Mail des Kunden")
    issue.add_argument("--plan", choices=["STANDARD", "PRO"], required=True, help="Lizenzplan")
    issue.add_argument("--machine-id", required=True, help="Machine-ID aus dem Lizenz-Tab des Kunden")
    issue.add_argument("--activation-id", help="eigene Bestell-/Aktivierungs-ID, optional")
    issue.add_argument("--expires", help="Ablaufdatum YYYY-MM-DD, optional")
    issue.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER, help="lokales Aktivierungsledger")
    issue.add_argument("--force", action="store_true", help="erneute Ausgabe trotz bereits genutzter Aktivierungs-ID erlauben")
    issue.add_argument("--secret-env", default="LISTINGTURBO_LICENSE_SECRET", help="Environment-Variable für Shop-Secret")

    inspect = sub.add_parser("inspect", help="Lizenzschlüssel dekodieren, ohne ihn zu aktivieren")
    inspect.add_argument("key", help="LT2-Lizenzschlüssel")

    mid = sub.add_parser("machine-id", help="Machine-ID dieser Maschine ausgeben")
    mid.add_argument("--json", action="store_true", help="als JSON ausgeben")

    args = parser.parse_args()
    match args.command:
        case "issue":
            return _issue(args)
        case "inspect":
            payload = decode_license_key_for_admin(args.key)
            print(json.dumps(payload or {}, ensure_ascii=False, indent=2))
            return 0
        case "machine-id":
            value = machine_fingerprint()
            if args.json:
                print(json.dumps({"machine_id": value}, ensure_ascii=False, indent=2))
            else:
                print(value)
            return 0
        case _:
            raise AssertionError("unerreichbar")


def _issue(args: argparse.Namespace) -> int:
    ledger = _read_ledger(args.ledger)
    activation_id = args.activation_id or f"ORDER-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    machine_id = args.machine_id.strip().lower()
    key = activation_id.strip().lower()
    existing = ledger.get("activations", {}).get(key)
    if existing and not args.force:
        raise SystemExit(
            "Aktivierungs-ID wurde bereits genutzt. Für Ersatzlizenz bewusst --force verwenden.\n"
            + json.dumps(existing, ensure_ascii=False, indent=2)
        )
    secret = os.getenv(args.secret_env, "")
    if not secret or is_development_license_secret(secret):
        raise SystemExit(
            f"{args.secret_env} muss auf ein eigenes Produktionssecret gesetzt sein. "
            "Das öffentliche Demo-Secret darf keine Kundenlizenzen erzeugen."
        )
    license_key = create_license_key(
        args.owner,
        args.plan,
        secret=secret,
        machine_id=machine_id,
        activation_id=activation_id,
        expires=args.expires,
    )
    entry: dict[str, Any] = {
        "owner": args.owner,
        "plan": args.plan,
        "machine_id": machine_id,
        "activation_id": activation_id,
        "expires": args.expires,
        "issued": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license_prefix": license_key[:24],
    }
    ledger.setdefault("schema_version", 1)
    ledger.setdefault("activations", {})[key] = entry
    args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(license_key)
    return 0


def _read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "activations": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Ledger ist kein JSON-Objekt.")
    if not isinstance(payload.get("activations", {}), dict):
        raise ValueError("Ledger enthält keinen gültigen activations-Block.")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
