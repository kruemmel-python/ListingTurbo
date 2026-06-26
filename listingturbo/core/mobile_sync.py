from __future__ import annotations

import base64
import json
import secrets
import socket
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from listingturbo.core.license import APP_DIR, machine_fingerprint
from listingturbo.core.project_store import save_project
from listingturbo.domain import ProductInput

MOBILE_SYNC_PORT = 53317
MAX_POST_BYTES = 64 * 1024 * 1024
IMPORT_ROOT = APP_DIR / "mobile_imports"


@dataclass(frozen=True, slots=True)
class MobileImportResult:
    project_path: Path
    image_count: int
    source: str


class MobileSyncServer:
    def __init__(self, host: str = "0.0.0.0", port: int = MOBILE_SYNC_PORT, token: str | None = None) -> None:
        self.host = host
        self.port = port
        self.token = token or f"{secrets.randbelow(1_000_000):06d}"
        self.import_root = IMPORT_ROOT
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.last_import: MobileImportResult | None = None

    @property
    def is_running(self) -> bool:
        return self._httpd is not None and self._thread is not None and self._thread.is_alive()

    @property
    def display_url(self) -> str:
        return f"http://{local_lan_ip()}:{self.port}"

    def start(self) -> None:
        if self.is_running:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ListingTurboMobileSync/1.0"

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/api/v1/ping"):
                    self._send_json(
                        200,
                        {
                            "app": "ListingTurbo Enterprise",
                            "kind": "desktop-sync",
                            "machine_id": machine_fingerprint(),
                            "port": owner.port,
                        },
                    )
                    return
                self._send_json(404, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                if not self.path.startswith("/api/v1/mobile-project"):
                    self._send_json(404, {"error": "not_found"})
                    return
                provided = self.headers.get("X-ListingTurbo-Pin", "").strip()
                if provided != owner.token:
                    self._send_json(403, {"error": "invalid_pin"})
                    return
                length_header = self.headers.get("Content-Length", "0")
                try:
                    length = int(length_header)
                except ValueError:
                    self._send_json(411, {"error": "invalid_content_length"})
                    return
                if length <= 0 or length > MAX_POST_BYTES:
                    self._send_json(413, {"error": "payload_too_large", "max_bytes": MAX_POST_BYTES})
                    return
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    result = import_mobile_payload(payload, owner.import_root)
                except Exception as exc:
                    self._send_json(400, {"error": "invalid_payload", "message": str(exc)})
                    return
                owner.last_import = result
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "project_path": str(result.project_path),
                        "image_count": result.image_count,
                        "source": result.source,
                    },
                )

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.import_root.mkdir(parents=True, exist_ok=True)
        self._httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="ListingTurboMobileSync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self._thread = None


def import_mobile_payload(payload: dict[str, Any], import_root: Path = IMPORT_ROOT) -> MobileImportResult:
    if not isinstance(payload, dict):
        raise ValueError("Payload muss ein JSON-Objekt sein.")
    product_data = payload.get("product")
    if not isinstance(product_data, dict):
        raise ValueError("Payload enthält keinen product-Block.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source = str(payload.get("source", "android")).strip() or "android"
    safe_source = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in source)[:32]
    target = import_root / f"{stamp}_{safe_source}"
    image_dir = target / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    images = payload.get("images", [])
    if images is None:
        images = []
    if not isinstance(images, list):
        raise ValueError("images muss eine Liste sein.")
    for index, item in enumerate(images, start=1):
        if not isinstance(item, dict):
            continue
        encoded = str(item.get("base64", ""))
        if not encoded:
            continue
        filename = _safe_filename(str(item.get("filename") or f"image_{index}.jpg"), index)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError(f"Bild {filename} ist kein gültiges Base64.") from exc
        if len(data) > 20 * 1024 * 1024:
            raise ValueError(f"Bild {filename} ist größer als 20 MB.")
        path = image_dir / filename
        path.write_bytes(data)
        image_paths.append(path)

    product_data = _normalize_android_product(product_data)
    product_data["image_paths"] = [str(path) for path in image_paths]
    product = ProductInput.from_jsonable(product_data)
    project_path = target / "mobile_import.lturbo.json"
    save_project(product, project_path)
    metadata = {
        "source": source,
        "device_name": payload.get("device_name", ""),
        "received": datetime.now().isoformat(timespec="seconds"),
        "image_count": len(image_paths),
    }
    (target / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return MobileImportResult(project_path=project_path, image_count=len(image_paths), source=source)


def local_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def _normalize_android_product(product: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(product)
    aliases = {
        "location": "location_hint",
        "shipping_mode": "shipping",
        "household_mode": "household",
    }
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized.pop(source)
    if not normalized.get("condition"):
        normalized["condition"] = "Gut"
    if not normalized.get("shipping"):
        normalized["shipping"] = "Abholung oder Versand"
    if not normalized.get("household"):
        normalized["household"] = "Keine Angabe"
    if not normalized.get("category"):
        normalized["category"] = "Sonstiges"
    if not normalized.get("product_type"):
        normalized["product_type"] = "Artikel"
    for int_key in ("quantity", "age_years"):
        if normalized.get(int_key) in {"", None}:
            normalized.pop(int_key, None)
    for float_key in ("original_price", "desired_price"):
        if normalized.get(float_key) in {"", None}:
            normalized.pop(float_key, None)
    normalized.setdefault("quantity", 1)
    return normalized


def _safe_filename(value: str, index: int) -> str:
    name = Path(value).name.strip() or f"image_{index}.jpg"
    cleaned = "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in name)
    if "." not in cleaned:
        cleaned += ".jpg"
    return cleaned[:80]
