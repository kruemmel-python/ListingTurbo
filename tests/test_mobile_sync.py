from __future__ import annotations

import base64
import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from listingturbo.core import mobile_sync
from listingturbo.core.mobile_sync import MobileSyncServer, import_mobile_payload


def _payload() -> dict[str, object]:
    return {
        "source": "ListingTurboAndroid",
        "device_name": "Testgerät",
        "product": {
            "category": "Elektronik",
            "product_type": "Smartphone",
            "brand": "Samsung",
            "model": "Galaxy S22",
            "condition": "Gut",
            "shipping": "Abholung oder Versand",
            "household": "Nichtraucherhaushalt",
            "quantity": 1,
        },
        "images": [
            {
                "filename": "front.jpg",
                "mime_type": "image/jpeg",
                "base64": base64.b64encode(b"fake-jpeg-bytes").decode("ascii"),
            }
        ],
    }


def test_mobile_payload_import_writes_project(tmp_path: Path) -> None:
    result = import_mobile_payload(_payload(), tmp_path)
    assert result.project_path.exists()
    assert result.image_count == 1
    project = json.loads(result.project_path.read_text(encoding="utf-8"))
    assert project["product"]["brand"] == "Samsung"
    assert len(project["product"]["image_paths"]) == 1


def test_mobile_payload_rejects_oversized_base64_before_decode(tmp_path: Path) -> None:
    previous_limit = mobile_sync.MAX_IMAGE_BYTES
    mobile_sync.MAX_IMAGE_BYTES = 8
    payload = _payload()
    payload["images"] = [{"filename": "too-large.jpg", "base64": "A" * 16}]
    try:
        try:
            import_mobile_payload(payload, tmp_path)
        except ValueError as exc:
            assert "größer als 20 MB" in str(exc)
        else:
            raise AssertionError("Oversized mobile image was accepted")
    finally:
        mobile_sync.MAX_IMAGE_BYTES = previous_limit


def test_mobile_sync_pin_expires() -> None:
    server = MobileSyncServer(host="127.0.0.1", port=0, token="123456", pin_ttl_seconds=60)
    server.started_at = datetime.now() - timedelta(seconds=120)

    assert server.is_pin_expired


def test_mobile_sync_server_accepts_authorized_post(tmp_path: Path) -> None:
    server = MobileSyncServer(host="127.0.0.1", port=0, token="123456")
    server.import_root = tmp_path
    server.start()
    assert server._httpd is not None
    port = int(server._httpd.server_address[1])
    try:
        data = json.dumps(_payload()).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/mobile-project",
            data=data,
            headers={"Content-Type": "application/json", "X-ListingTurbo-Pin": "123456"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        assert result["ok"] is True
        assert Path(result["project_path"]).exists()
    finally:
        server.stop()
