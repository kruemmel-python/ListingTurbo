from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

APP_DIR = Path(os.getenv("APPDATA", Path.home() / ".listingturbo")) / "ListingTurbo"
LICENSE_FILE = APP_DIR / "license.json"
USAGE_FILE = APP_DIR / "usage.json"
DEVELOPMENT_LICENSE_SECRET = "ListingTurbo-v1-offline-verifier-change-for-your-shop"
try:
    from listingturbo.core.license_secret import LICENSE_VERIFY_SECRET as BUNDLED_LICENSE_VERIFY_SECRET
except Exception:  # pragma: no cover - production builds may inject this module.
    BUNDLED_LICENSE_VERIFY_SECRET = ""
PUBLIC_VERIFY_SECRET = os.getenv(
    "LISTINGTURBO_LICENSE_VERIFY_SECRET",
    BUNDLED_LICENSE_VERIFY_SECRET or DEVELOPMENT_LICENSE_SECRET,
)
LICENSE_VERSION = 2
LICENSE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

Plan = Literal["DEMO", "STANDARD", "PRO"]


@dataclass(frozen=True, slots=True)
class LicenseState:
    plan: Plan
    valid: bool
    owner: str
    message: str
    remaining_demo_generations: int
    machine_id: str = ""
    licensed_machine_id: str = ""
    activation_id: str = ""

    @property
    def can_export_without_watermark(self) -> bool:
        return self.valid and self.plan in {"STANDARD", "PRO"}

    @property
    def can_batch(self) -> bool:
        return self.valid and self.plan == "PRO"

    @property
    def can_mobile_import(self) -> bool:
        return self.valid and self.plan in {"STANDARD", "PRO"}


def current_license_state() -> LicenseState:
    payload = _read_json(LICENSE_FILE)
    remaining = _remaining_demo_generations()
    current_machine = machine_fingerprint()
    if not payload:
        return LicenseState(
            "DEMO",
            False,
            "",
            "Demo-Modus: 3 Generierungen pro Tag.",
            remaining,
            machine_id=current_machine,
        )

    validation_message = validate_license_payload(payload, current_machine=current_machine)
    owner = str(payload.get("owner", ""))
    plan = payload.get("plan") if payload.get("plan") in {"STANDARD", "PRO"} else "DEMO"
    licensed_machine = str(payload.get("machine_id") or payload.get("machine_hint") or "")
    activation_id = str(payload.get("activation_id", ""))
    if validation_message is not None:
        return LicenseState(
            "DEMO",
            False,
            owner,
            validation_message,
            remaining,
            machine_id=current_machine,
            licensed_machine_id=licensed_machine,
            activation_id=activation_id,
        )
    return LicenseState(
        plan,  # type: ignore[arg-type]
        True,
        owner,
        f"{plan}-Lizenz aktiv für {owner} auf dieser Maschine.",
        remaining,
        machine_id=current_machine,
        licensed_machine_id=licensed_machine,
        activation_id=activation_id,
    )


def register_license_key(key: str) -> LicenseState:
    decoded = _decode_key(key)
    remaining = _remaining_demo_generations()
    current_machine = machine_fingerprint()
    if not decoded:
        return LicenseState(
            "DEMO",
            False,
            "",
            "Lizenzschlüssel konnte nicht gelesen werden.",
            remaining,
            machine_id=current_machine,
        )
    validation_message = validate_license_payload(decoded, current_machine=current_machine)
    if validation_message is not None:
        return LicenseState(
            "DEMO",
            False,
            str(decoded.get("owner", "")),
            validation_message,
            remaining,
            machine_id=current_machine,
            licensed_machine_id=str(decoded.get("machine_id", "")),
            activation_id=str(decoded.get("activation_id", "")),
        )
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(json.dumps(decoded, ensure_ascii=False, indent=2), encoding="utf-8")
    return current_license_state()


def validate_license_payload(payload: dict[str, Any], *, current_machine: str | None = None) -> str | None:
    plan = payload.get("plan")
    owner = str(payload.get("owner", "")).strip()
    signature = str(payload.get("signature", ""))
    signed_payload = {key: payload[key] for key in sorted(payload) if key != "signature"}
    expected = _signature(signed_payload, PUBLIC_VERIFY_SECRET)
    if not hmac.compare_digest(signature, expected):
        return "Lizenzsignatur ungültig."
    if plan not in {"STANDARD", "PRO"}:
        return "Lizenzplan unbekannt."
    if not owner:
        return "Lizenz enthält keinen Inhaber."
    expires = payload.get("expires")
    if expires:
        try:
            expiry = datetime.fromisoformat(str(expires)).date()
        except ValueError:
            return "Lizenz-Ablaufdatum ist ungültig."
        if expiry < date.today():
            return "Lizenz ist abgelaufen."
    licensed_machine = str(payload.get("machine_id", "")).strip()
    if not licensed_machine:
        return "Lizenz ist nicht maschinengebunden. Bitte eine neue LT2-Lizenz mit Machine-ID erzeugen."
    if current_machine is not None and licensed_machine != current_machine:
        return (
            "Lizenz ist an eine andere Maschine gebunden. "
            f"Diese Maschine: {current_machine}; Lizenz: {licensed_machine}."
        )
    return None


def record_generation() -> LicenseState:
    state = current_license_state()
    if state.valid:
        return state
    usage = _read_json(USAGE_FILE) or {}
    today = date.today().isoformat()
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    usage["count"] = int(usage.get("count", 0)) + 1
    APP_DIR.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage, indent=2), encoding="utf-8")
    return current_license_state()


def can_generate() -> bool:
    state = current_license_state()
    return state.valid or state.remaining_demo_generations > 0


def machine_fingerprint() -> str:
    components = [
        platform.node(),
        platform.system(),
        platform.machine(),
        os.getenv("PROCESSOR_IDENTIFIER", ""),
        _windows_machine_guid(),
        f"mac:{uuid.getnode():012x}",
    ]
    raw = "|".join(item for item in components if item)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def create_activation_request(owner: str = "") -> dict[str, Any]:
    return {
        "app": "ListingTurbo Enterprise",
        "license_version": LICENSE_VERSION,
        "owner": owner.strip(),
        "machine_id": machine_fingerprint(),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def create_license_key(
    owner: str,
    plan: Plan,
    *,
    secret: str,
    machine_id: str | None = None,
    activation_id: str | None = None,
    expires: str | None = None,
) -> str:
    if plan not in {"STANDARD", "PRO"}:
        raise ValueError("Nur STANDARD oder PRO können als Lizenz erstellt werden.")
    clean_owner = owner.strip()
    if not clean_owner:
        raise ValueError("Der Lizenzinhaber darf nicht leer sein.")
    bound_machine = (machine_id or machine_fingerprint()).strip().lower()
    if not _is_machine_id_shape(bound_machine):
        raise ValueError("Machine-ID ist ungültig. Erwartet werden 24 hexadezimale Zeichen.")
    payload: dict[str, Any] = {
        "license_version": LICENSE_VERSION,
        "owner": clean_owner,
        "plan": plan,
        "issued": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine_id": bound_machine,
        "activation_id": (activation_id or _activation_id(clean_owner, bound_machine)).strip(),
    }
    if expires:
        payload["expires"] = expires
    payload["signature"] = _signature({key: payload[key] for key in sorted(payload)}, secret)
    encoded = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode(
        "ascii"
    )
    return "LT2-" + encoded.rstrip("=")


def decode_license_key_for_admin(key: str) -> dict[str, Any] | None:
    return _decode_key(key)


def _remaining_demo_generations() -> int:
    usage = _read_json(USAGE_FILE) or {}
    today = date.today().isoformat()
    if usage.get("date") != today:
        return 3
    return max(0, 3 - int(usage.get("count", 0)))


def _decode_key(key: str) -> dict[str, Any] | None:
    stripped = "".join(str(key).split())
    prefix = stripped[:4].upper()
    if prefix == "LT2-":
        encoded = stripped[4:]
    elif prefix == "LT1-":
        encoded = stripped[4:]
    else:
        return None
    if not encoded or len(encoded) % 4 == 1 or not LICENSE_KEY_RE.fullmatch(encoded):
        return None
    encoded += "=" * (-len(encoded) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
    except (UnicodeEncodeError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _signature(payload: dict[str, Any], secret: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _windows_machine_guid() -> str:
    if platform.system().lower() != "windows":
        return ""
    try:
        import winreg  # type: ignore[import-not-found]

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _kind = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except Exception:
        return ""


def _is_machine_id_shape(value: str) -> bool:
    return len(value) == 24 and all(char in "0123456789abcdef" for char in value)


def _activation_id(owner: str, machine_id: str) -> str:
    raw = f"{owner.strip().lower()}|{machine_id}|{datetime.now(timezone.utc).date().isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:18].upper()


def is_development_license_secret(secret: str | None = None) -> bool:
    return (secret or PUBLIC_VERIFY_SECRET) == DEVELOPMENT_LICENSE_SECRET
