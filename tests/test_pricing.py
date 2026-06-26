from __future__ import annotations

from listingturbo.core.pricing import suggest_price
from listingturbo.domain import Condition, ProductInput


def test_price_from_original_price_has_reasonable_range() -> None:
    product = ProductInput(
        category="Elektronik",
        product_type="Smartphone",
        brand="Samsung",
        model="Galaxy S22",
        condition=Condition.GOOD,
        age_years=3,
        original_price=849,
    )
    price = suggest_price(product)
    assert price.low > 0
    assert price.high > price.low
    assert price.low <= price.recommended <= price.high
    assert price.confidence == "mittel"


def test_desired_price_has_high_confidence() -> None:
    product = ProductInput(category="Mode", product_type="Jacke", desired_price=25)
    price = suggest_price(product)
    assert price.confidence == "hoch"
    assert 18 <= price.low <= price.high <= 34
