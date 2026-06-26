from __future__ import annotations

import json
from pathlib import Path

from listingturbo.domain import ProductInput

SCHEMA_VERSION = 1


def save_project(product: ProductInput, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, "product": product.to_jsonable()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project(path: Path) -> ProductInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Projektdatei hat eine nicht unterstützte Schema-Version.")
    product = payload.get("product")
    if not isinstance(product, dict):
        raise ValueError("Projektdatei enthält keinen gültigen Produktblock.")
    return ProductInput.from_jsonable(product)
