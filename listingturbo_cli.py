from __future__ import annotations

import argparse
import json
from pathlib import Path

from listingturbo.core.exporter import export_html, export_pdf, export_txt, export_vks_image
from listingturbo.core.image_enhance import enhance_images
from listingturbo.core.listing_engine import generate_all_platforms
from listingturbo.domain import ProductInput


def main() -> int:
    parser = argparse.ArgumentParser(description="ListingTurbo CLI für Batch- und Automationsläufe.")
    parser.add_argument("project", type=Path, help="JSON-Datei mit ProductInput-Daten oder .lturbo.json-Projekt.")
    parser.add_argument("--out", type=Path, default=Path("out"), help="Ausgabeordner.")
    parser.add_argument("--format", choices=["txt", "html", "pdf", "vks", "all"], default="all")
    parser.add_argument("--enhance-photos", action="store_true", help="Fotos optimiert in out/photos exportieren.")
    args = parser.parse_args()

    product = _load_product(args.project)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.enhance_photos and product.image_paths:
        enhance_images(product.image_paths, args.out / "photos")

    listings = generate_all_platforms(product)
    for platform, listing in listings.items():
        stem = platform.lower().replace(" ", "_")
        if args.format in {"txt", "all"}:
            export_txt(listing, args.out / f"{stem}.txt")
        if args.format in {"html", "all"}:
            export_html(listing, args.out / f"{stem}.html")
        if args.format in {"pdf", "all"}:
            export_pdf(listing, args.out / f"{stem}.pdf")
        if args.format in {"vks", "all"}:
            export_vks_image(listing, args.out / f"{stem}_vks.png", product.image_paths)
    print(f"OK: {len(listings)} Plattform-Inserate nach {args.out} exportiert.")
    return 0


def _load_product(path: Path) -> ProductInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "product" in payload and "schema_version" in payload:
        payload = payload["product"]
    return ProductInput.from_jsonable(payload)


if __name__ == "__main__":
    raise SystemExit(main())
