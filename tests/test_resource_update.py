from __future__ import annotations

import json
from pathlib import Path

from listingturbo.core.resource_update import check_or_apply_resource_updates


def test_resource_update_detects_local_manifest(tmp_path: Path) -> None:
    platforms = {
        "Kleinanzeigen": {
            "max_title": 81,
            "max_description": 4000,
            "sections": ["titel", "beschreibung"],
            "hashtags": False,
            "tone": "test",
        }
    }
    platform_file = tmp_path / "platforms.json"
    platform_file.write_text(json.dumps(platforms, ensure_ascii=False), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "files": [{"name": "platforms.json", "url": platform_file.resolve().as_uri()}],
    }
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    result = check_or_apply_resource_updates(manifest_file.resolve().as_uri(), apply=False)
    assert result.checked
    assert not result.applied
    assert "platforms.json" in result.updated_files


def test_resource_update_rejects_http_scheme(tmp_path: Path) -> None:
    result = check_or_apply_resource_updates("http://example.invalid/manifest.json", apply=False)
    assert result.checked
    assert not result.applied
    assert "https:// oder file://" in result.message
