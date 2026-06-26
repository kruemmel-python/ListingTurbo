from __future__ import annotations

from pathlib import Path

from listingturbo.core.exporter import export_html, export_pdf, export_txt, export_vks_image
from listingturbo.core.listing_engine import generate_listing
from listingturbo.domain import ProductInput


def test_exports_are_written(tmp_path: Path) -> None:
    listing = generate_listing(ProductInput(category="Sonstiges", product_type="Testartikel"), "Kleinanzeigen")
    txt = export_txt(listing, tmp_path / "listing.txt")
    html = export_html(listing, tmp_path / "listing.html")
    pdf = export_pdf(listing, tmp_path / "listing.pdf")
    vks = export_vks_image(listing, tmp_path / "listing_vks.png")
    assert txt.read_text(encoding="utf-8").startswith("Titel:")
    assert "<!doctype html>" in html.read_text(encoding="utf-8")
    assert pdf.read_bytes().startswith(b"%PDF-1.4")
    assert vks.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
