from __future__ import annotations

from math import floor

from listingturbo.core.resources import load_json
from listingturbo.domain import PriceSuggestion, ProductInput


def suggest_price(product: ProductInput) -> PriceSuggestion:
    rules = load_json("price_rules.json")
    if product.desired_price is not None and product.desired_price > 0:
        base = product.desired_price
        confidence = "hoch"
        explanation = "Der Preis basiert auf deinem gewünschten Zielpreis und wird als verhandelbarer Bereich gerundet."
    elif product.original_price is not None and product.original_price > 0:
        base = _base_from_original_price(product, rules)
        confidence = "mittel"
        explanation = "Der Preis basiert auf Neupreis, Zustand, Alter, Kategorie und Markenfaktor."
    else:
        base = _fallback_price(product)
        confidence = "niedrig"
        explanation = "Ohne Neupreis ist dies eine konservative Marktplatz-Schätzung aus Kategorie und Zustand."

    spread = float(rules.get("category_spread", {}).get(product.category, 0.22))
    floor_value = int(rules.get("category_floor", {}).get(product.category, 2))
    low = max(floor_value, _round_market(base * (1.0 - spread)))
    high = max(low + 1, _round_market(base * (1.0 + spread)))
    recommended = _round_market((low + high) / 2)

    return PriceSuggestion(
        low=low,
        high=high,
        recommended=recommended,
        confidence=confidence,
        explanation=explanation,
    )


def _base_from_original_price(product: ProductInput, rules: dict) -> float:
    condition_multiplier = float(
        rules.get("condition_multiplier", {}).get(str(product.condition), 0.45)
    )
    age = product.age_years if product.age_years is not None else 2
    age_key = str(min(max(age, 0), 10))
    age_multiplier = float(rules.get("age_multiplier", {}).get(age_key, 0.35))
    brand_multiplier = _brand_multiplier(product.brand, rules)
    category_floor = float(rules.get("category_floor", {}).get(product.category, 2))
    assert product.original_price is not None
    return max(category_floor, product.original_price * condition_multiplier * age_multiplier * brand_multiplier)


def _brand_multiplier(brand: str, rules: dict) -> float:
    normalized = brand.strip().lower()
    if not normalized:
        return 1.0
    return float(rules.get("brand_bonus", {}).get(normalized, 1.0))


def _fallback_price(product: ProductInput) -> float:
    category_defaults = {
        "Elektronik": 95,
        "Mode": 18,
        "Kinderkleidung": 14,
        "Möbel": 45,
        "Haushalt": 28,
        "Werkzeug": 55,
        "Bücher & Medien": 12,
        "Sonstiges": 20,
    }
    condition_factor = {
        "Neu / unbenutzt": 1.5,
        "Sehr gut": 1.2,
        "Gut": 1.0,
        "Akzeptabel": 0.65,
        "Defekt / Bastler": 0.35,
    }.get(str(product.condition), 1.0)
    quantity_factor = max(1, min(product.quantity, 20)) ** 0.35
    brand_factor = 1.1 if product.brand.strip() else 1.0
    return category_defaults.get(product.category, 20) * condition_factor * quantity_factor * brand_factor


def _round_market(value: float) -> int:
    if value < 10:
        return max(1, round(value))
    if value < 50:
        return int(round(value / 2) * 2)
    if value < 200:
        return int(round(value / 5) * 5)
    return int(floor(value / 10) * 10)
