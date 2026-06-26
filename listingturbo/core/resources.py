from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from listingturbo.domain import validate_platform_resource

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=16)
def load_json(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Datenressource {name!r} muss ein JSON-Objekt enthalten.")
    if name == "platforms.json":
        validate_platform_resource(payload)
    return payload


def clear_resource_cache() -> None:
    load_json.cache_clear()


def resource_path(name: str) -> Path:
    path = DATA_DIR / name
    if path.parent != DATA_DIR:
        raise ValueError("Ungültiger Ressourcenname.")
    return path


def available_categories() -> list[str]:
    return sorted(load_json("categories.json").keys())


def available_platforms() -> list[str]:
    return sorted(load_json("platforms.json").keys())
