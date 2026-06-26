from __future__ import annotations

from pathlib import Path

from listingturbo.core.project_store import load_project, save_project
from listingturbo.domain import ProductInput


def test_project_roundtrip(tmp_path: Path) -> None:
    product = ProductInput(category="Werkzeug", product_type="Akkuschrauber", brand="Bosch")
    path = save_project(product, tmp_path / "test.lturbo.json")
    loaded = load_project(path)
    assert loaded.category == "Werkzeug"
    assert loaded.product_type == "Akkuschrauber"
    assert loaded.brand == "Bosch"
