from __future__ import annotations

from listingturbo.core.listing_engine import generate_all_platforms, generate_listing
from listingturbo.domain import Condition, ProductInput, ShippingMode


def test_listing_contains_core_fields() -> None:
    product = ProductInput(
        category="Elektronik",
        product_type="Smartphone",
        brand="Samsung",
        model="Galaxy S22",
        storage="128 GB",
        condition=Condition.GOOD,
        shipping=ShippingMode.BOTH,
        accessories="Ladegerät",
    )
    listing = generate_listing(product, "Kleinanzeigen")
    assert "Samsung" in listing.title
    assert "Galaxy S22" in listing.title
    assert "Ladegerät" in listing.description
    assert listing.price.low > 0
    assert any("Abholung/Versand" in item for item in listing.checklist)


def test_all_platforms_are_generated() -> None:
    product = ProductInput(category="Mode", product_type="Jacke", brand="Nike")
    listings = generate_all_platforms(product)
    assert {"Kleinanzeigen", "eBay", "Vinted", "Facebook Marketplace"}.issubset(listings)
    assert listings["Vinted"].hashtags


def test_platform_descriptions_are_materially_different() -> None:
    product = ProductInput(
        category="Elektronik",
        product_type="Smartphone",
        brand="Samsung",
        model="Galaxy S22",
        storage="128 GB",
        color="Schwarz",
        condition=Condition.GOOD,
        shipping=ShippingMode.BOTH,
        accessories="Ladegerät, Schutzhülle, Originalkarton",
        defects="Normale Gebrauchsspuren am Rahmen, Display ohne Risse",
        notes="Kamera, Lautsprecher, WLAN und Laden funktionieren problemlos.",
        location_hint="Abholung im Raum Leipzig möglich",
    )
    listings = generate_all_platforms(product)
    descriptions = {name: listing.description for name, listing in listings.items()}
    assert len(set(descriptions.values())) == 4
    assert "Artikelmerkmale" in descriptions["eBay"]
    assert "Für Vinted wichtige Angaben" in descriptions["Vinted"]
    assert "Schnelle Infos" in descriptions["Facebook Marketplace"]
    assert "Kurzüberblick" in descriptions["Kleinanzeigen"]


def test_price_is_not_duplicated_in_full_text() -> None:
    product = ProductInput(
        category="Elektronik",
        product_type="Smartphone",
        brand="Samsung",
        model="Galaxy S22",
        storage="128 GB",
        condition=Condition.GOOD,
        shipping=ShippingMode.BOTH,
        accessories="Ladegerät",
    )
    listing = generate_listing(product, "eBay")
    assert "Preisvorschlag:" not in listing.description
    assert listing.full_text().count("Preisvorschlag:") == 1
