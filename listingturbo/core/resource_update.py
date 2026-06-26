from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from listingturbo.core.resources import DATA_DIR, clear_resource_cache, load_json, resource_path
from listingturbo.domain import validate_platform_resource

DEFAULT_ALLOWED_FILES = frozenset({
    "platforms.json",
    "categories.json",
    "price_rules.json",
    "phrase_bank_de.json",
})
CONFIG_NAME = "update_sources.json"


@dataclass(frozen=True, slots=True)
class ResourceUpdateResult:
    checked: bool
    applied: bool
    updated_files: tuple[str, ...]
    message: str


class ResourceUpdateError(RuntimeError):
    pass


def default_manifest_url() -> str:
    try:
        config = load_json(CONFIG_NAME)
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    if not bool(config.get("enabled", False)):
        return ""
    value = config.get("manifest_url", "")
    return value if isinstance(value, str) else ""


def check_or_apply_resource_updates(
    manifest_url: str | None = None,
    *,
    apply: bool = False,
    timeout_seconds: int = 6,
) -> ResourceUpdateResult:
    url = (manifest_url or default_manifest_url()).strip()
    if not url:
        return ResourceUpdateResult(False, False, tuple(), "Kein Updatekanal konfiguriert. App bleibt vollständig offline.")

    try:
        manifest = _download_json(url, timeout_seconds)
        entries = _parse_manifest(manifest)
        if not entries:
            return ResourceUpdateResult(True, False, tuple(), "Manifest enthält keine aktualisierbaren JSON-Ressourcen.")
        pending = _resolve_pending_updates(entries, timeout_seconds)
        if not pending:
            return ResourceUpdateResult(True, False, tuple(), "Alle JSON-Ressourcen sind aktuell.")
        if not apply:
            names = ", ".join(name for name, _payload in pending)
            return ResourceUpdateResult(True, False, tuple(name for name, _ in pending), f"Updates verfügbar: {names}")
        _apply_pending_updates(pending)
        names = tuple(name for name, _payload in pending)
        return ResourceUpdateResult(True, True, names, "Aktualisiert: " + ", ".join(names))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ResourceUpdateError, ValueError) as exc:
        return ResourceUpdateResult(True, False, tuple(), f"Updateprüfung fehlgeschlagen: {exc}")


def _parse_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema_version") != 1:
        raise ResourceUpdateError("Manifest schema_version muss 1 sein.")
    entries = manifest.get("files", [])
    if not isinstance(entries, list):
        raise ResourceUpdateError("Manifest files muss eine Liste sein.")
    parsed: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ResourceUpdateError("Manifest file entry muss ein Objekt sein.")
        name = entry.get("name")
        url = entry.get("url")
        sha256 = entry.get("sha256")
        if name not in DEFAULT_ALLOWED_FILES:
            raise ResourceUpdateError(f"Nicht erlaubte Ressource: {name!r}.")
        if not isinstance(url, str) or not url.strip():
            raise ResourceUpdateError(f"Ressource {name!r}: url fehlt.")
        if sha256 is not None and (not isinstance(sha256, str) or len(sha256) != 64):
            raise ResourceUpdateError(f"Ressource {name!r}: sha256 ist ungültig.")
        parsed.append({"name": name, "url": url, "sha256": sha256})
    return parsed


def _resolve_pending_updates(entries: list[dict[str, Any]], timeout_seconds: int) -> list[tuple[str, dict[str, Any]]]:
    pending: list[tuple[str, dict[str, Any]]] = []
    for entry in entries:
        payload = _download_json(entry["url"], timeout_seconds)
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        expected = entry.get("sha256")
        if expected and digest.casefold() != expected.casefold():
            raise ResourceUpdateError(f"SHA256-Prüfung für {entry['name']} fehlgeschlagen.")
        _validate_resource(entry["name"], payload)
        current = _current_resource_digest(entry["name"])
        if current != digest:
            pending.append((entry["name"], payload))
    return pending


def _apply_pending_updates(pending: list[tuple[str, dict[str, Any]]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lturbo_update_") as temp_name:
        temp_dir = Path(temp_name)
        for name, payload in pending:
            target = temp_dir / name
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for name, _payload in pending:
            target = resource_path(name)
            backup = target.with_suffix(target.suffix + ".bak")
            if target.exists():
                shutil.copy2(target, backup)
            os.replace(temp_dir / name, target)
    clear_resource_cache()


def _validate_resource(name: str, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ResourceUpdateError(f"{name} muss ein JSON-Objekt sein.")
    if name == "platforms.json":
        validate_platform_resource(payload)
    elif name == "categories.json" and "Sonstiges" not in payload:
        raise ResourceUpdateError("categories.json muss Sonstiges enthalten.")
    elif name == "price_rules.json" and not payload:
        raise ResourceUpdateError("price_rules.json darf nicht leer sein.")


def _current_resource_digest(name: str) -> str:
    try:
        payload = load_json(name)
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _download_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "file"}:
        raise ResourceUpdateError("Update-URLs müssen https:// oder file:// verwenden.")
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # nosec: controlled scheme and JSON validation
        data = response.read(2_000_000)
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ResourceUpdateError("Geladene JSON-Ressource muss ein Objekt sein.")
    return payload
